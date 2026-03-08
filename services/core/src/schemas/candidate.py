from typing import Any

from pydantic import BaseModel, Field


class CandidateSearchResponse(BaseModel):
    document_id: int = Field(..., description="ID of the source CV document")
    similarity_score: float = Field(
        ..., description="Cosine similarity score (0.0 to 1.0)"
    )
    parsed_data: dict[str, Any] = Field(
        default_factory=dict, description="AI extracted structured data"
    )
    status: str
