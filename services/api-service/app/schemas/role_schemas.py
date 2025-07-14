from pydantic import BaseModel
import uuid
from typing import Optional

class RoleReadSchema(BaseModel):
    """Schema for reading Role data."""
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True 