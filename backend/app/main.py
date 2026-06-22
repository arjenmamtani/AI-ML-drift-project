"""
Drift Sentinel — FastAPI application entry point.

Startup order:
  1. Logging setup
  2. Database init (creates tables + TimescaleDB hypertable)
  3. API router registration
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import drift, health, ingestion, models as models_router
from app.core.init_db import init_db
from app.core.logging import logger, setup_logging


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
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(health.router)
app.include_router(models_router.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(drift.router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    return {"service": "Drift Sentinel", "docs": "/docs"}
