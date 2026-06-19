"""
Pydantic v2 schemas for all API request/response bodies.
Kept separate from ORM models intentionally (clean separation of concerns).
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── Model schemas ────────────────────────────────────────────────────────────

class ModelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    description: Optional[str] = None
    task_type: str = Field(..., pattern="^(classification|regression)$")
    feature_schema: dict[str, str] = Field(
        ...,
        description='Map of feature name to dtype, e.g. {"age": "float", "city": "str"}',
    )


class ModelResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    description: Optional[str]
    task_type: str
    feature_schema: dict[str, str]
    is_active: bool
    created_at: datetime


# ── Prediction log schemas ────────────────────────────────────────────────────

class PredictionLogCreate(BaseModel):
    ts: Optional[datetime] = Field(
        default=None,
        description="Timestamp of prediction. Defaults to now() if omitted.",
    )
    features: dict[str, Any] = Field(..., description="Feature values for this prediction")
    prediction: float
    prediction_proba: Optional[float] = Field(None, ge=0.0, le=1.0)
    metadata: Optional[dict[str, Any]] = None

    @field_validator("prediction_proba")
    @classmethod
    def proba_only_for_classifiers(cls, v: Optional[float]) -> Optional[float]:
        return v  # validation against task_type happens in the service layer


class PredictionLogBatch(BaseModel):
    predictions: list[PredictionLogCreate] = Field(..., min_length=1, max_length=5000)


class PredictionLogResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    model_id: UUID
    ts: datetime
    features: dict[str, Any]
    prediction: float
    prediction_proba: Optional[float]
    ground_truth: Optional[float]


class GroundTruthUpdate(BaseModel):
    prediction_id: UUID
    ground_truth: float


class GroundTruthBatch(BaseModel):
    updates: list[GroundTruthUpdate] = Field(..., min_length=1, max_length=5000)


# ── Drift report schemas ──────────────────────────────────────────────────────

class DriftReportResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    model_id: UUID
    window_start: datetime
    window_end: datetime
    feature_name: str
    test_type: str
    drift_score: float
    p_value: Optional[float]
    is_drifted: bool
    threshold: float
    sample_size: int
    created_at: datetime


class DriftSummary(BaseModel):
    model_id: UUID
    window_start: datetime
    window_end: datetime
    total_features: int
    drifted_features: int
    drift_ratio: float
    reports: list[DriftReportResponse]


# ── Alert schemas ─────────────────────────────────────────────────────────────

class AlertResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    model_id: UUID
    alert_type: str
    severity: str
    title: str
    details: Optional[dict[str, Any]]
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime]


# ── Health check ──────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    db: str
    redis: str
    version: str = "0.1.0"
