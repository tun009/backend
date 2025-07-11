from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import schemas
from app.data_access import user_repo
from app.db.session import get_db

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
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    user = user_repo.get_by_username(db, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this username already exists in the system.",
        )
    
    new_user = user_repo.create(db=db, obj_in=user_in)
    return new_user
