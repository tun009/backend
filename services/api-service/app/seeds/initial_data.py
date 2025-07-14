import uuid
import logging
from sqlalchemy.orm import Session
# The sys.path hack is no longer needed as we'll run this as a module
import sys
import os

from app.db.session import SessionLocal
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
    
    try:
        # 1. Create Default Organization
        default_org = db.query(Organization).filter(Organization.name == "Default Organization").first()
        if not default_org:
            logger.info("Creating default organization...")
            default_org = Organization(id=uuid.uuid4(), name="Default Organization", tax_code="0000000000")
            db.add(default_org)
        else:
            logger.info("Default organization already exists.")

        # 2. Create Roles
        for role_name, role_desc in roles_to_create.items():
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                logger.info(f"Creating '{role_name}' role...")
                role = Role(id=uuid.uuid4(), name=role_name, description=role_desc)
                db.add(role)
            else:
                logger.info(f"'{role_name}' role already exists.")
            
        db.commit()
        
        # Re-query the objects after committing to ensure we have the final state
        final_org = db.query(Organization).filter(Organization.name == "Default Organization").first()
        final_admin_role = db.query(Role).filter(Role.name == "Admin").first()

        logger.info("Seeding complete.")
        
        print("-" * 50)
        logger.info("Use these IDs for creating the first Admin user in Swagger:")
        
        if final_org:
            print(f"Default Organization ID: {final_org.id}")
        else:
            logger.warning("Could not find Default Organization after seeding.")
            
        if final_admin_role:
            print(f"Admin Role ID:         {final_admin_role.id}")
        else:
            logger.warning("Could not find Admin Role after seeding.")

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
    from app.models import Organization, Role

    seed_database()
