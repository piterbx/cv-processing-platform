from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobOfferBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the job offer")
    description: str | None = None
    is_active: bool = True


class JobOfferCreate(JobOfferBase):
    pass


class JobOfferUpdate(BaseModel):
    title: str | None = Field(None, min_length=1)
    description: str | None = None
    is_active: bool | None = None


class JobOfferRead(JobOfferBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
