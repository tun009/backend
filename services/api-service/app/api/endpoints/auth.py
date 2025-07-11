from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud, schemas
from app.database import get_db

router = APIRouter()

@router.post("/users/", response_model=schemas.user.UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.user.UserCreate, db: Session = Depends(get_db)):
    """
    Create a new user.
    """
    db_user_by_email = crud.user.get_user_by_email(db, email=user.email)
    if db_user_by_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    db_user_by_username = crud.user.get_user_by_username(db, username=user.username)
    if db_user_by_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
        
    return crud.user.create_user(db=db, user=user)
