"""
Unit tests for IngestionService.
DB session is mocked — no real database required to run these.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.models.db_models import MLModel, PredictionLog
from app.models.schemas import GroundTruthBatch, GroundTruthUpdate, PredictionLogBatch, PredictionLogCreate
from app.services.ingestion import IngestionService


def make_mock_model(task_type: str = "classification") -> MLModel:
    m = MagicMock(spec=MLModel)
    m.id = str(uuid4())
    m.name = "test-model"
    m.task_type = task_type
    m.feature_schema = {"age": "float", "income": "float", "city": "str"}
    return m


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.flush = AsyncMock()
    db.refresh = AsyncMock()
    db.add = MagicMock()
    db.add_all = MagicMock()
    return db


@pytest.fixture
def svc(mock_db):
    return IngestionService(mock_db)


# ── ingest_single ────────────────────────────────────────────────────────────

class TestIngestSingle:
    async def test_happy_path(self, svc, mock_db):
        model = make_mock_model()
        model_id = uuid4()

        # Mock get_model to return our fake model
        svc.get_model = AsyncMock(return_value=model)

        payload = PredictionLogCreate(
            features={"age": 30.0, "income": 50000.0, "city": "NYC"},
            prediction=1.0,
            prediction_proba=0.87,
        )

        # Make refresh populate the log's id
        async def fake_refresh(obj):
            obj.id = str(uuid4())
        mock_db.refresh.side_effect = fake_refresh

        log = await svc.ingest_single(model_id, payload)
        mock_db.add.assert_called_once()
        mock_db.flush.assert_awaited_once()

    async def test_missing_model_raises(self, svc):
        svc.get_model = AsyncMock(return_value=None)
        payload = PredictionLogCreate(features={"age": 30.0}, prediction=1.0)

        with pytest.raises(ValueError, match="not found"):
            await svc.ingest_single(uuid4(), payload)

    async def test_missing_features_warns_but_does_not_raise(self, svc, mock_db):
        model = make_mock_model()
        svc.get_model = AsyncMock(return_value=model)

        # Omit 'city' — should log warning but proceed
        payload = PredictionLogCreate(
            features={"age": 25.0, "income": 40000.0},  # city missing
            prediction=0.0,
        )

        async def fake_refresh(obj):
            obj.id = str(uuid4())
        mock_db.refresh.side_effect = fake_refresh

        # Should not raise
        await svc.ingest_single(uuid4(), payload)
        mock_db.add.assert_called_once()


# ── ingest_batch ─────────────────────────────────────────────────────────────

class TestIngestBatch:
    async def test_batch_inserts_all_records(self, svc, mock_db):
        model = make_mock_model()
        svc.get_model = AsyncMock(return_value=model)

        batch = PredictionLogBatch(
            predictions=[
                PredictionLogCreate(
                    features={"age": float(i), "income": float(i * 1000), "city": "NYC"},
                    prediction=float(i % 2),
                )
                for i in range(50)
            ]
        )

        result = await svc.ingest_batch(uuid4(), batch)

        mock_db.add_all.assert_called_once()
        call_args = mock_db.add_all.call_args[0][0]
        assert len(call_args) == 50
        assert result["ingested"] == 50

    async def test_batch_missing_model_raises(self, svc):
        svc.get_model = AsyncMock(return_value=None)
        batch = PredictionLogBatch(
            predictions=[PredictionLogCreate(features={"age": 1.0}, prediction=0.0)]
        )
        with pytest.raises(ValueError, match="not found"):
            await svc.ingest_batch(uuid4(), batch)


# ── Pydantic schema validation ────────────────────────────────────────────────

class TestSchemas:
    def test_prediction_proba_bounds(self):
        import pytest
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            PredictionLogCreate(
                features={"a": 1},
                prediction=1.0,
                prediction_proba=1.5,  # > 1.0 — invalid
            )

    def test_batch_max_size_enforced(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            PredictionLogBatch(
                predictions=[
                    PredictionLogCreate(features={"a": 1}, prediction=0.0)
                    for _ in range(5001)  # max is 5000
                ]
            )
