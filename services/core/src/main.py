import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from src.api.router import api_router
from src.db.session import engine
from src.services.storage import storage_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[SYSTEM CHECK] Starting services...")

    # health check S3
    try:
        await storage_service.ensure_bucket_exists()
        logger.info("S3 Connection: OK")
    except Exception as e:
        logger.error(f"S3 Connection: FAILED | {e}")

    # health check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database Connection: OK")
    except Exception as e:
        logger.error(f"Database Connection: FAILED | {e}")

    logger.info("[SYSTEM CHECK] Complete")

    yield  # app starts

    logger.info("Shutting down... Cleaning up database connections.")
    await engine.dispose()


app = FastAPI(title="CVPP Core", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
