import json
import logging
import os
import tempfile

from anyio import Path
from sqlalchemy import select
from src.core.config import settings
from src.db import AsyncSessionLocal
from src.services.ai_service import AIService
from src.services.censor_service import CensorService
from src.services.hash_service import HashService
from src.services.pdf_service import PDFService
from taskiq_redis import ListQueueBroker

from common.models import Document
from common.schemas import ParseCVTask
from common.services.storage import S3Service
from common.services.vector_service import VectorService

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

            if doc.status in ["PROCESSING", "COMPLETED", "DUPLICATE"]:
                return True

            doc.status = "PROCESSING"
            await session.commit()

            local_path = ""
            try:
                temp_dir = tempfile.gettempdir()
                local_path = os.path.join(temp_dir, task.s3_key)

                await s3_service.download_file(task.s3_key, local_path)

                raw_text = await PDFService.extract_text(local_path)

                if not raw_text:
                    logger.warning("Empty PDF content for document ID: %s", doc.id)
                    doc.status = "FAILED"
                    await session.commit()
                    return False

                text_hash = HashService.generate_text_hash(raw_text)

                existing_doc_stmt = select(Document).where(
                    Document.content_hash == text_hash, Document.id != doc.id
                )
                existing_doc_result = await session.execute(existing_doc_stmt)

                if existing_doc_result.scalars().first():
                    logger.info(
                        "Exact text duplicate detected for document ID: %s.", doc.id
                    )
                    doc.status = "DUPLICATE"
                    doc.content_hash = text_hash
                    await session.commit()
                    return True

                doc.content_hash = text_hash

                safe_text = CensorService.anonymize_text(raw_text)
                logger.info("Text anonymized successfully. Sending to AI extraction...")

                extracted_data = await AIService.extract_cv_data(safe_text)

                if not extracted_data:
                    logger.warning(
                        "AI extraction failed. Moving document to manual review."
                    )
                    doc.status = "REQUIRES_MANUAL_REVIEW"
                    await session.commit()
                    return True

                logger.info(
                    "AI Extraction COMPLETE! Result:\n%s",
                    json.dumps(extracted_data, indent=2, ensure_ascii=False),
                )

                if not extracted_data.get("prompt_injection_detected"):
                    logger.info("Generating semantic embeddings...")

                    text_to_embed = VectorService.prepare_text_for_embedding(
                        extracted_data
                    )
                    embedding_vector = await VectorService.generate_embedding(
                        text=text_to_embed,
                        host=settings.OLLAMA_HOST,
                        model_name=settings.OLLAMA_EMBEDDING_MODEL,
                    )

                    if embedding_vector:
                        logger.info(
                            "Successfully generated embedding of size: %d",
                            len(embedding_vector),
                        )
                        doc.embedding = embedding_vector
                        doc.parsed_json = extracted_data
                    else:
                        logger.warning("Failed to generate embedding.")
                else:
                    logger.warning(
                        "Skipping vectorization due to detected prompt injection."
                    )

                doc.status = "COMPLETED"
                await session.commit()
                return True

            except Exception as e:
                logger.error(f"Error parsing document: {e}", exc_info=True)
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
        logger.error(f"Task payload error: {e}", exc_info=True)
        return False
