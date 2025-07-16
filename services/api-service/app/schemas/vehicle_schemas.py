import uuid
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date

# --- Vehicle Schemas ---

class VehicleBaseSchema(BaseModel):
    """Schema chung chứa các trường cơ bản của Vehicle."""
    plate_number: str = Field(..., max_length=20, description="Biển số xe")
    type: Optional[str] = Field(None, max_length=50, description="Loại xe")
    load_capacity_kg: Optional[int] = Field(None, description="Tải trọng (kg)")
    registration_expiry: Optional[date] = Field(None, description="Hạn đăng kiểm")

class VehicleCreateSchema(VehicleBaseSchema):
    """Schema cho việc tạo mới Vehicle."""
    organization_id: uuid.UUID

class VehicleUpdateSchema(VehicleBaseSchema):
    """Schema cho việc cập nhật Vehicle. Tất cả các trường đều là tùy chọn."""
    # Kế thừa từ Base nhưng ghi đè lại để cho phép optional
    plate_number: Optional[str] = Field(None, max_length=20)
    type: Optional[str] = Field(None, max_length=50)
    load_capacity_kg: Optional[int] = Field(None)
    registration_expiry: Optional[date] = Field(None)
    organization_id: Optional[uuid.UUID] = None

class VehicleReadSchema(VehicleBaseSchema):
    """Schema cho việc đọc dữ liệu Vehicle, sẽ được trả về cho client."""
    id: uuid.UUID
    organization_id: uuid.UUID
    
    class Config:
        from_attributes = True 