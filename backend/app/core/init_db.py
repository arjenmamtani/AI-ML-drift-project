"""
Database initialisation: creates all tables and enables the TimescaleDB
hypertable on prediction_logs.ts for efficient time-series querying.

Run once on startup via app/main.py lifespan handler.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.logging import logger

# Import all models so Base.metadata is populated
from app.models.db_models import Alert, DriftReport, MLModel, PredictionLog  # noqa: F401


async def init_db() -> None:
    engine = create_async_engine(settings.database_url, echo=False)

    async with engine.begin() as conn:
        logger.info("Creating database tables...")
        await conn.run_sync(Base.metadata.create_all)

        # Enable TimescaleDB extension (idempotent)
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"))

        # Convert prediction_logs to a hypertable partitioned by hour
        # IF NOT EXISTS guard makes this idempotent
        await conn.execute(
            text("""
                SELECT create_hypertable(
                    'prediction_logs',
                    'ts',
                    chunk_time_interval => INTERVAL '1 hour',
                    if_not_exists => TRUE
                );
            """)
        )

        # Useful index for model+time range queries
        await conn.execute(
            text("""
                CREATE INDEX IF NOT EXISTS ix_prediction_logs_model_ts
                ON prediction_logs (model_id, ts DESC);
            """)
        )

        logger.info("Database initialised successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
