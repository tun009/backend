import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

# --- Vehicle Schemas - FastCRUD Pattern ---

class VehicleCreate(BaseModel):
    """Schema for creating new Vehicle."""
    plate_number: str = Field(..., max_length=20)
    type: Optional[str] = Field(None, max_length=50)
    load_capacity_kg: Optional[int] = Field(None)
    registration_expiry: Optional[date] = Field(None)

class VehicleUpdate(BaseModel):
    """Schema for updating Vehicle."""
    plate_number: Optional[str] = Field(None, max_length=20)
    type: Optional[str] = Field(None, max_length=50)
    load_capacity_kg: Optional[int] = Field(None)
    registration_expiry: Optional[date] = Field(None)

class VehicleRead(BaseModel):
    """Schema for reading Vehicle data."""
    id: uuid.UUID
    plate_number: str
    type: Optional[str]
    load_capacity_kg: Optional[int]
    registration_expiry: Optional[date]
    created_at: datetime
    
    class Config:
        from_attributes = True 