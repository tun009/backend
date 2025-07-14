import os
from dotenv import load_dotenv
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# This makes the path OS-independent.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"

load_dotenv(dotenv_path=ENV_PATH)

class Settings:
    """
    A class to hold all application settings.
    It reads settings from environment variables and .env file.
    """
    # --- Project Settings ---
    PROJECT_NAME: str = "OBU Service API"
    
    # --- Database Settings ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")

    # --- JWT Settings ---
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "default_secret_key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

settings = Settings()

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set.")
if settings.JWT_SECRET_KEY == "default_secret_key":
    print("WARNING: JWT_SECRET_KEY is not set in .env file. Using a default, non-secure key.") 