from enum import StrEnum

from pydantic import BaseModel


class TaskName(StrEnum):
    PARSE_CV = "process_cv_task"


class ParseCVTask(BaseModel):
    """
    A contract defining a background task.
    Core API sends this model to the queue, and the Worker receives it.
    """

    document_id: int
    s3_key: str
    filename: str
