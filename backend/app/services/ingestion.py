"""
Ingestion service: validates and persists prediction logs.

Responsibilities:
  - Validate that incoming feature keys match the model's registered schema
  - Bulk-insert prediction logs efficiently
  - Reconcile ground truth labels when they arrive later
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.models.db_models import MLModel, PredictionLog
from app.models.schemas import GroundTruthBatch, PredictionLogBatch, PredictionLogCreate


class IngestionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_model(self, model_id: UUID) -> MLModel | None:
        result = await self.db.execute(
            select(MLModel).where(MLModel.id == str(model_id), MLModel.is_active == True)
        )
        return result.scalar_one_or_none()

    def _validate_features(
        self, features: dict[str, Any], schema: dict[str, str], model_name: str
    ) -> None:
        """
        Soft validation: warn on missing/extra features but don't reject.
        In production you'd tighten this to raise on missing required features.
        """
        schema_keys = set(schema.keys())
        incoming_keys = set(features.keys())

        missing = schema_keys - incoming_keys
        extra = incoming_keys - schema_keys

        if missing:
            logger.warning(
                "prediction_missing_features",
                model=model_name,
                missing=list(missing),
            )
        if extra:
            logger.warning(
                "prediction_extra_features",
                model=model_name,
                extra=list(extra),
            )

    async def ingest_single(
        self, model_id: UUID, payload: PredictionLogCreate
    ) -> PredictionLog:
        model = await self.get_model(model_id)
        if model is None:
            raise ValueError(f"Model {model_id} not found or inactive")

        self._validate_features(payload.features, model.feature_schema, model.name)

        log = PredictionLog(
            model_id=str(model_id),
            ts=payload.ts or datetime.now(timezone.utc),
            features=payload.features,
            prediction=payload.prediction,
            prediction_proba=payload.prediction_proba,
            metadata_=payload.metadata,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)

        logger.info("prediction_ingested", model=model.name, log_id=log.id)
        return log

    async def ingest_batch(
        self, model_id: UUID, batch: PredictionLogBatch
    ) -> dict[str, Any]:
        model = await self.get_model(model_id)
        if model is None:
            raise ValueError(f"Model {model_id} not found or inactive")

        logs = []
        now = datetime.now(timezone.utc)
        for p in batch.predictions:
            self._validate_features(p.features, model.feature_schema, model.name)
            logs.append(
                PredictionLog(
                    model_id=str(model_id),
                    ts=p.ts or now,
                    features=p.features,
                    prediction=p.prediction,
                    prediction_proba=p.prediction_proba,
                    metadata_=p.metadata,
                )
            )

        self.db.add_all(logs)
        await self.db.flush()

        logger.info("batch_ingested", model=model.name, count=len(logs))
        return {"ingested": len(logs), "model_id": str(model_id)}

    async def update_ground_truth(
        self, model_id: UUID, batch: GroundTruthBatch
    ) -> dict[str, Any]:
        """
        Reconcile delayed ground-truth labels with existing prediction logs.
        This is how we compute real accuracy metrics over time.
        """
        updated = 0
        for item in batch.updates:
            result = await self.db.execute(
                update(PredictionLog)
                .where(
                    PredictionLog.id == str(item.prediction_id),
                    PredictionLog.model_id == str(model_id),
                )
                .values(ground_truth=item.ground_truth)
            )
            updated += result.rowcount

        logger.info("ground_truth_updated", model_id=str(model_id), count=updated)
        return {"updated": updated}
