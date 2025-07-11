from fastapi import APIRouter
from .routes import authentication_routes

api_router = APIRouter()

# Include authentication routes
api_router.include_router(authentication_routes.router, prefix="/auth", tags=["Authentication & Users"]) 