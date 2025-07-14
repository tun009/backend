from pydantic import BaseModel
import uuid

class TokenSchema(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

class TokenPayloadSchema(BaseModel):
    sub: str  # Subject - usually the user_id or username

class LoginRequestSchema(BaseModel):
    username: str
    password: str 