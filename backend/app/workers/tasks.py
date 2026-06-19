"""
Celery background tasks.
Week 1-2: stub tasks that will be fleshed out in Week 3 (drift engine).
"""

from app.workers.celery_app import celery_app
from app.core.logging import logger


@celery_app.task(bind=True, name="tasks.compute_drift")
def compute_drift(self, model_id: str, window_hours: int = 1) -> dict:
    """
    Compute drift scores for a model over the last N hours.
    Full implementation in Week 3 — drift engine module.
    """
    logger.info("compute_drift_started", model_id=model_id, window_hours=window_hours)
    # TODO: Week 3 — wire in DriftDetector
    return {"status": "pending_implementation", "model_id": model_id}


@celery_app.task(bind=True, name="tasks.trigger_retrain")
def trigger_retrain(self, model_id: str) -> dict:
    """
    Trigger model retraining when drift threshold is exceeded.
    Full implementation in Week 5 — ML pipeline module.
    """
    logger.info("retrain_triggered", model_id=model_id)
    # TODO: Week 5 — wire in training pipeline
    return {"status": "pending_implementation", "model_id": model_id}
