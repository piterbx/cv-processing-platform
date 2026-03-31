import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from common.models import Application

logger = logging.getLogger(__name__)


class ApplicationService:
    async def create_pending_application(
        self, db: AsyncSession, document_id: int, job_offer_id: int
    ) -> Application:
        """
        Creates a 'Processing' application linked to a document and job offer,
        or returns the existing one to avoid duplicates.
        """
        query = select(Application).where(
            Application.document_id == document_id,
            Application.job_offer_id == job_offer_id,
        )
        existing_app = (await db.execute(query)).scalar_one_or_none()

        if existing_app:
            logger.info(
                f"Application for doc {document_id} and "
                f"job {job_offer_id} already exists."
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "message": "You have already applied for this position.",
                    "application_id": existing_app.id,
                    "status": existing_app.status,
                    "applied_at": existing_app.applied_at.isoformat()
                    if existing_app.applied_at
                    else None,
                },
            )

        pending_app = Application(
            document_id=document_id, job_offer_id=job_offer_id, status="PROCESSING"
        )

        try:
            db.add(pending_app)
            await db.commit()
            await db.refresh(pending_app)
            return pending_app
        except IntegrityError as e:
            await db.rollback()
            logger.warning(
                f"Integrity error creating application. "
                f"Job offer {job_offer_id} likely doesn't exist. Error: {e}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job offer with ID {job_offer_id} not found.",
            ) from e
        except Exception as e:
            logger.error(
                f"Critical error creating application for doc {document_id}: {e}"
            )
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error during application creation.",
            ) from e


application_service = ApplicationService()
