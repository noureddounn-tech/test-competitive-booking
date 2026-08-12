from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.reservation import ReservationCreate, ReservationRead

router = APIRouter(tags=["reservations"])


@router.post(
    "/slots/{slot_id}/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    slot_id: int, payload: ReservationCreate, db: AsyncSession = Depends(get_db)
) -> ReservationRead:
    # TODO: create a reservation with zero overselling and idempotent retries on request_id.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not implemented")


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(reservation_id: int, db: AsyncSession = Depends(get_db)) -> None:
    # TODO: cancel the reservation.
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="not implemented")
