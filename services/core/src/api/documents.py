from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_db
from src.schemas.document import DocumentRead, DocumentUpload
from src.services.document import document_service

router = APIRouter()

@router.get("/", response_model=List[DocumentRead])
async def get_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db)
):
    return await document_service.get_all_documents(db, skip, limit)


@router.post("/upload", response_model=DocumentRead, operation_id="upload_cv")
async def upload_document(
    upload_data: DocumentUpload = Depends(),
    db: AsyncSession = Depends(get_db) 
):
    return await document_service.create_document(db, upload_data)


@router.get("/{doc_id}", response_model=DocumentRead, operation_id="get_document")
async def get_document(
    doc_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Retrieves the metadata and current status of a specific document."""
    return await document_service.get_document_by_id(db, doc_id)


@router.get("/{doc_id}/download", operation_id="download_cv")
async def download_document(
    doc_id: int, 
    db: AsyncSession = Depends(get_db)
):
    """Downloads the actual PDF file associated with the document ID."""
    file_stream, content_type, filename = await document_service.get_document_download_stream(db, doc_id)
    
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }
    
    return StreamingResponse(
        file_stream,
        media_type=content_type or "application/pdf",
        headers=headers
    )