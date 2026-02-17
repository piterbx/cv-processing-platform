from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.db.session import get_db
from src.db.models import Document
from src.schemas.document import DocumentRead, DocumentUpload
from src.services.storage import storage_service

router = APIRouter()

@router.get("/documents", response_model=List[DocumentRead])
async def get_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db)
):

    query = (
        select(Document)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    
    return result.scalars().all()


@router.post("/upload", response_model=DocumentRead, operation_id="upload_cv")
async def upload_document(
    upload_data: DocumentUpload = Depends(),
    db: AsyncSession = Depends(get_db) 
):
    file = upload_data.file

    # upload to s3
    s3_key = await storage_service.upload_file(file)

    # metadata to postgres
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