import logging
import os
import tempfile

from anyio import Path
from src.core.config import settings
from src.db import AsyncSessionLocal
from taskiq_redis import ListQueueBroker

from common.models import Document
from common.schemas import ParseCVTask
from common.services.storage import S3Service

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] WORKER: %(message)s"
)
logger = logging.getLogger(__name__)

broker = ListQueueBroker(settings.REDIS_URL)
s3_service = S3Service(settings)


@broker.on_event("startup")
async def startup(state) -> None:
    logger.info("Worker started and listening to Taskiq Redis queue...")


@broker.on_event("shutdown")
async def shutdown(state) -> None:
    logger.info("Worker gracefully shutting down.")


@broker.task(task_name="process_cv_task")
async def process_cv_task(task_data: dict) -> bool:
    try:
        task = ParseCVTask.model_validate(task_data)

        async with AsyncSessionLocal() as session:
            doc = await session.get(Document, task.document_id)
            if not doc:
                return False

            if doc.status in ["PROCESSING", "COMPLETED"]:
                return True

            doc.status = "PROCESSING"
            await session.commit()

            local_path = ""
            try:
                temp_dir = tempfile.gettempdir()
                local_path = os.path.join(temp_dir, task.s3_key)

                await s3_service.download_file(task.s3_key, local_path)

                # TODO: Extract text z pliku PDF

                doc.status = "COMPLETED"
                await session.commit()
                return True

            except Exception as e:
                logger.error(f"Error parsing document: {e}")
                doc.status = "FAILED"
                await session.commit()
                return False

            finally:
                if local_path:
                    async_path = Path(local_path)

                    if await async_path.exists():
                        await async_path.unlink()
                        logger.info(f"Cleaned up temporary file: {local_path}")

    except Exception as e:
        logger.error(f"Task payload error: {e}")
        return False
