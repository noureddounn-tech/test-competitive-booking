from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.reservation import ReservationRead
from app.schemas.slot import SlotRead

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/{slot_id}", response_model=SlotRead)
async def get_slot_availability(slot_id: int, db: AsyncSession = Depends(get_db)) -> SlotRead:
    # TODO: return the slot with its remaining availability (SlotRead.available).
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not implemented")


@router.get("/{slot_id}/reservations", response_model=list[ReservationRead])
async def list_slot_reservations(
    slot_id: int, db: AsyncSession = Depends(get_db)
) -> list[ReservationRead]:
    # TODO: list reservations for this slot, with user and event info, without N+1 queries.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not implemented")
