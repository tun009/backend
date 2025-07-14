from pydantic import BaseModel
import uuid
from typing import Optional

class OrganizationReadSchema(BaseModel):
    """Schema for reading Organization data."""
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True 