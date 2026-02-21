import logging

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Document
from src.schemas.document import DocumentUpload
from src.services.storage import storage_service

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

        # upload to S3
        s3_key = await storage_service.upload_file(file)

        # metadata to Postgres
        new_doc = Document(
            filename=file.filename,
            content_type=file.content_type,
            s3_key=s3_key,
            status="UPLOADED",
        )

        try:
            db.add(new_doc)
            await db.commit()
            await db.refresh(new_doc)
        except Exception as e:
            logger.error(f"Database error during document creation: {e}")
            await db.rollback()

            # cleaning file from bucket
            try:
                await storage_service.delete_file(s3_key)
            except Exception as cleanup_error:
                logger.critical(
                    f"CRITICAL ORPHAN FILE: Failed to clean up S3 file {s3_key}. "
                    f"Error: {cleanup_error}"
                )

            raise HTTPException(
                status_code=500,
                detail="Failed to save document metadata. Upload reverted.",
            ) from None

        # TODO: btask not celery

        return new_doc

    async def get_document_by_id(self, db: AsyncSession, doc_id: int) -> Document:
        """Fetches a single document's metadata from the database."""
        query = select(Document).where(Document.id == doc_id)
        result = await db.execute(query)
        doc = result.scalar_one_or_none()

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found.")

        return doc

    async def get_document_download_stream(self, db: AsyncSession, doc_id: int):
        """Retrieves the document metadata and initializes the S3 download stream."""
        doc = await self.get_document_by_id(db, doc_id)

        file_stream = storage_service.stream_file(doc.s3_key)

        return file_stream, doc.content_type, doc.filename


document_service = DocumentService()
