import logging

from sqlalchemy import Integer, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.core.config import settings
from src.schemas.candidate import CandidateSearchParams

from common.models import Document
from common.services.vector_service import VectorService

logger = logging.getLogger(__name__)


class CandidateService:
    async def search_candidates(self, db: AsyncSession, filters: CandidateSearchParams):
        query_embedding = await VectorService.generate_embedding(
            text=filters.q,
            host=settings.OLLAMA_HOST,
            model_name=settings.OLLAMA_EMBEDDING_MODEL,
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
        similarity_expr = (
            1 - Document.embedding.cosine_distance(query_embedding)
        ).label("similarity_score")

        stmt = (
            select(Document, similarity_expr)
            .where(Document.status == "COMPLETED")
            .where(Document.embedding.is_not(None))
        )

        # hard filters
        if filters.min_experience is not None:
            stmt = stmt.where(
                Document.parsed_json["hard_facts"][
                    "total_experience_years"
                ].astext.cast(Integer)
                >= filters.min_experience
            )

        if filters.required_skill:
            stmt = stmt.where(
                Document.parsed_json["keywords"]["skills"].astext.ilike(
                    f"%{filters.required_skill}%"
                )
            )

        if filters.location:
            stmt = stmt.where(
                Document.parsed_json["hard_facts"]["location"].astext.ilike(
                    f"%{filters.location}%"
                )
            )

        if filters.job_title:
            stmt = stmt.where(
                Document.parsed_json["keywords"]["job_titles_held"].astext.ilike(
                    f"%{filters.job_title}%"
                )
            )

        # pagination
        stmt = (
            stmt.order_by(Document.embedding.cosine_distance(query_embedding))
            .offset(filters.skip)
            .limit(filters.limit)
        )

        result = await db.execute(stmt)
        rows = result.all()

        return [
            {
                "document_id": doc.id,
                "similarity_score": float(score),
                "parsed_data": doc.parsed_json or {},
                "status": doc.status,
            }
            for doc, score in rows
        ]


candidate_service = CandidateService()
