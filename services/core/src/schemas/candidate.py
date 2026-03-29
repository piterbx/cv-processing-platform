from typing import Any

from pydantic import BaseModel, EmailStr, Field


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


class SkillApproveSchema(BaseModel):
    name: str = Field(..., min_length=1, description="Skill name, ex. Python")


class WorkExperienceApproveSchema(BaseModel):
    company: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class ApprovedCandidateData(BaseModel):
    """
    Main schema that will arrive from the frontend (from the recruiter)
    during CV approval.
    """

    first_name: str | None = None
    last_name: str | None = None

    email: EmailStr | None = None

    phone: str | None = None
    location: str | None = None

    total_experience_years: int = Field(default=0, ge=0)
    summary: str | None = None

    skills: list[SkillApproveSchema] = Field(default_factory=list)
    experiences: list[WorkExperienceApproveSchema] = Field(default_factory=list)

    # optional: Job offer ID. If the recruiter doesn't select one, the application
    # is treated as "spontaneous" (not tied to a specific job offer)
    job_offer_id: int | None = None
