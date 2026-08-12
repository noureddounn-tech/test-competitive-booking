from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.reservation import Reservation


class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(primary_key=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"))
    capacity: Mapped[int] = mapped_column(Integer)

    event: Mapped["Event"] = relationship(back_populates="slots")
    reservations: Mapped[list["Reservation"]] = relationship(back_populates="slot")
