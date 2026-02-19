from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from fastapi import UploadFile, File, HTTPException, status

class DocumentBase(BaseModel):
    filename: str
    content_type: Optional[str] = None
    status: str


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentUpload:
    def __init__(self, file: UploadFile = File(...)):
        if file.content_type != "application/pdf":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type: {file.content_type}. Only PDF is allowed."
            )
        
        if not file.filename.lower().endswith('.pdf'):
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file extension. Filename must end with .pdf"
            )

        self.file = file