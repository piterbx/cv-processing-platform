from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.candidate import (
    CandidateRead,
    CandidateSearchParams,
    CandidateSearchResponse,
    CandidateUpdate,
)
from src.schemas.skill import SkillRead
from src.schemas.work_experience import (
    WorkExperienceCreate,
    WorkExperienceRead,
    WorkExperienceUpdate,
)
from src.services.candidate import candidate_service
from src.services.skill import skill_service
from src.services.work_experience import work_experience_service

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


@router.get("/", response_model=list[CandidateRead], operation_id="list_candidates")
async def get_candidates(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=100, description="Number of records to return"),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a list of candidates."""
    return await candidate_service.get_all_candidates(db, skip, limit)


@router.get(
    "/{candidate_id}", response_model=CandidateRead, operation_id="get_candidate"
)
async def get_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves detailed information about a specific candidate."""
    candidate = await candidate_service.get_candidate_by_id(db, candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return candidate


@router.put(
    "/{candidate_id}", response_model=CandidateRead, operation_id="update_candidate"
)
async def update_candidate(
    candidate_id: int, update_data: CandidateUpdate, db: AsyncSession = Depends(get_db)
):
    """Updates basic profile information for a candidate."""
    return await candidate_service.update_candidate(db, candidate_id, update_data)


@router.delete(
    "/{candidate_id}", status_code=status.HTTP_200_OK, operation_id="delete_candidate"
)
async def delete_candidate(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """
    Deletes a candidate.
    Cascade rules will also remove their work experiences and applications.
    """
    return await candidate_service.delete_candidate(db, candidate_id)


# WORK EXPERIENCE ENDPOINTS


@router.get(
    "/{candidate_id}/experiences",
    response_model=list[WorkExperienceRead],
    operation_id="get_candidate_experiences",
)
async def get_candidate_experiences(
    candidate_id: int, db: AsyncSession = Depends(get_db)
):
    """Retrieves all work experiences for a specific candidate."""
    return await work_experience_service.get_experiences(db, candidate_id)


@router.post(
    "/{candidate_id}/experiences",
    response_model=WorkExperienceRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="add_candidate_experience",
)
async def add_candidate_experience(
    candidate_id: int,
    experience_data: WorkExperienceCreate,
    db: AsyncSession = Depends(get_db),
):
    """Adds a new work experience entry to the candidate's profile."""
    candidate = await candidate_service.get_candidate_by_id(db, candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
        )

    return await work_experience_service.add_experience(
        db, candidate_id, experience_data
    )


@router.put(
    "/{candidate_id}/experiences/{exp_id}",
    response_model=WorkExperienceRead,
    operation_id="update_candidate_experience",
)
async def update_candidate_experience(
    candidate_id: int,
    exp_id: int,
    update_data: WorkExperienceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Updates a specific work experience entry."""
    return await work_experience_service.update_experience(
        db, candidate_id, exp_id, update_data
    )


@router.delete(
    "/{candidate_id}/experiences/{exp_id}",
    status_code=status.HTTP_200_OK,
    operation_id="delete_candidate_experience",
)
async def delete_candidate_experience(
    candidate_id: int, exp_id: int, db: AsyncSession = Depends(get_db)
):
    """Deletes a specific work experience entry from the candidate's profile."""
    return await work_experience_service.delete_experience(db, candidate_id, exp_id)


# SKILLS ENDPOINTS


@router.get(
    "/{candidate_id}/skills",
    response_model=list[SkillRead],
    operation_id="get_candidate_skills",
)
async def get_candidate_skills(candidate_id: int, db: AsyncSession = Depends(get_db)):
    """Retrieves all skills linked to a specific candidate."""
    return await skill_service.get_skills(db, candidate_id)


@router.post(
    "/{candidate_id}/skills/{skill_id}",
    response_model=list[SkillRead],
    operation_id="add_candidate_skill",
)
async def add_candidate_skill(
    candidate_id: int, skill_id: int, db: AsyncSession = Depends(get_db)
):
    """Links an existing skill to the candidate."""
    return await skill_service.add_skill_to_candidate(db, candidate_id, skill_id)


@router.delete(
    "/{candidate_id}/skills/{skill_id}",
    status_code=status.HTTP_200_OK,
    operation_id="remove_candidate_skill",
)
async def remove_candidate_skill(
    candidate_id: int, skill_id: int, db: AsyncSession = Depends(get_db)
):
    """Removes a skill link from the candidate's profile."""
    return await skill_service.remove_skill_from_candidate(db, candidate_id, skill_id)
