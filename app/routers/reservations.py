from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Event, Reservation, Slot, User
from app.schemas.reservation import (
    ReservationCreate,
    ReservationListItem,
    ReservationPage,
    ReservationRead,
)

router = APIRouter(tags=["reservations"])


async def _find_by_request_id(
    db: AsyncSession, user_id: int, request_id: str
) -> Reservation | None:
    """Return the reservation already associated with this user's request key."""
    return await db.scalar(
        select(Reservation).where(
            Reservation.user_id == user_id,
            Reservation.request_id == request_id,
        )
    )


def _ensure_same_slot(reservation: Reservation, slot_id: int) -> Reservation:
    """Prevent reusing an idempotency key for a different operation."""
    if reservation.slot_id != slot_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="request_id has already been used for another slot",
        )
    return reservation


@router.post(
    "/slots/{slot_id}/reservations",
    response_model=ReservationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    slot_id: int, payload: ReservationCreate, db: AsyncSession = Depends(get_db)
) -> ReservationRead:
    try:
        async with db.begin():
            # Fast path: a retry should return the original result without
            # consuming capacity a second time.
            existing = await _find_by_request_id(db, payload.user_id, payload.request_id)
            if existing is not None:
                return _ensure_same_slot(existing, slot_id)

            # All writers for one slot serialize on this row. The lock, count,
            # and insert must be in the same transaction to prevent overselling.
            slot = await db.scalar(select(Slot).where(Slot.id == slot_id).with_for_update())
            if slot is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Slot not found",
                )

            # A concurrent retry may have committed while this request waited
            # for the slot lock, so check the idempotency key again.
            existing = await _find_by_request_id(db, payload.user_id, payload.request_id)
            if existing is not None:
                return _ensure_same_slot(existing, slot_id)

            user = await db.get(User, payload.user_id)
            if user is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            confirmed_count = await db.scalar(
                select(func.count(Reservation.id)).where(
                    Reservation.slot_id == slot_id,
                    Reservation.status == "confirmed",
                )
            )
            if confirmed_count >= slot.capacity:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Slot is fully booked",
                )

            reservation = Reservation(
                slot_id=slot_id,
                user_id=payload.user_id,
                request_id=payload.request_id,
                status="confirmed",
            )
            db.add(reservation)
            # Flush assigns the primary key and detects constraint violations
            # before leaving the transaction context.
            await db.flush()
            return reservation
    except IntegrityError:
        # The unique constraint on (user_id, request_id) also protects against
        # the same key being submitted concurrently for different slots. The
        # transaction context has rolled back; fetch the winning request.
        await db.rollback()
        existing = await _find_by_request_id(db, payload.user_id, payload.request_id)
        if existing is not None:
            return _ensure_same_slot(existing, slot_id)
        # It was a different integrity failure; preserve the original error.
        raise


@router.get(
    "/slots/{slot_id}/reservations",
    response_model=ReservationPage,
)
async def list_slot_reservations(
    slot_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> ReservationPage:
    # The grouped outer join distinguishes a missing slot from an existing
    # slot with no reservations, without an extra existence query.
    count_row = (
        await db.execute(
            select(Slot.id, func.count(Reservation.id))
            .outerjoin(Reservation, Reservation.slot_id == Slot.id)
            .where(Slot.id == slot_id)
            .group_by(Slot.id)
        )
    ).one_or_none()
    if count_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slot not found",
        )
    total = count_row[1]

    # Fetch all display fields in one joined query to avoid one query per
    # reservation (the N+1 problem). Include cancelled rows for history.
    rows = (
        await db.execute(
            select(
                Reservation.id.label("id"),
                Reservation.slot_id.label("slot_id"),
                Reservation.user_id.label("user_id"),
                User.name.label("user_name"),
                User.email.label("user_email"),
                Event.id.label("event_id"),
                Event.name.label("event_name"),
                Event.date.label("event_date"),
                Reservation.status.label("status"),
                Reservation.created_at.label("created_at"),
            )
            .join(User, User.id == Reservation.user_id)
            .join(Slot, Slot.id == Reservation.slot_id)
            .join(Event, Event.id == Slot.event_id)
            .where(Reservation.slot_id == slot_id)
            .order_by(Reservation.created_at.desc(), Reservation.id.desc())
            .offset(offset)
            .limit(limit)
        )
    ).mappings().all()

    return ReservationPage(
        items=[ReservationListItem.model_validate(row) for row in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_reservation(
    reservation_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    # Read the slot ID without locking the reservation, then acquire locks in
    # the same order as creation: slot row, then reservation row. This keeps
    # capacity changes serialized with new bookings and avoids lock-order
    # deadlocks.
    async with db.begin():
        reservation = await db.scalar(
            select(Reservation).where(Reservation.id == reservation_id)
        )
        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found",
            )

        slot = await db.scalar(
            select(Slot).where(Slot.id == reservation.slot_id).with_for_update()
        )
        if slot is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Slot not found",
            )

        # Re-read and lock after acquiring the slot lock: another cancellation
        # may have changed the status while this request was waiting.
        reservation = await db.scalar(
            select(Reservation)
            .where(Reservation.id == reservation_id)
            .with_for_update()
        )
        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found",
            )

        # Cancellation is idempotent. Keep the row for audit/history and only
        # release capacity by excluding it from confirmed-reservation counts.
        if reservation.status == "confirmed":
            reservation.status = "cancelled"
            await db.flush()