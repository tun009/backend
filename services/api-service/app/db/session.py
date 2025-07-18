from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Correctly build the path to the .env file.
# The `session.py` file is inside `app/db/`, so we need to go up two levels
# to reach the root of the `api-service` where the .env file is.
API_SERVICE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ENV_PATH = os.path.join(API_SERVICE_ROOT, '.env')

load_dotenv(dotenv_path=ENV_PATH)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(f"DATABASE_URL environment variable not set or .env file not found at {ENV_PATH}")

# Sync engine (for existing code)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Async engine (for FastCRUD)
async_database_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
async_engine = create_async_engine(async_database_url)
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine, expire_on_commit=False
)

# Sync dependency (for existing code)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 

# Async dependency (for FastCRUD)
async def get_async_db():
    async with AsyncSessionLocal() as session:
        yield session 