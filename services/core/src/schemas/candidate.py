from typing import Any

from pydantic import BaseModel, Field


class CandidateSearchParams(BaseModel):
    q: str = Field(..., description="Semantic search query, e.g., 'Senior Python'")
    skip: int = Field(0, ge=0, description="Number of records to skip")
    limit: int = Field(
        5, ge=1, le=50, description="Maximum number of candidates to return"
    )
    min_experience: int | None = Field(
        None, ge=0, description="Minimum years of experience"
    )
    required_skill: str | None = Field(None, description="Must-have skill keyword")
    location: str | None = Field(None, description="Required location keyword")
    job_title: str | None = Field(None, description="Required job title keyword")


class CandidateSearchResponse(BaseModel):
    document_id: int = Field(..., description="ID of the source CV document")
    similarity_score: float = Field(
        ..., description="Cosine similarity score (0.0 to 1.0)"
    )
    parsed_data: dict[str, Any] = Field(
        default_factory=dict, description="AI extracted structured data"
    )
    status: str
