from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.data_access import user_repo
from app.db.session import get_db
from app.core import security
from app.api import dependencies
from app import models

router = APIRouter()

@router.post("/register", response_model=schemas.user_schemas.UserReadSchema, status_code=status.HTTP_201_CREATED)
def register_new_user(
    *,
    db: Session = Depends(get_db),
    user_in: schemas.user_schemas.UserCreateSchema
):
    """
    Create a new user.
    """
    user = user_repo.get_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    user = user_repo.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )

    new_user = user_repo.create(db, obj_in=user_in)
    
    return new_user


@router.post("/login", response_model=schemas.token_schemas.TokenSchema)
def login_for_access_token(
    *,
    db: Session = Depends(get_db),
    login_data: schemas.token_schemas.LoginRequestSchema
):
    """
    Login to get an access token.
    """
    user = user_repo.authenticate(db, username=login_data.username, password=login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:  # type: ignore
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = security.create_access_token(subject=user.id)  # type: ignore
    
    # Placeholder for refresh token logic
    return {
        "access_token": access_token,
        "refresh_token": access_token, 
        "token_type": "Bearer",
    }


@router.get("/users/me", response_model=schemas.user_schemas.UserReadSchema)
def read_users_me(
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    return current_user

