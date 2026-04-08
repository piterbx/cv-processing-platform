from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class WorkExperienceBase(BaseModel):
    company: str = Field(..., min_length=1)
    position: str = Field(..., min_length=1)
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)
    description: str | None = None


class WorkExperienceCreate(WorkExperienceBase):
    """Schema used when manually adding a new work experience."""

    pass


class WorkExperienceUpdate(BaseModel):
    """Schema used for partial updates (PATCH/PUT). All fields are optional."""

    company: str | None = Field(None, min_length=1)
    position: str | None = Field(None, min_length=1)
    start_date: date | None = Field(None)
    end_date: date | None = Field(None)
    description: str | None = None


class WorkExperienceRead(WorkExperienceBase):
    """Schema used when returning work experience from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_id: int
