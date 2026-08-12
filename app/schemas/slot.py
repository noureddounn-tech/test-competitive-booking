from pydantic import BaseModel, ConfigDict


class SlotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: int
    capacity: int
    available: int
