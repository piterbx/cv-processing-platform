from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
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
    content_hash = Column(String(64), nullable=True)

    parsed_json = Column(JSONB, nullable=True)
    embedding = Column(Vector(384), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index(
            "ix_unique_content_hash",
            "content_hash",
            unique=True,
            postgresql_where=(status.in_(["PROCESSING", "COMPLETED"])),
        ),
    )
