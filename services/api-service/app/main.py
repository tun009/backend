from fastapi import FastAPI

app = FastAPI(title="OBU API Service")


@app.get("/", tags=["Root"])
async def read_root():
    """A simple health check endpoint."""
    return {"status": "ok", "message": "Welcome to OBU API Service!"}
