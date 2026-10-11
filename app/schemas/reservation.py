from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ReservationCreate(BaseModel):
    user_id: int = Field(gt=0)
    request_id: str = Field(min_length=1, max_length=100)


class ReservationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slot_id: int
    user_id: int
    created_at: datetime