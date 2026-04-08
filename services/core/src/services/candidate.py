import logging

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.schemas.candidate import (
    CandidateSearchParams,
    CandidateSearchResponse,
    CandidateUpdate,
)

from common.enums import DocumentStatus
from common.models import Candidate, Document, Skill, WorkExperience
from common.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class CandidateService:
    async def search_candidates(self, db: AsyncSession, filters: CandidateSearchParams):
        query_embedding = await VectorService.generate_embedding(
            text=filters.q,
            host=settings.OLLAMA_HOST,
            model_name=settings.OLLAMA_EMBEDDING_MODEL,
            num_ctx=settings.OLLAMA_EMBEDDING_NUM_CTX,
            temperature=settings.OLLAMA_EMBEDDING_TEMPERATURE,
        )

        if not query_embedding:
            logger.error(
                "Failed to generate embedding for search query: '%s'", filters.q
            )
            raise ValueError(
                "Failed to process search query due to AI service unavailability."
            )

        # cosine_distance returns 0 for identical vectors, up to 2 for opposites.
        # here invert it (1 - distance) to get
        # a logical similarity score (higher is better).
        distance_expr = Document.embedding.cosine_distance(query_embedding)
        similarity_expr = 1 - distance_expr

        stmt = (
            select(Candidate, func.max(similarity_expr).label("similarity_score"))
            .join(Document, Candidate.id == Document.candidate_id)
            .where(Document.status == DocumentStatus.COMPLETED)
            .where(Document.embedding.is_not(None))
        )

        # hard filters
        if filters.min_experience is not None:
            stmt = stmt.where(
                Candidate.total_experience_years >= filters.min_experience
            )

        if filters.required_skill:
            stmt = stmt.where(
                Candidate.skills.any(Skill.name.ilike(f"%{filters.required_skill}%"))
            )

        if filters.location:
            stmt = stmt.where(Candidate.location.ilike(f"%{filters.location}%"))

        if filters.job_title:
            stmt = stmt.where(
                Candidate.experiences.any(
                    WorkExperience.position.ilike(f"%{filters.job_title}%")
                )
            )

        # pagination
        stmt = (
            stmt.group_by(Candidate.id)
            .order_by(func.min(distance_expr).asc())
            .offset(filters.skip)
            .limit(filters.limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        return [
            CandidateSearchResponse(
                candidate_id=cand.id,
                first_name=cand.first_name,
                last_name=cand.last_name,
                email=cand.email,
                location=cand.location,
                total_experience_years=cand.total_experience_years,
                similarity_score=float(score),
                status="COMPLETED",
            )
            for cand, score in rows
        ]

    # CANDIDATE CRUD
    async def get_all_candidates(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ):
        query = select(Candidate).offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    async def get_candidate_by_id(self, db: AsyncSession, candidate_id: int):
        query = select(Candidate).where(Candidate.id == candidate_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def update_candidate(
        self, db: AsyncSession, candidate_id: int, update_data: CandidateUpdate
    ):
        candidate = await self.get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(candidate, key, value)

        await db.commit()
        await db.refresh(candidate)
        return candidate

    async def delete_candidate(self, db: AsyncSession, candidate_id: int):
        candidate = await self.get_candidate_by_id(db, candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found"
            )

        await db.delete(candidate)
        await db.commit()
        return {"detail": "Candidate deleted successfully"}


candidate_service = CandidateService()
