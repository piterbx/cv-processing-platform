from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.work_experience import WorkExperienceCreate, WorkExperienceUpdate

from common.models import WorkExperience


class WorkExperienceService:
    # WORK EXPERIENCE CRUD
    async def get_experiences(self, db: AsyncSession, candidate_id: int):
        query = select(WorkExperience).where(
            WorkExperience.candidate_id == candidate_id
        )
        result = await db.execute(query)
        return result.scalars().all()

    async def add_experience(
        self, db: AsyncSession, candidate_id: int, experience_data: WorkExperienceCreate
    ):
        new_experience = WorkExperience(
            **experience_data.model_dump(), candidate_id=candidate_id
        )
        db.add(new_experience)
        await db.commit()
        await db.refresh(new_experience)
        return new_experience

    async def update_experience(
        self,
        db: AsyncSession,
        candidate_id: int,
        exp_id: int,
        update_data: WorkExperienceUpdate,
    ):
        query = select(WorkExperience).where(
            WorkExperience.id == exp_id, WorkExperience.candidate_id == candidate_id
        )
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work experience not found",
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(experience, key, value)

        await db.commit()
        await db.refresh(experience)
        return experience

    async def delete_experience(self, db: AsyncSession, candidate_id: int, exp_id: int):
        query = select(WorkExperience).where(
            WorkExperience.id == exp_id, WorkExperience.candidate_id == candidate_id
        )
        result = await db.execute(query)
        experience = result.scalar_one_or_none()

        if not experience:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Work experience not found",
            )

        await db.delete(experience)
        await db.commit()
        return {"detail": "Work experience deleted successfully"}


work_experience_service = WorkExperienceService()
