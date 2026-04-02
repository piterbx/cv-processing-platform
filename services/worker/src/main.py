import json
import logging
import tempfile

import redis.asyncio as aioredis
from anyio import Path
from sqlalchemy.exc import IntegrityError
from src.core.config import settings
from src.db import AsyncSessionLocal
from src.services.ai_service import AIService
from src.services.censor_service import CensorService
from src.services.hash_service import HashService
from src.services.pdf_service import PDFService
from taskiq_redis import ListQueueBroker

from common.enums import DocumentStatus
from common.models import Document
from common.schemas import GenerateEmbeddingsTask, ParseCVTask, TaskName
from common.services.storage import S3Service
from common.services.vector_service import VectorService

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] WORKER: %(message)s"
)
logger = logging.getLogger(__name__)

broker = ListQueueBroker(settings.REDIS_URL)
s3_service = S3Service(settings)
redis_client = aioredis.from_url(
    settings.REDIS_URL, decode_responses=True, max_connections=10
)


async def notify_status_change(
    document_id: int, status: DocumentStatus, step: str = None
):
    """Broadcats status to Redis Pub/Sub."""
    try:
        payload = {"status": status, "document_id": document_id}
        if step:
            payload["step"] = step

        await redis_client.publish(
            f"document_status_{document_id}", json.dumps(payload)
        )
    except Exception as e:
        logger.error(f"Redis Notify Error: {e}")


async def set_status(session, doc, status: DocumentStatus, step: str = None):
    """Helper to commit status to DB and notify Redis in one line."""
    doc.status = status
    await session.commit()
    await session.refresh(doc)
    await notify_status_change(doc.id, status, step)


@broker.on_event("startup")
async def startup(state) -> None:
    logger.info("Worker started and listening to Taskiq Redis queue...")


@broker.on_event("shutdown")
async def shutdown(state) -> None:
    await redis_client.aclose()
    logger.info("Worker gracefully shutting down.")


@broker.task(task_name=TaskName.PARSE_CV)
async def process_cv_task(task_data: dict) -> bool:
    local_path = ""
    try:
        task = ParseCVTask.model_validate(task_data)

        async with AsyncSessionLocal() as session:
            try:
                doc = await session.get(Document, task.document_id)
                if not doc or doc.status in [
                    DocumentStatus.PROCESSING,
                    DocumentStatus.COMPLETED,
                    DocumentStatus.DUPLICATE,
                    DocumentStatus.AWAITING_REVIEW,
                ]:
                    return True

                # download phase
                with tempfile.NamedTemporaryFile(
                    delete=False, suffix=".pdf"
                ) as tmp_file:
                    local_path = tmp_file.name

                await set_status(
                    session, doc, DocumentStatus.PROCESSING, "Downloading from S3..."
                )
                await s3_service.download_file(task.s3_key, local_path)

                # text extraction
                await set_status(
                    session, doc, DocumentStatus.PROCESSING, "Extracting text..."
                )
                raw_text = await PDFService.extract_text(local_path)
                if not raw_text:
                    await set_status(
                        session, doc, DocumentStatus.FAILED, "PDF content is empty"
                    )
                    return True

                # hashing & duplicate detection
                doc.content_hash = HashService.generate_text_hash(raw_text)
                try:
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.PROCESSING,
                        "Checking for duplicates...",
                    )
                except IntegrityError:
                    await session.rollback()
                    doc = await session.get(Document, task.document_id)
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.DUPLICATE,
                        "Exact content duplicate detected",
                    )
                    return True

                # AI Processing
                await set_status(
                    session,
                    doc,
                    DocumentStatus.PROCESSING,
                    "Anonymizing & Analyzing AI data...",
                )
                contact_info = CensorService.extract_contact_info(raw_text)

                safe_text = CensorService.anonymize_text(raw_text)
                extracted_data = await AIService.extract_cv_data(safe_text)

                if not extracted_data:
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.REQUIRES_MANUAL_REVIEW,
                        "AI failed to parse document",
                    )
                    return True

                doc.parsed_json = extracted_data

                if extracted_data.get("prompt_injection_detected"):
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.REJECTED,
                        "Security risk: Prompt injection detected",
                    )
                    return True

                if "personal_info" not in extracted_data:
                    extracted_data["personal_info"] = {}

                extracted_data["personal_info"]["email"] = contact_info["email"]
                extracted_data["personal_info"]["phone"] = contact_info["phone"]

                doc.parsed_json = extracted_data

                await set_status(session, doc, DocumentStatus.AWAITING_REVIEW)
                return True

            except Exception as processing_error:
                logger.error(
                    f"Error during CV parsing logic: {processing_error}", exc_info=True
                )
                await session.rollback()
                doc = await session.get(Document, task.document_id)
                if doc:
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.FAILED,
                        f"Internal processing error: {str(processing_error)}",
                    )
                return False

    except Exception as e:
        logger.error(f"Critical wrapper error parsing document: {e}", exc_info=True)
        return False

    finally:
        if local_path:
            path_obj = Path(local_path)
            if await path_obj.exists():
                try:
                    await path_obj.unlink()
                    logger.info(f"Cleaned up temporary file: {local_path}")
                except Exception as cleanup_error:
                    logger.warning(
                        f"Failed to delete temp file {local_path}: {cleanup_error}"
                    )


@broker.task(task_name=TaskName.GENERATE_EMBEDDINGS)
async def generate_embeddings_task(task_data: dict) -> bool:
    try:
        task = GenerateEmbeddingsTask.model_validate(task_data)
        document_id = task.document_id

        async with AsyncSessionLocal() as session:
            try:
                doc = await session.get(Document, document_id)

                if not doc or doc.status != DocumentStatus.APPROVED:
                    logger.warning(
                        "Task GENERATE_EMBEDDINGS ignored. "
                        f"Document {document_id} status is not APPROVED."
                    )
                    return True

                await set_status(
                    session,
                    doc,
                    DocumentStatus.INDEXING,
                    "Generating semantic embeddings...",
                )

                extracted_data = doc.parsed_json

                if not extracted_data:
                    await set_status(
                        session, doc, DocumentStatus.FAILED, "Parsed JSON is missing"
                    )
                    return True

                text_to_embed = VectorService.prepare_text_for_embedding(extracted_data)
                embedding_vector = await VectorService.generate_embedding_with_retry(
                    text=text_to_embed,
                    host=settings.OLLAMA_HOST,
                    model_name=settings.OLLAMA_EMBEDDING_MODEL,
                    num_ctx=settings.OLLAMA_EMBEDDING_NUM_CTX,
                    temperature=settings.OLLAMA_EMBEDDING_TEMPERATURE,
                )

                if embedding_vector:
                    doc.embedding = embedding_vector
                    await set_status(session, doc, DocumentStatus.COMPLETED)
                else:
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.FAILED,
                        "Embedding generation failed",
                    )

                return True

            except Exception as processing_error:
                logger.error(
                    f"Error during embedding generation: {processing_error}",
                    exc_info=True,
                )
                await session.rollback()
                doc = await session.get(Document, document_id)
                if doc:
                    await set_status(
                        session,
                        doc,
                        DocumentStatus.FAILED,
                        f"Internal processing error: {str(processing_error)}",
                    )
                return False

    except Exception as e:
        logger.error(
            f"Critical wrapper error generating embeddings: {e}", exc_info=True
        )
        return False
