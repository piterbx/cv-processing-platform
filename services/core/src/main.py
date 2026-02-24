import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text
from src.api.router import api_router
from src.db.session import engine
from src.services.queue import queue_service
from src.services.storage import storage_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("[SYSTEM CHECK] Starting services...")

    # health check S3
    try:
        await storage_service.check_bucket_exists()
        logger.info("S3 Connection: OK")
    except Exception as e:
        logger.critical(f"S3 Connection: FAILED | {e}")
        raise RuntimeError("Failed to connect to S3") from e

    # health check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database Connection: OK")
    except Exception as e:
        logger.critical(f"Database Connection: FAILED | {e}")
        raise RuntimeError("Failed to connect to Database") from e

    # health check queue
    try:
        await queue_service.connect()
        logger.info("Redis Connection: OK")
    except Exception as e:
        logger.critical(f"Redis Connection: FAILED | {e}")
        raise RuntimeError("Failed to connect to Redis") from e

    logger.info("[SYSTEM CHECK] Complete. Application is ready.")

    yield  # app starts

    logger.info("Shutting down... Cleaning up database connections.")
    await queue_service.disconnect()
    await engine.dispose()


app = FastAPI(title="CVPP Core", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
