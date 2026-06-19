"""
Integration tests for the ingestion and model registry API.
Uses an in-memory SQLite database so no real Postgres is needed.
"""

import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app

TEST_DATABASE_URL = "sqlite+aiosqlite://"  # pure in-memory, fresh per session

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest.fixture
async def client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def unique_name(prefix: str) -> str:
    """Generate a unique model name to avoid unique-constraint collisions."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


class TestModelRegistry:
    async def test_create_model(self, client):
        response = await client.post(
            "/api/v1/models",
            json={
                "name": unique_name("credit-risk"),
                "description": "Binary credit risk classifier",
                "task_type": "classification",
                "feature_schema": {
                    "age": "float",
                    "income": "float",
                    "loan_amount": "float",
                    "credit_score": "float",
                },
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["task_type"] == "classification"
        assert "id" in data

    async def test_list_models(self, client):
        response = await client.get("/api/v1/models")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    async def test_get_model_not_found(self, client):
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = await client.get(f"/api/v1/models/{fake_id}")
        assert response.status_code == 404

    async def test_duplicate_model_name_fails(self, client):
        name = unique_name("duplicate")
        payload = {"name": name, "task_type": "regression", "feature_schema": {"x": "float"}}
        r1 = await client.post("/api/v1/models", json=payload)
        assert r1.status_code == 201
        import pytest
        with pytest.raises(Exception):
            r2 = await client.post("/api/v1/models", json=payload)
            assert r2.status_code in (409, 422, 500)


class TestIngestion:
    @pytest.fixture
    async def model_id(self, client) -> str:
        response = await client.post(
            "/api/v1/models",
            json={
                "name": unique_name("ingestion-model"),
                "task_type": "classification",
                "feature_schema": {"age": "float", "income": "float"},
            },
        )
        assert response.status_code == 201
        return response.json()["id"]

    async def test_ingest_single_prediction(self, client, model_id):
        response = await client.post(
            f"/api/v1/models/{model_id}/predictions",
            json={
                "features": {"age": 35.0, "income": 60000.0},
                "prediction": 1.0,
                "prediction_proba": 0.82,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["prediction"] == 1.0
        assert data["prediction_proba"] == 0.82
        assert data["ground_truth"] is None

    async def test_ingest_batch(self, client, model_id):
        predictions = [
            {
                "features": {"age": float(20 + i), "income": float(30000 + i * 500)},
                "prediction": float(i % 2),
                "prediction_proba": round(0.5 + (i % 10) * 0.04, 2),
            }
            for i in range(100)
        ]
        response = await client.post(
            f"/api/v1/models/{model_id}/predictions/batch",
            json={"predictions": predictions},
        )
        assert response.status_code == 201
        assert response.json()["ingested"] == 100

    async def test_list_predictions_paginated(self, client, model_id):
        response = await client.get(
            f"/api/v1/models/{model_id}/predictions?limit=10&offset=0"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) <= 10

    async def test_ingest_to_nonexistent_model(self, client):
        fake_id = "00000000-0000-0000-0000-000000000099"
        response = await client.post(
            f"/api/v1/models/{fake_id}/predictions",
            json={"features": {"age": 30.0}, "prediction": 1.0},
        )
        assert response.status_code == 404
