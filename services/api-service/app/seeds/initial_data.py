import uuid
import logging
from sqlalchemy.orm import Session
# The sys.path hack is no longer needed as we'll run this as a module
import sys
import os

from app.db.session import SessionLocal
from app.models import User
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    db: Session = SessionLocal()
    
    try:
        # Create default admin user
        admin_user = db.query(User).filter(User.username == "admin").first()
        if not admin_user:
            logger.info("Creating default admin user...")
            admin_user = User(
                id=uuid.uuid4(),
                username="admin",
                email="admin@example.com",
                full_name="System Administrator",
                role="admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True
            )
            db.add(admin_user)
        else:
            logger.info("Default admin user already exists.")
            
        db.commit()
        
        logger.info("Seeding complete.")
        
        print("-" * 50)
        logger.info("Default admin user credentials:")
        print(f"Username: admin")
        print(f"Password: admin123")
        print(f"Email: admin@example.com")
        print(f"Role: admin")
        print("-" * 50)

    except Exception as e:
        logger.error(f"An error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # To run this script correctly, execute it as a module from the api-service root:
    # python -m app.seeds.initial_data
    
    # We need to temporarily add the project root to the path
    # so that the 'app' module can be found when running directly.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sys.path.insert(0, project_root)
    
    from app.db.session import SessionLocal
    from app.models import User
    from app.core.security import get_password_hash

    seed_database()
