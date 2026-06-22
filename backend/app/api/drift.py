"""
Drift detection API endpoints.

POST /api/v1/models/{model_id}/drift/compute   - run drift detection now
GET  /api/v1/models/{model_id}/drift/reports    - retrieve historical reports
GET  /api/v1/models/{model_id}/drift/latest     - most recent drift summary
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.drift.engine import DriftEngine
from app.models.db_models import DriftReport
from app.models.schemas import DriftReportResponse

router = APIRouter(prefix="/models/{model_id}/drift", tags=["drift"])


@router.post(
    "/compute",
    summary="Run drift detection for a model right now",
)
async def compute_drift(
    model_id: UUID,
    window_hours: int = Query(default=1, ge=1, le=24),
    reference_hours_back: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    engine = DriftEngine(db)
    try:
        return await engine.compute_drift_report(
            model_id, window_hours=window_hours, reference_hours_back=reference_hours_back
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/reports",
    response_model=list[DriftReportResponse],
    summary="Retrieve historical drift reports for a model",
)
async def list_drift_reports(
    model_id: UUID,
    feature_name: str | None = Query(default=None),
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
) -> list[DriftReportResponse]:
    query = select(DriftReport).where(DriftReport.model_id == str(model_id))
    if feature_name:
        query = query.where(DriftReport.feature_name == feature_name)
    query = query.order_by(DriftReport.created_at.desc()).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()
    return [DriftReportResponse.model_validate(r) for r in reports]


@router.get(
    "/latest",
    summary="Get the most recent drift summary (one row per feature)",
)
async def get_latest_drift(
    model_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    result = await db.execute(
        select(DriftReport)
        .where(DriftReport.model_id == str(model_id))
        .order_by(DriftReport.created_at.desc())
        .limit(50)
    )
    reports = result.scalars().all()

    if not reports:
        return {"model_id": str(model_id), "reports": [], "message": "No drift reports yet"}

    # Keep only the latest report per feature
    latest_by_feature: dict[str, DriftReport] = {}
    for r in reports:
        if r.feature_name not in latest_by_feature:
            latest_by_feature[r.feature_name] = r

    drifted = [name for name, r in latest_by_feature.items() if r.is_drifted]

    return {
        "model_id": str(model_id),
        "total_features": len(latest_by_feature),
        "drifted_features": drifted,
        "drift_ratio": len(drifted) / len(latest_by_feature) if latest_by_feature else 0.0,
        "reports": [
            DriftReportResponse.model_validate(r).model_dump()
            for r in latest_by_feature.values()
        ],
    }
