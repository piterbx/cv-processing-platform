from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.candidate import CandidateSearchParams, CandidateSearchResponse
from src.services.candidate import candidate_service

router = APIRouter()


@router.get(
    "/search",
    response_model=list[CandidateSearchResponse],
    operation_id="search_candidates",
)
async def search_candidates(
    search_params: CandidateSearchParams = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Searches for candidates using semantic vector search (Cosine Similarity)
    combined with strict database filters (Hybrid Search) and pagination.
    """
    try:
        return await candidate_service.search_candidates(db, filters=search_params)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
