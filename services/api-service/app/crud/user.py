from sqlalchemy.orm import Session
from app import models, schemas
from app.core.security import get_password_hash

def get_user_by_email(db: Session, email: str):
    """
    Get a single user by their email address.
    """
    return db.query(models.User).filter(models.User.email == email).first()

def get_user_by_username(db: Session, username: str):
    """
    Get a single user by their username.
    """
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.user.UserCreate):
    """
    Create a new user in the database.
    """
    # Hash the password before storing
    hashed_password = get_password_hash(user.password)
    
    # Create a new User database model instance
    db_user = models.User(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password,
        organization_id=user.organization_id,
        role_id=user.role_id
    )
    
    # Add the new user to the session and commit to the database
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user
