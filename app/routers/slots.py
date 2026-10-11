from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Reservation, Slot
from app.schemas.slot import SlotRead

router = APIRouter(prefix="/slots", tags=["slots"])


@router.get("/{slot_id}", response_model=SlotRead)
async def get_slot_availability(slot_id: int, db: AsyncSession = Depends(get_db)) -> SlotRead:
    confirmed_count_query = (
        select(func.count(Reservation.id))
        .where(
            Reservation.slot_id == Slot.id,
            Reservation.status == "confirmed",
        )
        .scalar_subquery()
    )
    result = await db.execute(
        select(Slot, confirmed_count_query.label("confirmed_count")).where(Slot.id == slot_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )

    slot, confirmed_count = row
    # One SQL statement gives a consistent snapshot for capacity and bookings.
    # Clamp to zero defensively if legacy or manually edited data exceeds capacity.
    available = max(slot.capacity - confirmed_count, 0)
    return SlotRead(
        id=slot.id,
        event_id=slot.event_id,
        capacity=slot.capacity,
        available=available,
    )