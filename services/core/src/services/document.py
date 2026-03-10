import logging
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
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
        file_ext = file.filename.split(".")[-1]
        s3_key = f"{uuid.uuid4()}.{file_ext}"

        new_doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            s3_key=s3_key,
            status="PENDING",
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

        task = ParseCVTask(
            document_id=new_doc.id, s3_key=s3_key, filename=file.filename
        )

        job = await queue_service.enqueue_parse_cv(task.model_dump())
        if not job:
            logger.critical(
                "FATAL: Redis rejected task for document %s. Document is orphaned.",
                new_doc.id,
            )
            # TODO: handling

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

        task = ParseCVTask(document_id=doc.id, s3_key=doc.s3_key, filename=doc.filename)

        job = await queue_service.enqueue_parse_cv(task.model_dump())
        if not job:
            logger.critical(
                "FATAL: Redis rejected reprocess task for document %s.",
                doc.id,
            )
            doc.status = "FAILED"
            await db.commit()
            raise HTTPException(
                status_code=503,
                detail="Failed to enqueue background task for reprocessing.",
            )

        logger.info("Successfully enqueued document %s for reprocessing.", doc.id)
        return doc

    async def get_document_download_stream(self, db: AsyncSession, doc_id: int):
        doc = await self.get_document_by_id(db, doc_id)
        file_stream = storage_service.stream_file(doc.s3_key)
        return file_stream, doc.content_type, doc.filename


document_service = DocumentService()
