import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.schemas.candidate import CandidateSearchParams, CandidateSearchResponse

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


candidate_service = CandidateService()
