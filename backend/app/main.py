"""
Drift Sentinel — FastAPI application entry point.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import auth, drift, health, ingestion, models as models_router, training
from app.core.init_db import init_db
from app.core.logging import logger, setup_logging
from app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("drift_sentinel_starting")
    await init_db()
    logger.info("drift_sentinel_ready")
    yield
    logger.info("drift_sentinel_shutdown")


app = FastAPI(
    title="Drift Sentinel",
    description=(
        "Production ML monitoring platform — detects data drift, model degradation, "
        "and triggers automated retraining."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(models_router.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(drift.router, prefix="/api/v1")
app.include_router(training.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Drift Sentinel", "version": "0.2.0", "docs": "/docs"}
