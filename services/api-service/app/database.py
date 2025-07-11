from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# We need to build the full path to the .env file
# The current file is in /app, so we go up one level to the project root
# where the .env file is located.
# Note: In a real microservice, this config might come from a central config service or env vars set by k8s
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(PROJECT_ROOT, '.env')

from dotenv import load_dotenv
load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get the DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 