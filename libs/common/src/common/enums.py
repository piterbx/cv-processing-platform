import enum


class DocumentStatus(enum.StrEnum):
    """
    Represents the lifecycle of a CV document in the system.
    """

    PENDING = "PENDING"  # initial state upon record creation
    UPLOADED = "UPLOADED"  # successfully stored in S3, ready for parsing

    PROCESSING = "PROCESSING"  # currently being handled by the CV Parser worker
    DUPLICATE = "DUPLICATE"  # content hash matches an existing document
    FAILED = "FAILED"  # technical error during processing

    AWAITING_REVIEW = (
        "AWAITING_REVIEW"  # successfully parsed, waiting for recruiter approval
    )
    REQUIRES_MANUAL_REVIEW = (
        "REQUIRES_MANUAL_REVIEW"  # AI results were inconclusive or empty
    )
    REJECTED = "REJECTED"  # discarded due to security risk

    APPROVED = "APPROVED"  # recruiter confirmed data, ready for vectorization
    INDEXING = "INDEXING"  # currently generating semantic embedding

    COMPLETED = "COMPLETED"  # data and vectors are synced. Candidate is searchable.


class ApplicationStatus(enum.StrEnum):
    """
    Represents the business lifecycle of a candidate's application
    to a specific job offer.
    """

    NEW = "NEW"  # fresh application, not yet seen by recruiter
    SCREENING = "SCREENING"  # recruiter is reviewing the CV/profile

    CONTACTED = "CONTACTED"  # initial reach out (phone/email)
    INTERVIEW = "INTERVIEW"  # interview scheduled or in progress
    TECHNICAL_TEST = "TECHNICAL_TEST"  # candidate is solving a task test

    OFFER_SENT = "OFFER_SENT"  # formal offer extended to the candidate

    HIRED = "HIRED"  # candidate accepted and is onboarded

    REJECTED = "REJECTED"  # candidate did not meet requirements
    WITHDRAWN = "WITHDRAWN"  # candidate opted out of the process
    GHOSTED = "GHOSTED"  # candidate stopped responding
