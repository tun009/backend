from pydantic import BaseModel, EmailStr
import uuid
from typing import Optional

# Properties to be received via API on creation
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    organization_id: uuid.UUID
    role_id: uuid.UUID

# Properties to return to client
class UserRead(BaseModel):
    id: uuid.UUID
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    organization_id: uuid.UUID
    role_id: uuid.UUID

    class Config:
        from_attributes = True

# Properties to be received via API on update
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None 