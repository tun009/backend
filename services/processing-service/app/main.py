import asyncio
import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.services.gps_processor import GPSProcessor
from app.db.session import test_database_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global GPS processor instance
gps_processor = GPSProcessor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan"""
    # Startup
    logger.info("🚀 Starting OBU Processing Service...")
    
    try:
        # Test database connection
        db_ok = await test_database_connection()
        if not db_ok:
            raise Exception("Database connection failed")
        
        # Initialize MQTT connection
        await gps_processor.initialize()
        
        # Start GPS processing
        await gps_processor.start_processing()
        
        logger.info("🎉 OBU Processing Service started successfully")
        logger.info(f"📊 Scan interval: {settings.SCAN_INTERVAL}s")
        logger.info(f"📡 MQTT broker: {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
        
    except Exception as e:
        logger.error(f"❌ Failed to start Processing Service: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down OBU Processing Service...")
    
    try:
        await gps_processor.stop()
        logger.info("✅ GPS processor stopped")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")
    
    logger.info("👋 OBU Processing Service shutdown complete")

app = FastAPI(
    title="OBU Processing Service",
    description="Simple GPS data processor for active journey sessions",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

@app.get("/", tags=["Root"])
async def read_root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "OBU Processing Service is running!",
        "version": "1.0.0",
        "service": "GPS Processor"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "OBU Processing Service",
        "version": "1.0.0",
        "processor": {
            "running": gps_processor.is_running(),
            "mqtt_connected": gps_processor.is_connected(),
            "scan_interval": settings.SCAN_INTERVAL
        },
        "config": {
            "database_url": settings.DATABASE_URL[:50] + "...",
            "mqtt_broker": f"{settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}",
            "mqtt_user": settings.MQTT_USER_NO
        }
    }

@app.get("/status", tags=["Status"])
async def get_status():
    """Get processing status"""
    return {
        "processor_running": gps_processor.is_running(),
        "mqtt_connected": gps_processor.is_connected(),
        "scan_interval_seconds": settings.SCAN_INTERVAL,
        "max_concurrent_devices": settings.MAX_CONCURRENT_DEVICES,
        "mqtt_timeout_seconds": settings.MQTT_TIMEOUT
    }
