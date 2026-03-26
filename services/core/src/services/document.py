import asyncio
import hashlib
import json
import logging
import uuid
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.schemas.document import DocumentUpload
from src.services.queue import queue_service
from src.services.storage import storage_service

from common import S3UploadError
from common.models import Document
from common.schemas import ParseCVTask

logger = logging.getLogger(__name__)


class DocumentService:
    async def get_all_documents(self, db: AsyncSession, skip: int, limit: int):
        query = (
            select(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def create_document(self, db: AsyncSession, upload_data: DocumentUpload):
        file = upload_data.file
        file_content = await file.read()

        await self._check_exact_duplicate(db, file_content)
        await file.seek(0)

        file_hash = hashlib.sha256(file_content).hexdigest()
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "pdf"
        s3_key = f"{uuid.uuid4()}.{file_ext}"

        new_doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            s3_key=s3_key,
            status="PENDING",
            file_hash=file_hash,
        )

        try:
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
        except Exception as e:
            logger.error(f"Database error during creation: {e}")
            await db.rollback()
            raise HTTPException(status_code=500, detail="Database error") from e

        try:
            await storage_service.upload_file(file.file, s3_key, file.content_type)
        except S3UploadError as e:
            logger.error(f"Failed to upload to S3. Error: {e}")
            new_doc.status = "FAILED"
            await db.commit()
            raise HTTPException(
                status_code=500, detail="Failed to upload file to S3"
            ) from e

        new_doc.status = "UPLOADED"
        await db.commit()

        await self._enqueue_parsing_task(db, new_doc)

        return new_doc

    async def get_document_by_id(self, db: AsyncSession, doc_id: int) -> Document:
        query = select(Document).where(Document.id == doc_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")
        return doc

    async def reprocess_document(self, db: AsyncSession, doc_id: int) -> Document:
        """
        Resets the document state and dispatches it to the background worker
        for a fresh AI extraction and vectorization.
        """
        doc = await self.get_document_by_id(db, doc_id)

        doc.status = "PENDING"
        doc.parsed_json = None
        doc.embedding = None

        try:
            await db.commit()
            await db.refresh(doc)
        except Exception as e:
            logger.error(f"Database error during document reset: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500, detail="Database error while resetting document"
            ) from e

        await self._enqueue_parsing_task(db, doc)

        logger.info("Successfully enqueued document %s for reprocessing.", doc.id)
        return doc

    async def get_document_download_stream(self, db: AsyncSession, doc_id: int):
        doc = await self.get_document_by_id(db, doc_id)
        file_stream = storage_service.stream_file(doc.s3_key)
        return file_stream, doc.content_type, doc.filename

    async def delete_document(self, db: AsyncSession, doc_id: int) -> dict:
        """
        Hard delete: Removes the physical file from S3 and the record from the database.
        """
        doc = await self.get_document_by_id(db, doc_id)

        try:
            await storage_service.delete_file(doc.s3_key)
        except Exception as e:
            logger.error(f"S3 deletion failed for doc {doc_id}. Error: {e}")
            raise HTTPException(
                status_code=500, detail="Failed to delete file from S3 storage."
            ) from e

        try:
            await db.delete(doc)
            await db.commit()
            logger.info("Successfully hard-deleted document %s from database.", doc_id)
        except Exception as e:
            logger.error(f"Database error during hard delete for doc {doc_id}: {e}")
            await db.rollback()
            raise HTTPException(
                status_code=500,
                detail="Database error occurred while deleting the document.",
            ) from e

        return {"message": f"Document {doc_id} has been permanently deleted."}

    async def stream_document_status(self, doc: Document) -> AsyncGenerator[str, None]:
        """
        Subscribes to Redis PubSub and yields SSE-formatted status updates.
        """
        redis_client = None
        pubsub = None
        channel_name = f"document_status_{doc.id}"
        final_statuses = {
            "COMPLETED",
            "FAILED",
            "DUPLICATE",
            "REJECTED",
            "REQUIRES_MANUAL_REVIEW",
        }

        try:
            redis_client = aioredis.from_url(settings.REDIS_URL)
            pubsub = redis_client.pubsub()

            if doc.status in final_statuses:
                payload = {"status": doc.status, "document_id": doc.id}
                yield f"data: {json.dumps(payload)}\n\n"
                return

            await pubsub.subscribe(channel_name)
            logger.info(f"SSE Subscribed to Redis channel: {channel_name}")

            payload = {"status": doc.status, "document_id": doc.id}
            yield f"data: {json.dumps(payload)}\n\n"

            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"].decode("utf-8")
                    yield f"data: {data}\n\n"

                    parsed_data = json.loads(data)
                    if parsed_data.get("status") in final_statuses:
                        logger.info(f"Closing SSE connection for doc {doc.id}")
                        break

        except asyncio.CancelledError:
            logger.info(f"Client cleanly disconnected from SSE stream for doc {doc.id}")

        except Exception as e:
            logger.error(f"Unexpected error in SSE stream for doc {doc.id}: {e}")
            yield f"data: {json.dumps({'error': 'Internal stream error'})}\n\n"

        finally:
            if pubsub:
                await pubsub.unsubscribe(channel_name)
                await pubsub.close()
            if redis_client:
                await redis_client.aclose()

    async def _check_exact_duplicate(
        self, db: AsyncSession, file_content: bytes
    ) -> None:
        """Calculates binary hash and raises 409 Conflict if file already exists."""
        file_hash = hashlib.sha256(file_content).hexdigest()
        query = select(Document).where(Document.file_hash == file_hash)
        result = await db.execute(query)
        existing_doc = result.scalar_one_or_none()

        if existing_doc:
            logger.info(
                f"Upload rejected: Exact binary duplicate (ID: {existing_doc.id})"
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "This exact file has already been uploaded.",
                    "existing_document_id": existing_doc.id,
                },
            )

    async def _enqueue_parsing_task(self, db: AsyncSession, doc: Document) -> None:
        """Creates the task payload and enqueues it. Reverts DB state on failure."""
        task = ParseCVTask(document_id=doc.id, s3_key=doc.s3_key, filename=doc.filename)
        job = await queue_service.enqueue_parse_cv(task.model_dump())

        if not job:
            logger.critical(f"FATAL: Redis rejected task for document {doc.id}.")
            doc.status = "FAILED"
            try:
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to update status to FAILED for doc {doc.id}: {e}")
                await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "message": (
                        "Service temporarily unavailable. "
                        "Document saved but not processed."
                    ),
                    "document_id": doc.id,
                },
            )


document_service = DocumentService()
