from fastapi import APIRouter
from src.api import candidates, documents, skills

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])
