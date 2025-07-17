import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- Driver Schemas - FastCRUD Pattern ---

class DriverCreate(BaseModel):
    """Schema for creating new Driver."""
    full_name: str = Field(..., min_length=2, max_length=100)
    license_number: str = Field(..., min_length=5, max_length=50)
    card_id: Optional[str] = Field(None, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)

class DriverUpdate(BaseModel):
    """Schema for updating Driver."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    license_number: Optional[str] = Field(None, min_length=5, max_length=50)
    card_id: Optional[str] = Field(None, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)

class DriverRead(BaseModel):
    """Schema for reading Driver data."""
    id: uuid.UUID
    full_name: str
    license_number: str
    card_id: Optional[str]
    phone_number: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True 