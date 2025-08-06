from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

# --- DeviceLog Schemas - FastCRUD Pattern ---

class DeviceLogCreate(BaseModel):
    """Schema for creating new DeviceLog."""
    journey_session_id: int = Field(..., description="ID của journey session")
    device_imei: str = Field(..., max_length=50, description="IMEI của thiết bị")
    mqtt_response: Dict[str, Any] = Field(..., description="Raw MQTT response data")

class DeviceLogUpdate(BaseModel):
    """Schema for updating DeviceLog."""
    mqtt_response: Optional[Dict[str, Any]] = Field(None, description="Updated MQTT response data")

class DeviceLogRead(BaseModel):
    """Schema for reading DeviceLog data."""
    id: int
    journey_session_id: int
    device_imei: str
    mqtt_response: Dict[str, Any]
    collected_at: datetime
    
    class Config:
        from_attributes = True

class DeviceLogSummary(BaseModel):
    """Schema for DeviceLog summary (without full MQTT data)."""
    id: int
    journey_session_id: int
    device_imei: str
    collected_at: datetime
    has_gps_data: bool = Field(default=False, description="Có dữ liệu GPS không")
    
    class Config:
        from_attributes = True
