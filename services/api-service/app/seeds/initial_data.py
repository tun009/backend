import uuid
import logging
from sqlalchemy.orm import Session
# We need to adjust the path to import from the 'app' package
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Organization, Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    db: Session = SessionLocal()
    
    roles_to_create = {
        "Admin": "Administrator with all permissions.",
        "Manager": "Manager with operational permissions.",
        "Viewer": "Viewer with read-only permissions."
    }
    
    created_ids = {}

    try:
        # 1. Create Default Organization
        default_org = db.query(Organization).filter(Organization.name == "Default Organization").first()
        if not default_org:
            logger.info("Creating default organization...")
            default_org = Organization(id=uuid.uuid4(), name="Default Organization", tax_code="0000000000")
            db.add(default_org)
        else:
            logger.info("Default organization already exists.")
        created_ids['organization_id'] = default_org.id

        # 2. Create Roles
        for role_name, role_desc in roles_to_create.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logger.info(f"Creating '{role_name}' role...")
                role = Role(id=uuid.uuid4(), name=role_name, description=role_desc)
                db.add(role)
            else:
                logger.info(f"'{role_name}' role already exists.")
            
            if role_name == "Admin":
                created_ids['admin_role_id'] = role.id

        db.commit()
        
        # Re-query to get the committed IDs if they were newly created
        if 'admin_role_id' not in created_ids:
             admin_role = db.query(Role).filter(Role.name == "Admin").first()
             created_ids['admin_role_id'] = admin_role.id

        logger.info("Seeding complete.")
        
        # 3. Print the IDs to use for creating the first user
        print("-" * 50)
        logger.info("Use these IDs for creating the first Admin user in Swagger:")
        print(f"Default Organization ID: {created_ids.get('organization_id')}")
        print(f"Admin Role ID:         {created_ids.get('admin_role_id')}")
        print("-" * 50)

    except Exception as e:
        logger.error(f"An error occurred during seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
