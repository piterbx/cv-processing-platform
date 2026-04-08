from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.session import get_db
from src.schemas.job_offer import JobOfferCreate, JobOfferRead, JobOfferUpdate
from src.services.job_offer import job_offer_service

router = APIRouter()


@router.get("/", response_model=list[JobOfferRead], operation_id="list_job_offers")
async def get_job_offers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    active_only: bool = Query(False, description="Filter only active job offers"),
    db: AsyncSession = Depends(get_db),
):
    return await job_offer_service.get_all_offers(db, skip, limit, active_only)


@router.get("/{offer_id}", response_model=JobOfferRead, operation_id="get_job_offer")
async def get_job_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    offer = await job_offer_service.get_offer_by_id(db, offer_id)
    if not offer:
        raise HTTPException(status_code=404, detail="Job offer not found")
    return offer


@router.post(
    "/",
    response_model=JobOfferRead,
    status_code=status.HTTP_201_CREATED,
    operation_id="create_job_offer",
)
async def create_job_offer(
    offer_data: JobOfferCreate, db: AsyncSession = Depends(get_db)
):
    return await job_offer_service.create_offer(db, offer_data)


@router.put("/{offer_id}", response_model=JobOfferRead, operation_id="update_job_offer")
async def update_job_offer(
    offer_id: int, update_data: JobOfferUpdate, db: AsyncSession = Depends(get_db)
):
    return await job_offer_service.update_offer(db, offer_id, update_data)


@router.delete(
    "/{offer_id}", status_code=status.HTTP_200_OK, operation_id="delete_job_offer"
)
async def delete_job_offer(offer_id: int, db: AsyncSession = Depends(get_db)):
    return await job_offer_service.delete_offer(db, offer_id)
