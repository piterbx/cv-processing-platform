from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    content_type = Column(String)
    s3_key = Column(String, nullable=False)
    status = Column(String, default="UPLOADED") # UPLOADED -> PROCESSING -> DONE
    created_at = Column(DateTime(timezone=True), server_default=func.now())