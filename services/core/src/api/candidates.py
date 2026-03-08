from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.candidate import CandidateSearchResponse
from src.services.candidate import candidate_service

router = APIRouter()


@router.get(
    "/search",
    response_model=list[CandidateSearchResponse],
    operation_id="search_candidates",
)
async def search_candidates(
    q: str = Query(
        ...,
        description="Search query, e.g., 'Python Developer with AWS cloud experience'",
    ),
    limit: int = Query(
        5, ge=1, le=50, description="Maximum number of candidates to return"
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Searches for candidates using semantic vector search (Cosine Similarity).
    """
    try:
        return await candidate_service.search_candidates(db, query=q, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
