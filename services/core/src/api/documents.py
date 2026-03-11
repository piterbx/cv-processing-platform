from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.document import DocumentRead, DocumentUpload
from src.services.document import document_service

from common import S3DownloadError

router = APIRouter()


@router.get("/", response_model=list[DocumentRead])
async def get_documents(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    return await document_service.get_all_documents(db, skip, limit)


@router.post("/upload", response_model=DocumentRead, operation_id="upload_cv")
async def upload_document(
    upload_data: DocumentUpload = Depends(), db: AsyncSession = Depends(get_db)
):
    return await document_service.create_document(db, upload_data)


@router.post(
    "/{doc_id}/reprocess", response_model=DocumentRead, operation_id="reprocess_cv"
)
async def reprocess_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    return await document_service.reprocess_document(db, doc_id)


@router.get("/{doc_id}", response_model=DocumentRead, operation_id="get_document")
async def get_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves the metadata and current status of a specific document."""
    return await document_service.get_document_by_id(db, doc_id)


@router.get("/{doc_id}/download", operation_id="download_cv")
async def download_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """Downloads the PDF file associated with the document ID."""
    try:
        (
            file_stream,
            content_type,
            filename,
        ) = await document_service.get_document_download_stream(db, doc_id)

        headers = {"Content-Disposition": f'attachment; filename="{filename}"'}

        return StreamingResponse(
            file_stream, media_type=content_type or "application/pdf", headers=headers
        )
    except S3DownloadError as e:
        raise HTTPException(
            status_code=404, detail="File not found on storage server"
        ) from e


@router.delete(
    "/{doc_id}", status_code=status.HTTP_200_OK, operation_id="delete_document"
)
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    """
    Permanently deletes a candidate's CV from the system.
    This action removes the database record, AI vector embeddings,
    and the physical PDF file from S3.
    """
    return await document_service.delete_document(db, doc_id)
