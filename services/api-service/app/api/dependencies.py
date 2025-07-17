from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import jwt, JWTError

from app.core import security
from app.db.session import get_db
from app.data_access import user_repo
from app.models import User
from app.schemas import token_schemas

# Create a simpler security scheme
http_bearer_scheme = HTTPBearer()

def get_current_user(
    auth: HTTPAuthorizationCredentials = Depends(http_bearer_scheme), 
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get the current user from a Bearer token.
    1. Extracts the token from the Authorization header.
    2. Decodes and validates the token.
    3. Fetches the user from the database.
    """
    token = auth.credentials
    try:
        payload = jwt.decode(
            token, security.settings.JWT_SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        username: str | None = payload.get("sub")
        if username is None:
            raise security.CREDENTIALS_EXCEPTION
        token_data = token_schemas.TokenPayloadSchema(sub=username)
    except JWTError:
        raise security.CREDENTIALS_EXCEPTION
    
    user = user_repo.get_by_user_id(db, user_id=token_data.sub)
    if user is None:
        raise security.CREDENTIALS_EXCEPTION
    return user

def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    A further dependency that checks if the user is active.
    """
    if not current_user.is_active:  # type: ignore  
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def get_current_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Dependency that ensures the current user has admin role.
    """
    if str(current_user.role) != "admin":
        raise HTTPException(
            status_code=403, 
            detail="Not enough permissions. Admin role required."
        )
    return current_user

def require_role(role: str):
    """
    Factory function that creates a dependency for requiring a specific role.
    Usage: Depends(require_role("admin"))
    """
    def check_role(current_user: User = Depends(get_current_active_user)) -> User:
        if str(current_user.role) != role:
            raise HTTPException(
                status_code=403,
                detail=f"Not enough permissions. {role.title()} role required."
            )
        return current_user
    return check_role 