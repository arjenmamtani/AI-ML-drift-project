"""
Ingestion API endpoints.

POST /api/v1/models/{model_id}/predictions        - single prediction
POST /api/v1/models/{model_id}/predictions/batch  - batch ingestion (up to 5000)
PATCH /api/v1/models/{model_id}/ground-truth      - reconcile delayed labels
GET  /api/v1/models/{model_id}/predictions        - paginated log retrieval
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db_models import PredictionLog
from app.models.schemas import (
    GroundTruthBatch,
    PredictionLogBatch,
    PredictionLogCreate,
    PredictionLogResponse,
)
from app.services.ingestion import IngestionService

router = APIRouter(prefix="/models/{model_id}/predictions", tags=["ingestion"])


@router.post(
    "",
    response_model=PredictionLogResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a single prediction",
)
async def ingest_prediction(
    model_id: UUID,
    payload: PredictionLogCreate,
    db: AsyncSession = Depends(get_db),
) -> PredictionLogResponse:
    svc = IngestionService(db)
    try:
        log = await svc.ingest_single(model_id, payload)
        return PredictionLogResponse.model_validate(log)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/batch",
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a batch of predictions (max 5000)",
)
async def ingest_batch(
    model_id: UUID,
    batch: PredictionLogBatch,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = IngestionService(db)
    try:
        return await svc.ingest_batch(model_id, batch)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch(
    "/ground-truth",
    summary="Reconcile delayed ground-truth labels",
)
async def update_ground_truth(
    model_id: UUID,
    batch: GroundTruthBatch,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = IngestionService(db)
    return await svc.update_ground_truth(model_id, batch)


@router.get(
    "",
    response_model=list[PredictionLogResponse],
    summary="Retrieve paginated prediction logs",
)
async def list_predictions(
    model_id: UUID,
    limit: int = Query(default=100, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[PredictionLogResponse]:
    result = await db.execute(
        select(PredictionLog)
        .where(PredictionLog.model_id == str(model_id))
        .order_by(PredictionLog.ts.desc())
        .limit(limit)
        .offset(offset)
    )
    logs = result.scalars().all()
    return [PredictionLogResponse.model_validate(l) for l in logs]
