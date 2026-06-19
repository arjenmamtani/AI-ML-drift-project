"""
Model registry endpoints.

POST   /api/v1/models        - register a new model
GET    /api/v1/models        - list all models
GET    /api/v1/models/{id}   - get model detail
DELETE /api/v1/models/{id}   - soft-delete (set is_active=False)
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.db_models import MLModel
from app.models.schemas import ModelCreate, ModelResponse

router = APIRouter(prefix="/models", tags=["models"])


@router.post(
    "",
    response_model=ModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new ML model",
)
async def create_model(
    payload: ModelCreate,
    db: AsyncSession = Depends(get_db),
) -> ModelResponse:
    model = MLModel(
        name=payload.name,
        description=payload.description,
        task_type=payload.task_type,
        feature_schema=payload.feature_schema,
    )
    db.add(model)
    await db.flush()
    await db.refresh(model)
    return ModelResponse.model_validate(model)


@router.get(
    "",
    response_model=list[ModelResponse],
    summary="List all registered models",
)
async def list_models(db: AsyncSession = Depends(get_db)) -> list[ModelResponse]:
    result = await db.execute(select(MLModel).order_by(MLModel.created_at.desc()))
    return [ModelResponse.model_validate(m) for m in result.scalars().all()]


@router.get(
    "/{model_id}",
    response_model=ModelResponse,
    summary="Get a model by ID",
)
async def get_model(model_id: UUID, db: AsyncSession = Depends(get_db)) -> ModelResponse:
    result = await db.execute(select(MLModel).where(MLModel.id == str(model_id)))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    return ModelResponse.model_validate(model)


@router.delete("/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_model(model_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    result = await db.execute(select(MLModel).where(MLModel.id == str(model_id)))
    model = result.scalar_one_or_none()
    if model is None:
        raise HTTPException(status_code=404, detail="Model not found")
    model.is_active = False
