import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- Device Schemas - FastCRUD Pattern ---

class DeviceCreate(BaseModel):
    """Schema for creating new Device."""
    vehicle_id: Optional[str] = Field(None, description="Vehicle to assign (optional)")
    imei: str = Field(..., max_length=50)
    serial_number: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=20)

class DeviceUpdate(BaseModel):
    """Schema for updating Device."""
    vehicle_id: Optional[str] = None
    imei: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None

class DeviceRead(BaseModel):
    """Schema for reading Device data."""
    id: uuid.UUID
    vehicle_id: Optional[str]
    imei: str
    serial_number: Optional[str]
    firmware_version: Optional[str]
    installed_at: datetime
    
    class Config:
        from_attributes = True

class DeviceAssignment(BaseModel):
    """Schema for device assignment."""
    vehicle_id: Optional[str] 