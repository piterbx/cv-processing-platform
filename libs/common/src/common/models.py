from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# association table between Candidate and Skill M:N
candidate_skills = Table(
    "candidate_skills",
    Base.metadata,
    Column(
        "candidate_id",
        Integer,
        ForeignKey("candidates.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "skill_id",
        Integer,
        ForeignKey("skills.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)

    # Document -> Candidate
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True
    )

    filename = Column(String, nullable=False)
    content_type = Column(String)
    s3_key = Column(String, nullable=False)
    status = Column(String, default="PENDING")

    file_hash = Column(String(64), unique=True, index=True, nullable=True)
    content_hash = Column(String(64), nullable=True)

    parsed_json = Column(JSONB, nullable=True)
    embedding = Column(Vector(384), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # many Documents -> 1 Candidate | Nullable: True
    candidate = relationship("Candidate", back_populates="documents")

    # 1 Document -> many Applications | Nullable: True (for Application)
    applications = relationship("Application", back_populates="document")

    __table_args__ = (
        Index(
            "ix_unique_content_hash",
            "content_hash",
            unique=True,
            postgresql_where=(
                status.in_(
                    [
                        "PROCESSING",
                        "AWAITING_REVIEW",
                        "APPROVED",
                        "INDEXING",
                        "COMPLETED",
                    ]
                )
            ),
        ),
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True)

    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone = Column(String(50), nullable=True)
    location = Column(String(255), nullable=True)
    total_experience_years = Column(Integer, default=0)
    summary = Column(Text, nullable=True)

    # 1 Candidate -> many Documents
    documents = relationship("Document", back_populates="candidate")

    # 1 Candidate -> many WorkExperiences | Cascade deletes orphans
    experiences = relationship(
        "WorkExperience", back_populates="candidate", cascade="all, delete-orphan"
    )

    # many Candidates <-> many Skills (via candidate_skills table)
    skills = relationship(
        "Skill", secondary=candidate_skills, back_populates="candidates"
    )

    # 1 Candidate -> many Applications | Cascade deletes orphans
    applications = relationship(
        "Application", back_populates="candidate", cascade="all, delete-orphan"
    )


class WorkExperience(Base):
    __tablename__ = "work_experiences"

    id = Column(Integer, primary_key=True)

    # WorkExperience -> Candidate | Nullable: False (Cascade on delete)
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False
    )

    company = Column(String(255), nullable=False)
    position = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    description = Column(Text, nullable=True)

    # many WorkExperiences -> 1 Candidate | Nullable: False
    candidate = relationship("Candidate", back_populates="experiences")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

    # many Skills <-> many Candidates (via candidate_skills table)
    candidates = relationship(
        "Candidate", secondary=candidate_skills, back_populates="skills"
    )


class JobOffer(Base):
    __tablename__ = "job_offers"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 1 JobOffer -> many Applications | Cascade deletes orphans
    applications = relationship(
        "Application", back_populates="job_offer", cascade="all, delete-orphan"
    )


class Application(Base):
    """Links a Candidate, their specific CV (Document), and a Job Offer."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True)

    # Application -> Candidate
    candidate_id = Column(
        Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True
    )

    # Application -> JobOffer
    job_offer_id = Column(
        Integer, ForeignKey("job_offers.id", ondelete="CASCADE"), nullable=False
    )

    # Application -> Document
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"))

    status = Column(String(50), default="NEW")
    applied_at = Column(DateTime(timezone=True), server_default=func.now())

    # many Applications -> 1 Candidate
    candidate = relationship("Candidate", back_populates="applications")

    # many Applications -> 1 JobOffer
    job_offer = relationship("JobOffer", back_populates="applications")

    # many Applications -> 1 Document
    document = relationship("Document", back_populates="applications")
