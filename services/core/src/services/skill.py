from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from src.schemas.skill import SkillCreate

from common.models import Candidate, Skill


class SkillService:
    async def get_all_skills(
        self,
        db: AsyncSession,
        search: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        stmt = select(Skill)
        if search:
            stmt = stmt.where(Skill.name.ilike(f"%{search}%"))

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def create_skill(self, db: AsyncSession, skill_data: SkillCreate):
        existing_query = select(Skill).where(Skill.name.ilike(skill_data.name))
        existing_result = await db.execute(existing_query)

        if existing_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Skill with this name already exists",
            )

        new_skill = Skill(name=skill_data.name)
        db.add(new_skill)
        await db.commit()
        await db.refresh(new_skill)
        return new_skill

    async def get_skills(self, db: AsyncSession, candidate_id: int):
        query = (
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.id == candidate_id)
        )
        result = await db.execute(query)
        candidate = result.scalar_one_or_none()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )

        return candidate.skills

    async def add_skill_to_candidate(
        self, db: AsyncSession, candidate_id: int, skill_id: int
    ):
        candidate_query = (
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.id == candidate_id)
        )
        candidate_result = await db.execute(candidate_query)
        candidate = candidate_result.scalar_one_or_none()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )

        skill_query = select(Skill).where(Skill.id == skill_id)
        skill_result = await db.execute(skill_query)
        skill = skill_result.scalar_one_or_none()

        if not skill:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found"
            )

        if any(s.id == skill_id for s in candidate.skills):
            return candidate.skills

        candidate.skills.append(skill)
        await db.commit()
        await db.refresh(candidate)

        return candidate.skills

    async def remove_skill_from_candidate(
        self, db: AsyncSession, candidate_id: int, skill_id: int
    ):
        candidate_query = (
            select(Candidate)
            .options(selectinload(Candidate.skills))
            .where(Candidate.id == candidate_id)
        )
        candidate_result = await db.execute(candidate_query)
        candidate = candidate_result.scalar_one_or_none()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )

        skill_to_remove = next((s for s in candidate.skills if s.id == skill_id), None)

        if not skill_to_remove:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill not linked to this candidate",
            )

        candidate.skills.remove(skill_to_remove)
        await db.commit()
        return {"detail": "Skill removed from candidate"}


skill_service = SkillService()
