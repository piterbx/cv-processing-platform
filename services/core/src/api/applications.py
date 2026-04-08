from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.application import ApplicationRead, ApplicationUpdate
from src.services.application import application_service

router = APIRouter()


@router.get("/", response_model=list[ApplicationRead], operation_id="list_applications")
async def get_applications(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    return await application_service.get_all_applications(db, skip, limit)


@router.get("/{app_id}", response_model=ApplicationRead, operation_id="get_application")
async def get_application(app_id: int, db: AsyncSession = Depends(get_db)):
    app = await application_service.get_application_by_id(db, app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch(
    "/{app_id}/status",
    response_model=ApplicationRead,
    operation_id="update_application_status",
)
async def update_application_status(
    app_id: int, update_data: ApplicationUpdate, db: AsyncSession = Depends(get_db)
):
    """Updates only the status of the application (e.g., from NEW to REJECTED/HIRED)."""
    return await application_service.update_application_status(db, app_id, update_data)


@router.delete(
    "/{app_id}", status_code=status.HTTP_200_OK, operation_id="delete_application"
)
async def delete_application(app_id: int, db: AsyncSession = Depends(get_db)):
    return await application_service.delete_application(db, app_id)
