from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from app.api.api_router import api_router
from app.core.config import settings
from app.core.redis_client import redis_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("🚀 OBU Service starting up...")
    
    try:
        # Initialize Redis
        if settings.CACHE_ENABLED:
            await redis_client.initialize()
            logger.info("✅ Redis initialized successfully")
        else:
            logger.info("⚠️ Redis caching is disabled")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Redis: {e}")
        # Continue without Redis if it fails
    
    logger.info("🎉 OBU Service startup complete")
    
    yield
    
    # Shutdown
    logger.info("🔄 OBU Service shutting down...")
    
    try:
        if settings.CACHE_ENABLED:
            await redis_client.close()
            logger.info("✅ Redis connections closed")
    except Exception as e:
        logger.error(f"❌ Error during Redis shutdown: {e}")
    
    logger.info("👋 OBU Service shutdown complete")

app = FastAPI(
    title="OBU Service API",
    description="Backend API for the OBU Fleet Management System.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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
    redis_status = "connected" if settings.CACHE_ENABLED else "disabled"
    
    # Test Redis connection if enabled
    if settings.CACHE_ENABLED:
        try:
            await redis_client.get_client().ping()
            redis_status = "connected"
        except:
            redis_status = "disconnected"
    
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "service": "OBU Service API",
        "version": "0.1.0",
        "redis": redis_status,
        "cache_enabled": settings.CACHE_ENABLED
    }
