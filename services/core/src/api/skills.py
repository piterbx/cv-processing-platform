from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.skill import SkillCreate, SkillRead
from src.services.skill import skill_service

router = APIRouter()


@router.get("/", response_model=list[SkillRead], operation_id="list_all_skills")
async def get_all_skills(
    search: str | None = Query(
        None, description="Search term to filter skills (e.g. 'Python')"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a global list of available skills.
    Useful for populating dropdowns or frontend autocomplete.
    """
    return await skill_service.get_all_skills(db, search, skip, limit)


@router.post(
    "/",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_skill",
)
async def create_skill(skill_data: SkillCreate, db: AsyncSession = Depends(get_db)):
    """
    Creates a new skill in the global database dictionary.
    """
    return await skill_service.create_skill(db, skill_data)
