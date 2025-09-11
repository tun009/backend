import os
from dotenv import load_dotenv
from pathlib import Path

# Load .env từ api-service (shared config)
api_service_env = Path(__file__).resolve().parent.parent.parent.parent / "api-service" / ".env"
load_dotenv(dotenv_path=api_service_env)

class Settings:
    """
    Configuration settings for Processing Service.
    Sử dụng chung .env từ api-service.
    """
    # --- Project Settings ---
    PROJECT_NAME: str = "OBU Processing Service"
    
    # --- Database Settings (từ api-service) ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    
    # --- MQTT Settings (từ api-service) ---
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "103.21.151.183")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))
    MQTT_USERNAME: str = os.getenv("MQTT_USERNAME", "dev1")
    MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD", "dev1")
    MQTT_USER_NO: str = os.getenv("MQTT_USER_NO", "kh4423")
    MQTT_TIMEOUT: int = int(os.getenv("MQTT_TIMEOUT", "10"))
    
    # --- Processing Settings ---
    SCAN_INTERVAL: int = int(os.getenv("GPS_COLLECTION_INTERVAL", "5"))  # Use GPS_COLLECTION_INTERVAL from .env
    MAX_CONCURRENT_DEVICES: int = int(os.getenv("MAX_CONCURRENT_DEVICES", "5"))
    
    # --- Logging Settings ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()

if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set in api-service/.env")
