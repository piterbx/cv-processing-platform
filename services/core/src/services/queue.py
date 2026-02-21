import logging

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from src.core.config import settings

logger = logging.getLogger(__name__)


class QueueService:
    def __init__(self):
        self.redis_pool: ArqRedis | None = None

    async def connect(self) -> None:
        """Initializes the Redis connection pool using environment variables."""
        try:
            self.redis_pool = await create_pool(
                RedisSettings(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                )
            )
            logger.info("Redis Queue Connection: OK")
        except Exception as e:
            logger.error(f"Redis Queue Connection: FAILED | {e}")
            raise

    async def disconnect(self) -> None:
        """Closes the Redis connection pool gracefully on server shutdown."""
        if self.redis_pool:
            await self.redis_pool.close()
            logger.info("Redis Queue Connection: Closed")

    async def enqueue_parse_cv(self, task_data: dict):
        """Enqueues a CV processing task into the ARQ queue."""
        if not self.redis_pool:
            logger.error("Redis pool is not initialized. Cannot enqueue task.")
            return None

        # 'process_cv_task' must match the exact function name in the Worker service
        job = await self.redis_pool.enqueue_job("process_cv_task", task_data)

        if job:
            logger.info(f"Enqueued job {job.job_id} for CV processing")
        return job


queue_service = QueueService()
