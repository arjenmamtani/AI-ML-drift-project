"""
Celery background tasks.

compute_drift runs the real DriftEngine. trigger_retrain runs the real
TrainingService. Celery tasks are sync by default, so we spin up a
short-lived asyncio event loop per task to drive our async SQLAlchemy
session — the standard pattern for mixing Celery with an async-first
codebase.
"""

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import logger
from app.drift.engine import DriftEngine
from app.services.training import TrainingService
from app.workers.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from inside a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _compute_drift_async(model_id: str, window_hours: int) -> dict:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        drift_engine = DriftEngine(session)
        result = await drift_engine.compute_drift_report(model_id, window_hours=window_hours)
        await session.commit()

    await engine.dispose()
    return result


async def _trigger_retrain_async(model_id: str) -> dict:
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        training_service = TrainingService(session)
        result = await training_service.train(model_id)
        await session.commit()

    await engine.dispose()
    return result


@celery_app.task(bind=True, name="tasks.compute_drift", max_retries=3)
def compute_drift(self, model_id: str, window_hours: int = 1) -> dict:
    """
    Compute drift scores for a model over the last N hours.
    Scheduled periodically (see celery beat config) or triggered manually
    via POST /api/v1/models/{id}/drift/compute.
    """
    logger.info("compute_drift_task_started", model_id=model_id, window_hours=window_hours)
    try:
        result = _run_async(_compute_drift_async(model_id, window_hours))
        logger.info("compute_drift_task_completed", model_id=model_id, **result)

        if result.get("drift_ratio", 0) > 0.3:
            logger.warning(
                "high_drift_detected_triggering_retrain",
                model_id=model_id,
                drift_ratio=result["drift_ratio"],
            )
            trigger_retrain.delay(model_id)

        return result
    except Exception as exc:
        logger.error("compute_drift_task_failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, name="tasks.trigger_retrain", max_retries=2)
def trigger_retrain(self, model_id: str) -> dict:
    """
    Retrain a model using reconciled labeled data, triggered automatically
    when compute_drift detects drift_ratio > 0.3, or manually via
    POST /api/v1/models/{id}/train.
    """
    logger.info("retrain_task_started", model_id=model_id)
    try:
        result = _run_async(_trigger_retrain_async(model_id))
        logger.info("retrain_task_completed", model_id=model_id, run_id=result.get("mlflow_run_id"))
        return result
    except ValueError as exc:
        # Insufficient labeled data — don't retry, this needs human intervention
        # (i.e. someone needs to reconcile more ground truth labels first)
        logger.warning("retrain_skipped_insufficient_data", model_id=model_id, reason=str(exc))
        return {"status": "skipped", "reason": str(exc)}
    except Exception as exc:
        logger.error("retrain_task_failed", model_id=model_id, error=str(exc))
        raise self.retry(exc=exc, countdown=60)
