from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional

from .role_schemas import RoleReadSchema
from .organization_schemas import OrganizationReadSchema

# --- User Schemas ---

class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_id: uuid.UUID
    role_id: uuid.UUID

class UserReadSchema(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    
    organization: OrganizationReadSchema
    role: RoleReadSchema

    class Config:
        from_attributes = True

class UserUpdateSchema(BaseModel):
    """Properties to receive via API on update."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None 