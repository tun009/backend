import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- Vehicle Schemas ---

class VehicleBase(BaseModel):
    plate_number: str = Field(..., max_length=50)
    load_capacity_kg: Optional[int] = None
    type: Optional[str] = Field(None, max_length=50)

class VehicleCreate(VehicleBase):
    pass

class VehicleUpdate(BaseModel):
    plate_number: Optional[str] = Field(None, max_length=50)
    load_capacity_kg: Optional[int] = None
    type: Optional[str] = Field(None, max_length=50)

class VehicleRead(VehicleBase):
    id: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True

