from fastapi import APIRouter
from src.api import applications, candidates, documents, job_offers, skills

api_router = APIRouter()

api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(candidates.router, prefix="/candidates", tags=["candidates"])
api_router.include_router(skills.router, prefix="/skills", tags=["skills"])

api_router.include_router(job_offers.router, prefix="/job-offers", tags=["job_offers"])
api_router.include_router(
    applications.router, prefix="/applications", tags=["applications"]
)
