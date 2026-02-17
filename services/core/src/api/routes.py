from fastapi import APIRouter, UploadFile, Depends, File, HTTPException
from sqlalchemy.orm import Session
from src.db.session import get_db
from src.db.models import Document
from src.services.storage import storage_service

router = APIRouter()

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    if file.content_type != "application/pdf":
        raise HTTPException(400, "Only PDF files allowed")

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
    db.commit()
    db.refresh(new_doc)

    # TODO: celery.send_task("process_cv", args=[new_doc.id])
    
    return {"id": new_doc.id, "status": "UPLOADED", "filename": new_doc.filename}