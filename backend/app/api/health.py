from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.schemas import HealthResponse

import redis.asyncio as aioredis

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="System health check")
async def health(db: AsyncSession = Depends(get_db)) -> HealthResponse:
    # Check DB
    db_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {e}"

    # Check Redis
    redis_status = "ok"
    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
    except Exception as e:
        redis_status = f"error: {e}"

    overall = "healthy" if db_status == "ok" and redis_status == "ok" else "degraded"

    return HealthResponse(status=overall, db=db_status, redis=redis_status)
