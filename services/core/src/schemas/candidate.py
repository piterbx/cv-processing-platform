from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field


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
    model_config = ConfigDict(from_attributes=True)

    candidate_id: int = Field(..., description="ID of the candidate profile")
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    location: str | None = None
    total_experience_years: int = 0
    similarity_score: float = Field(
        ..., description="Cosine similarity score (0.0 to 1.0)"
    )
    status: str = Field(..., description="Current status of the source document")


class SkillApproveSchema(BaseModel):
    name: str = Field(..., min_length=1, description="Skill name, ex. Python")


class WorkExperienceApproveSchema(BaseModel):
    company: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    start_date: date | str | None = Field(None)
    end_date: date | str | None = Field(None)
    description: str | None = None


class WorkExperienceStrictSchema(WorkExperienceApproveSchema):
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)


class CandidateReviewDraft(BaseModel):
    """
    Main schema that will arrive from the frontend (from the recruiter)
    during CV approval.
    """

    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    total_experience_years: int = 0
    summary: str | None = None
    skills: list[SkillApproveSchema] = Field(default_factory=list)
    experiences: list[WorkExperienceApproveSchema] = Field(default_factory=list)
    job_offer_id: int | None = None


class ApprovedCandidateData(CandidateReviewDraft):
    model_config = ConfigDict(extra="forbid")

    first_name: str = Field(..., min_length=1)
    last_name: str = Field(..., min_length=1)
    email: EmailStr = Field(...)

    experiences: list[WorkExperienceStrictSchema] = Field(default_factory=list)
