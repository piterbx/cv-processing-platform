from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Document
from src.schemas.document import DocumentUpload
from src.services.storage import storage_service

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
            status="UPLOADED"
        )
        
        db.add(new_doc)
        await db.commit()
        await db.refresh(new_doc)

        # TODO: celery.send_task("process_cv", args=[new_doc.id])
        
        return new_doc

document_service = DocumentService()