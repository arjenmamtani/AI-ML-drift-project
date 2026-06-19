"""
ORM models for Drift Sentinel.

Tables:
  - models          : registered ML models
  - prediction_logs : every prediction ingested (TimescaleDB hypertable on ts)
  - drift_reports   : computed drift scores per window
  - alerts          : triggered alerts with status tracking
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB as _PG_JSONB, UUID
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship

from app.core.database import Base


class JSONB(TypeDecorator):
    """
    Dialect-aware JSON/JSONB type.
    Uses native JSONB on PostgreSQL (better indexing + operators),
    falls back to plain JSON on SQLite (used in tests).
    """
    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PG_JSONB())
        return dialect.type_descriptor(JSON())


def new_uuid() -> str:
    return str(uuid.uuid4())


class MLModel(Base):
    __tablename__ = "models"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    name = Column(String(120), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    task_type = Column(String(50), nullable=False)  # classification | regression
    feature_schema = Column(JSONB, nullable=False)  # {"feature_name": "dtype", ...}
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    prediction_logs = relationship("PredictionLog", back_populates="model", lazy="dynamic")
    drift_reports = relationship("DriftReport", back_populates="model", lazy="dynamic")
    alerts = relationship("Alert", back_populates="model", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<MLModel {self.name}>"


class PredictionLog(Base):
    """
    Core ingest table. Will be converted to a TimescaleDB hypertable on `ts`.
    Each row is one prediction event from a deployed model.
    """

    __tablename__ = "prediction_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    ts = Column(DateTime(timezone=True), primary_key=True, nullable=False, index=True)
    model_id = Column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False, index=True)
    features = Column(JSONB, nullable=False)
    prediction = Column(Float, nullable=False)
    prediction_proba = Column(Float, nullable=True)
    ground_truth = Column(Float, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True)

    model = relationship("MLModel", back_populates="prediction_logs")

    def __repr__(self) -> str:
        return f"<PredictionLog {self.model_id} @ {self.ts}>"


class DriftReport(Base):
    __tablename__ = "drift_reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    model_id = Column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False, index=True)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    feature_name = Column(String(120), nullable=False)
    test_type = Column(String(50), nullable=False)
    drift_score = Column(Float, nullable=False)
    p_value = Column(Float, nullable=True)
    is_drifted = Column(Boolean, nullable=False, default=False)
    threshold = Column(Float, nullable=False)
    sample_size = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    model = relationship("MLModel", back_populates="drift_reports")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    model_id = Column(UUID(as_uuid=False), ForeignKey("models.id"), nullable=False, index=True)
    alert_type = Column(String(80), nullable=False)
    severity = Column(String(20), nullable=False)
    title = Column(String(255), nullable=False)
    details = Column(JSONB, nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    model = relationship("MLModel", back_populates="alerts")
