from fastapi import APIRouter
from .routes import authentication_routes, vehicles_routes, drivers_routes

api_router = APIRouter()

# Include authentication routes
api_router.include_router(authentication_routes.router, prefix="/auth", tags=["Authentication & Users"])

# Include vehicle routes
api_router.include_router(vehicles_routes.router, prefix="/vehicles", tags=["Vehicles"])

# Include driver routes  
api_router.include_router(drivers_routes.router, prefix="/drivers", tags=["Drivers"]) 