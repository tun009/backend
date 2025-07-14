from sqlalchemy.orm import Session

from app.core.security import get_password_hash, verify_password
from app.models import User
from app.schemas import user_schemas

class UserRepository:
    def authenticate(self, db: Session, *, username: str, password: str) -> User | None:
        user = self.get_by_username(db, username=username)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):  # type: ignore
            return None
        return user
        
    def get_by_email(self, db: Session, *, email: str) -> User | None:
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, *, username: str) -> User | None:
        return db.query(User).filter(User.username == username).first()
    
    def get_by_user_id(self, db: Session, *, user_id: str) -> User | None:
        return db.query(User).filter(User.id == user_id).first()
    
    def create(self, db: Session, *, obj_in: user_schemas.UserCreateSchema) -> User:
        hashed_password = get_password_hash(obj_in.password)
        
        db_obj = User(
            username=obj_in.username,
            email=obj_in.email,
            full_name=obj_in.full_name,
            hashed_password=hashed_password,
            organization_id=obj_in.organization_id,
            role_id=obj_in.role_id
        )
        
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

user_repo = UserRepository()
