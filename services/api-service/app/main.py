from fastapi import FastAPI
from app.api.endpoints import auth

app = FastAPI(title="OBU API Service")

app.include_router(auth.router, prefix="/api/v1", tags=["Authentication"])

@app.get("/", tags=["Root"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to OBU API Service!"}

