from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ReservationCreate(BaseModel):
    user_id: int
    request_id: str


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    user_id: int
    created_at: datetime
