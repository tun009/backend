from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm

from app import schemas
from app.data_access import user_repo
from app.db.session import get_db
from app.core import security

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


    user_data = schemas.user_schemas.UserReadSchema.from_orm(new_user)
    
    success_content = {
        "code": status.HTTP_201_CREATED,
        "message": f"User '{user_data.username}' created successfully.",
        "data": user_data
    }

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=jsonable_encoder(success_content)
    )


@router.post("/login", response_model=schemas.token_schemas.TokenSchema)
def login_for_access_token(
    *,
    db: Session = Depends(get_db),
    login_data: schemas.token_schemas.LoginRequestSchema
):
    """
    Login to get an access token.
    """
    user = user_repo.get_by_username(db, username=login_data.username)
    if not user or not security.verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    access_token = security.create_access_token(subject=user.id)
    
    # Placeholder for refresh token logic
    return {
        "access_token": access_token,
        "refresh_token": access_token, 
        "token_type": "Bearer",
    }

