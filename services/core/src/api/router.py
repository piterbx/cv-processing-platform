from fastapi import APIRouter
from src.api import documents

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
