from pydantic import BaseModel, ConfigDict, Field


class SkillBase(BaseModel):
    name: str = Field(..., min_length=1, description="Skill name, ex. Python")


class SkillApproveSchema(SkillBase):
    pass


class SkillCreate(SkillBase):
    """Schema used when creating a new skill in the dictionary."""

    pass


class SkillRead(SkillBase):
    """Schema used when returning skill data from the database."""

    model_config = ConfigDict(from_attributes=True)

    id: int
