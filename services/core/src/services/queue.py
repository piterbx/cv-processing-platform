import logging

import redis.asyncio as aioredis
from src.core.config import settings
from taskiq.kicker import AsyncKicker
from taskiq_redis import ListQueueBroker

logger = logging.getLogger(__name__)

broker = ListQueueBroker(settings.REDIS_URL)


class QueueService:
    async def connect(self) -> None:
        """Initializes Taskiq and verifies Redis connection independently."""
        try:
            await broker.startup()

            client = aioredis.from_url(settings.REDIS_URL)
            await client.ping()
            await client.aclose()

            logger.info("Taskiq Broker Connection: OK")
        except Exception as e:
            logger.error(f"Taskiq Broker Connection: FAILED | : {e}")
            raise RuntimeError(
                f"Could not connect to Redis at {settings.REDIS_URL}"
            ) from e

    async def disconnect(self) -> None:
        """Closes the Taskiq broker connection gracefully."""
        await broker.shutdown()
        logger.info("Taskiq Broker Connection: Closed")

    async def enqueue_parse_cv(self, task_data: dict):
        """Enqueues a task. If Redis is down, it returns None."""
        try:
            kicker = AsyncKicker(task_name="process_cv_task", broker=broker, labels={})
            job = await kicker.kiq(task_data)
            logger.info(f"Enqueued job {job.task_id} for CV processing")
            return job
        except Exception as e:
            logger.error(f"Failed to enqueue task: {e}")
            return None


queue_service = QueueService()
