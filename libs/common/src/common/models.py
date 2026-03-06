from sqlalchemy import Column, DateTime, Integer, String, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    content_type = Column(String)
    s3_key = Column(String, nullable=False)
    status = Column(
        String, default="PENDING"
    )  # PENDING -> UPLOADED -> PROCESSING -> COMPLETED / FAILED
    content_hash = Column(String(64), index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
