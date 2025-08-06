from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from app.api.api_router import api_router
from app.core.config import settings
from app.services.mqtt_service import MQTTPersistentService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events"""
    # Startup
    logger.info("🚀 Starting OBU Service API...")

    try:
        # Initialize MQTT persistent connection
        await MQTTPersistentService.initialize()
        logger.info("✅ MQTT persistent connection initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize MQTT: {e}")
        # Continue without MQTT - graceful degradation

    logger.info("🎉 OBU Service API started successfully")

    yield

    # Shutdown
    logger.info("🛑 Shutting down OBU Service API...")

    try:
        # Close MQTT persistent connection
        await MQTTPersistentService.close()
        logger.info("✅ MQTT persistent connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing MQTT: {e}")

    logger.info("👋 OBU Service API shutdown complete")


app = FastAPI(
    title="OBU Service API",
    description="Backend API for the OBU Fleet Management System.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add trusted host middleware for security
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this properly for production
)

# Add request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {process_time:.4f}s")
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to OBU Service API!", "version": "0.1.0"}

@app.get("/health", tags=["Health"])
async def health_check():
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "OBU Service API",
        "version": "0.1.0"
    }
