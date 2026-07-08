"""
Training API endpoints.

POST /api/v1/models/{model_id}/train   - train a new model version now
"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.training import TrainingService

router = APIRouter(prefix="/models/{model_id}", tags=["training"])


@router.post(
    "/train",
    summary="Train a new model version using reconciled labeled data",
)
async def train_model(
    model_id: UUID,
    test_size: float = Query(default=0.2, ge=0.05, le=0.5),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    svc = TrainingService(db)
    try:
        return await svc.train(model_id, test_size=test_size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
