import uuid
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# --- JourneySession Schemas - FastCRUD Pattern ---

class JourneySessionCreate(BaseModel):
    """Schema for creating new JourneySession."""
    vehicle_id: uuid.UUID = Field(..., description="ID của xe")
    driver_id: uuid.UUID = Field(..., description="ID của tài xế")
    start_time: datetime = Field(..., description="Thời gian bắt đầu ca dự kiến")
    end_time: datetime = Field(..., description="Thời gian kết thúc ca dự kiến")
    notes: Optional[str] = Field(None, description="Ghi chú cho ca làm việc")

    @model_validator(mode='after')
    def validate_times(self):
        if self.end_time <= self.start_time:
            raise ValueError('Thời gian kết thúc phải sau thời gian bắt đầu')
        return self

class JourneySessionUpdate(BaseModel):
    """Schema for updating JourneySession."""
    end_time: Optional[datetime] = Field(None, description="Thời gian kết thúc ca")
    total_distance_km: Optional[Decimal] = Field(None, description="Tổng quãng đường (km)")
    notes: Optional[str] = Field(None, description="Ghi chú")
    status: Optional[str] = Field(None, description="Trạng thái ca làm việc")

class JourneySessionStatusUpdate(BaseModel):
    """Schema for updating only status of JourneySession."""
    status: str = Field(..., description="Trạng thái mới")
    
    @field_validator('status')
    @classmethod
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'active', 'completed', 'cancelled']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {allowed_statuses}')
        return v

class JourneySessionRead(BaseModel):
    """Schema for reading JourneySession data."""
    id: int
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    start_time: datetime
    end_time: Optional[datetime]
    total_distance_km: Optional[Decimal]
    notes: Optional[str]
    status: Optional[str]
    activated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

class JourneySessionWithDetails(BaseModel):
    """Schema for JourneySession with related data."""
    id: int
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    start_time: datetime
    end_time: Optional[datetime]
    total_distance_km: Optional[Decimal]
    notes: Optional[str]
    status: Optional[str]
    activated_at: Optional[datetime]

    # Related data (will be populated by API)
    vehicle_plate_number: Optional[str] = Field(None, description="Biển số xe")
    driver_name: Optional[str] = Field(None, description="Tên tài xế")
    device_imei: Optional[str] = Field(None, description="IMEI thiết bị")

    class Config:
        from_attributes = True

class JourneySessionRealtime(BaseModel):
    """Schema for active JourneySession with realtime data from device_logs."""
    id: int
    vehicle_id: uuid.UUID
    driver_id: uuid.UUID
    start_time: datetime
    end_time: Optional[datetime]
    status: Optional[str]
    activated_at: Optional[datetime]

    # Related data
    plate_number: Optional[str] = Field(None, description="Biển số xe")
    driver_name: Optional[str] = Field(None, description="Tên tài xế")
    imei: Optional[str] = Field(None, description="IMEI thiết bị")

    # Realtime data (toàn bộ mqtt_response từ device_logs)
    realtime: dict = Field(default_factory=dict, description="Dữ liệu realtime từ device logs")

    class Config:
        from_attributes = True

class JourneyHistoryPoint(BaseModel):
    """Schema for journey history point with essential GPS and battery data."""
    id: int
    collected_at: datetime

    # GPS data
    latitude: Optional[float] = None
    gps_longitude: Optional[float] = None
    gps_speed: Optional[float] = None
    gps_valid: Optional[int] = None
    gps_enable: Optional[int] = None

    # Battery data
    bat_percent: Optional[int] = None

    class Config:
        from_attributes = True

class JourneySessionHistoryResponse(BaseModel):
    """Schema for journey session history response."""
    plate_number: Optional[str] = None
    driver_name: Optional[str] = None
    imei: Optional[str] = None
    id: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    data: List[JourneyHistoryPoint]
    class Config:
        from_attributes = True
