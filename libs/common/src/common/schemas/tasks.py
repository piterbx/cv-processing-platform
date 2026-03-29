from enum import StrEnum

from pydantic import BaseModel


class TaskName(StrEnum):
    PARSE_CV = "process_cv_task"
    GENERATE_EMBEDDINGS = "generate_embeddings"


class ParseCVTask(BaseModel):
    """
    A contract defining a background task.
    Core API sends this model to the queue, and the Worker receives it.
    """

    document_id: int
    s3_key: str
    filename: str


class GenerateEmbeddingsTask(BaseModel):
    """
    A contract defining a background task for generating embeddings.
    Core API sends this model to the queue AFTER the recruiter approves
    the CV data, and the Worker receives it to vectorize the final JSON.
    """

    document_id: int
