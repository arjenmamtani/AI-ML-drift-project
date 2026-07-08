"""
Training pipeline.

Pulls labeled prediction logs (rows where ground_truth has been reconciled)
for a model, trains a fresh XGBoost classifier/regressor, evaluates it,
logs everything to MLflow, and computes SHAP feature importances.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.db_models import MLModel, PredictionLog

MIN_TRAINING_SAMPLES = 50


class TrainingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _fetch_labeled_data(self, model_id: UUID) -> pd.DataFrame:
        result = await self.db.execute(
            select(PredictionLog).where(
                PredictionLog.model_id == str(model_id),
                PredictionLog.ground_truth.is_not(None),
            )
        )
        logs = result.scalars().all()

        if not logs:
            return pd.DataFrame()

        rows = []
        for log in logs:
            row = dict(log.features)
            row["__ground_truth__"] = log.ground_truth
            rows.append(row)

        return pd.DataFrame(rows)

    async def train(
        self,
        model_id: UUID,
        test_size: float = 0.2,
        random_state: int = 42,
    ) -> dict[str, Any]:
        # Lazy imports — keeps mlflow out of module-level scope so tests
        # that don't use training can collect without pkg_resources installed.
        import mlflow
        import shap
        from xgboost import XGBClassifier, XGBRegressor
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import (
            accuracy_score, f1_score, mean_squared_error,
            precision_score, r2_score, recall_score, roc_auc_score,
        )

        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)

        model_result = await self.db.execute(
            select(MLModel).where(MLModel.id == str(model_id))
        )
        model = model_result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Model {model_id} not found")

        df = await self._fetch_labeled_data(model_id)

        if len(df) < MIN_TRAINING_SAMPLES:
            raise ValueError(
                f"Insufficient labeled data: {len(df)} samples found, "
                f"need at least {MIN_TRAINING_SAMPLES}. "
                f"Reconcile ground truth via PATCH /predictions/ground-truth first."
            )

        feature_cols = [c for c in df.columns if c != "__ground_truth__"]
        X = df[feature_cols]
        y = df["__ground_truth__"]

        X = pd.get_dummies(X, drop_first=False)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state
        )

        is_classification = model.task_type == "classification"
        experiment_name = f"drift-sentinel-{model.name}"
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run(run_name=f"retrain-{datetime.now(timezone.utc).isoformat()}") as run:
            mlflow.log_param("task_type", model.task_type)
            mlflow.log_param("n_samples", len(df))
            mlflow.log_param("n_features", X.shape[1])
            mlflow.log_param("test_size", test_size)

            if is_classification:
                clf = XGBClassifier(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.1,
                    eval_metric="logloss",
                    random_state=random_state,
                )
                clf.fit(X_train, y_train)
                y_pred = clf.predict(X_test)
                y_proba = clf.predict_proba(X_test)[:, 1] if len(set(y)) == 2 else None

                metrics = {
                    "accuracy": float(accuracy_score(y_test, y_pred)),
                    "precision": float(precision_score(y_test, y_pred, zero_division=0)),
                    "recall": float(recall_score(y_test, y_pred, zero_division=0)),
                    "f1": float(f1_score(y_test, y_pred, zero_division=0)),
                }
                if y_proba is not None:
                    try:
                        metrics["roc_auc"] = float(roc_auc_score(y_test, y_proba))
                    except ValueError:
                        pass

                trained_model = clf
            else:
                reg = XGBRegressor(
                    n_estimators=100,
                    max_depth=4,
                    learning_rate=0.1,
                    random_state=random_state,
                )
                reg.fit(X_train, y_train)
                y_pred = reg.predict(X_test)

                metrics = {
                    "rmse": float(np.sqrt(mean_squared_error(y_test, y_pred))),
                    "r2": float(r2_score(y_test, y_pred)),
                }
                trained_model = reg

            for metric_name, value in metrics.items():
                mlflow.log_metric(metric_name, value)

            explainer = shap.TreeExplainer(trained_model)
            shap_values = explainer.shap_values(X_test)

            if isinstance(shap_values, list):
                shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

            mean_abs_shap = np.abs(shap_values).mean(axis=0)
            feature_importance = dict(
                sorted(
                    zip(X.columns.tolist(), mean_abs_shap.tolist()),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )

            for feat, importance in list(feature_importance.items())[:10]:
                mlflow.log_metric(f"shap_importance_{feat}", importance)

            mlflow.xgboost.log_model(trained_model, name="model")
            run_id = run.info.run_id

        logger.info(
            "model_trained",
            model=model.name,
            run_id=run_id,
            n_samples=len(df),
            metrics=metrics,
        )

        return {
            "model_id": str(model_id),
            "model_name": model.name,
            "mlflow_run_id": run_id,
            "n_training_samples": len(df),
            "metrics": metrics,
            "feature_importance": feature_importance,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }