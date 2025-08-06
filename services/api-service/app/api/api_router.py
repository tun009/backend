from fastapi import APIRouter
from .routes import authentication_routes, vehicles_routes, drivers_routes, devices_routes, journey_sessions_routes

api_router = APIRouter()

api_router.include_router(authentication_routes.router, prefix="/auth", tags=["Authentication & Users"])

api_router.include_router(vehicles_routes.router, prefix="/vehicles", tags=["Vehicles"])

api_router.include_router(drivers_routes.router, prefix="/drivers", tags=["Drivers"])

api_router.include_router(devices_routes.router, prefix="/devices", tags=["Devices"])

api_router.include_router(journey_sessions_routes.router, prefix="/journey-sessions", tags=["Journey Sessions"])