from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional

# --- User Schemas ---

class UserCreateSchema(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "admin"

class UserReadSchema(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    role: str

    class Config:
        from_attributes = True

class UserUpdateSchema(BaseModel):
    """Properties to receive via API on update."""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None 