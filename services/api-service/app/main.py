from fastapi import FastAPI
from app.api.api_router import api_router

app = FastAPI(
    title="OBU Service API",
    description="Backend API for the OBU Fleet Management System.",
    version="0.1.0"
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/", tags=["Root"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to OBU Service API!"}

