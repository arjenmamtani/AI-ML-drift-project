"""
DriftEngine: orchestrates the end-to-end drift detection workflow.

Responsibilities:
  1. Pull a reference window (baseline) and current window of prediction
     logs for a given model from TimescaleDB
  2. For each feature in the model's schema, run the appropriate test
     (KS for numeric, chi-squared for categorical)
  3. Also check the prediction distribution itself for drift (covers
     cases where the model's output shifts even if inputs look stable)
  4. Persist results as DriftReport rows
  5. Return a summary so callers (API, Celery task) can decide whether
     to fire an alert or trigger retraining
"""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.drift.detectors import DriftResult, categorical_drift, ks_test
from app.models.db_models import DriftReport, MLModel, PredictionLog

NUMERIC_DTYPES = {"float", "int", "number"}
CATEGORICAL_DTYPES = {"str", "category", "categorical"}

# Minimum samples required per window before we trust a drift test.
# Statistical tests are unreliable on tiny samples.
MIN_SAMPLE_SIZE = 30


class DriftEngine:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _fetch_window(
        self, model_id: UUID, start: datetime, end: datetime
    ) -> list[PredictionLog]:
        result = await self.db.execute(
            select(PredictionLog)
            .where(
                PredictionLog.model_id == str(model_id),
                PredictionLog.ts >= start,
                PredictionLog.ts < end,
            )
            .order_by(PredictionLog.ts)
        )
        return list(result.scalars().all())

    def _extract_feature_values(
        self, logs: list[PredictionLog], feature_name: str
    ) -> list:
        values = []
        for log in logs:
            v = log.features.get(feature_name)
            if v is not None:
                values.append(v)
        return values

    def _infer_is_numeric(self, dtype: str) -> bool:
        return dtype.lower() in NUMERIC_DTYPES

    def _run_feature_test(
        self, feature_name: str, dtype: str, ref_values: list, cur_values: list
    ) -> DriftResult | None:
        if len(ref_values) < MIN_SAMPLE_SIZE or len(cur_values) < MIN_SAMPLE_SIZE:
            logger.warning(
                "drift_test_skipped_insufficient_samples",
                feature=feature_name,
                ref_n=len(ref_values),
                cur_n=len(cur_values),
                min_required=MIN_SAMPLE_SIZE,
            )
            return None

        if self._infer_is_numeric(dtype):
            ref_arr = np.array(ref_values, dtype=float)
            cur_arr = np.array(cur_values, dtype=float)
            return ks_test(ref_arr, cur_arr)
        else:
            return categorical_drift(
                [str(v) for v in ref_values], [str(v) for v in cur_values]
            )

    async def compute_drift_report(
        self,
        model_id: UUID,
        window_hours: int = 1,
        reference_hours_back: int = 24,
    ) -> dict:
        """
        Compare a recent "current" window against an older "reference" window.

        Default setup: reference = the 24-hour period ending `window_hours`
        ago, current = the most recent `window_hours`.
        """
        model_result = await self.db.execute(
            select(MLModel).where(MLModel.id == str(model_id))
        )
        model = model_result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Model {model_id} not found")

        now = datetime.now(timezone.utc)
        current_start = now - timedelta(hours=window_hours)
        current_end = now
        reference_end = current_start
        reference_start = reference_end - timedelta(hours=reference_hours_back)

        current_logs = await self._fetch_window(model_id, current_start, current_end)
        reference_logs = await self._fetch_window(model_id, reference_start, reference_end)

        logger.info(
            "drift_window_fetched",
            model=model.name,
            current_n=len(current_logs),
            reference_n=len(reference_logs),
        )

        reports: list[DriftReport] = []
        feature_results: dict[str, DriftResult] = {}

        for feature_name, dtype in model.feature_schema.items():
            ref_values = self._extract_feature_values(reference_logs, feature_name)
            cur_values = self._extract_feature_values(current_logs, feature_name)

            result = self._run_feature_test(feature_name, dtype, ref_values, cur_values)
            if result is None:
                continue

            feature_results[feature_name] = result
            reports.append(
                DriftReport(
                    model_id=str(model_id),
                    window_start=current_start,
                    window_end=current_end,
                    feature_name=feature_name,
                    test_type=result.test_type,
                    drift_score=result.drift_score,
                    p_value=result.p_value,
                    is_drifted=result.is_drifted,
                    threshold=result.threshold,
                    sample_size=result.sample_size,
                )
            )

        # Also check the prediction output distribution itself —
        # catches concept drift even when inputs look stable.
        ref_preds = [log.prediction for log in reference_logs]
        cur_preds = [log.prediction for log in current_logs]
        if len(ref_preds) >= MIN_SAMPLE_SIZE and len(cur_preds) >= MIN_SAMPLE_SIZE:
            pred_result = ks_test(np.array(ref_preds), np.array(cur_preds))
            feature_results["__prediction__"] = pred_result
            reports.append(
                DriftReport(
                    model_id=str(model_id),
                    window_start=current_start,
                    window_end=current_end,
                    feature_name="__prediction__",
                    test_type=pred_result.test_type,
                    drift_score=pred_result.drift_score,
                    p_value=pred_result.p_value,
                    is_drifted=pred_result.is_drifted,
                    threshold=pred_result.threshold,
                    sample_size=pred_result.sample_size,
                )
            )

        self.db.add_all(reports)
        await self.db.flush()

        drifted_features = [name for name, r in feature_results.items() if r.is_drifted]

        summary = {
            "model_id": str(model_id),
            "model_name": model.name,
            "window_start": current_start.isoformat(),
            "window_end": current_end.isoformat(),
            "total_features_tested": len(feature_results),
            "drifted_features": drifted_features,
            "drift_ratio": (
                len(drifted_features) / len(feature_results) if feature_results else 0.0
            ),
            "reports_created": len(reports),
        }

        logger.info("drift_report_computed", **summary)
        return summary
