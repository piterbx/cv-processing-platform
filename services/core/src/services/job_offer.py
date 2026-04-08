from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.schemas.job_offer import JobOfferCreate, JobOfferUpdate

from common.models import JobOffer


class JobOfferService:
    async def get_all_offers(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        active_only: bool = False,
    ):
        stmt = select(JobOffer)
        if active_only:
            stmt = stmt.where(JobOffer.is_active)

        stmt = stmt.offset(skip).limit(limit)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def get_offer_by_id(self, db: AsyncSession, offer_id: int):
        stmt = select(JobOffer).where(JobOffer.id == offer_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_offer(self, db: AsyncSession, offer_data: JobOfferCreate):
        new_offer = JobOffer(**offer_data.model_dump())
        db.add(new_offer)
        await db.commit()
        await db.refresh(new_offer)
        return new_offer

    async def update_offer(
        self, db: AsyncSession, offer_id: int, update_data: JobOfferUpdate
    ):
        offer = await self.get_offer_by_id(db, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job offer not found"
            )

        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(offer, key, value)

        await db.commit()
        await db.refresh(offer)
        return offer

    async def delete_offer(self, db: AsyncSession, offer_id: int):
        offer = await self.get_offer_by_id(db, offer_id)
        if not offer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job offer not found"
            )

        await db.delete(offer)
        await db.commit()
        return {"detail": "Job offer deleted successfully"}


job_offer_service = JobOfferService()
