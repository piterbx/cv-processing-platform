from datetime import datetime

from pydantic import BaseModel, ConfigDict

from common.enums import ApplicationStatus


class ApplicationBase(BaseModel):
    job_offer_id: int
    candidate_id: int | None = None
    document_id: int | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: ApplicationStatus


class ApplicationRead(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ApplicationStatus
    applied_at: datetime
