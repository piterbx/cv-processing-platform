import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.application import ApplicationCreate, ApplicationUpdate

from common.enums import ApplicationStatus
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
            document_id=document_id,
            job_offer_id=job_offer_id,
            status=ApplicationStatus.NEW,
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

    async def get_all_applications(
        self, db: AsyncSession, skip: int = 0, limit: int = 100
    ):
        stmt = select(Application).offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_application_by_id(self, db: AsyncSession, app_id: int):
        stmt = select(Application).where(Application.id == app_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_application(self, db: AsyncSession, app_data: ApplicationCreate):
        """Standard create for API endpoint."""
        new_app = Application(**app_data.model_dump())
        db.add(new_app)
        try:
            await db.commit()
            await db.refresh(new_app)
            return new_app
        except IntegrityError as e:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate or job offer ID.",
            ) from e

    async def update_application_status(
        self, db: AsyncSession, app_id: int, update_data: ApplicationUpdate
    ):
        """Updates the status of an existing application."""
        app = await self.get_application_by_id(db, app_id)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
            )

        app.status = update_data.status
        await db.commit()
        await db.refresh(app)
        return app

    async def delete_application(self, db: AsyncSession, app_id: int):
        app = await self.get_application_by_id(db, app_id)
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Application not found"
            )

        await db.delete(app)
        await db.commit()
        return {"detail": "Application deleted successfully"}


application_service = ApplicationService()
