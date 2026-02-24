from pydantic import BaseModel


class ParseCVTask(BaseModel):
    """
    A contract defining a background task.
    Core API sends this model to the queue, and the Worker receives it.
    """

    document_id: int
    s3_key: str
    filename: str
