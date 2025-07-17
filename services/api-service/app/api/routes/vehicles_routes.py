import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models, schemas
from app.api import dependencies
from app.db.session import get_db
from app.data_access import vehicle_repo
from app.core.cache_decorator import cache, invalidate_vehicle_cache

router = APIRouter()

@router.post("/", response_model=schemas.vehicle_schemas.VehicleReadSchema, status_code=status.HTTP_201_CREATED, dependencies=[Depends(dependencies.get_current_active_user)])
async def create_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_in: schemas.vehicle_schemas.VehicleCreateSchema,
):
    """
    Create a new vehicle.
    """
    existing_vehicle = vehicle_repo.get_by_plate_number(db, plate_number=vehicle_in.plate_number)
    if existing_vehicle:
        raise HTTPException(
            status_code=400,
            detail="A vehicle with this plate number already exists."
        )
    try:
        vehicle = vehicle_repo.create(db, obj_in=vehicle_in)
        return vehicle
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Integrity error occurred."
        )

@router.get("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleReadSchema,  dependencies=[Depends(dependencies.get_current_active_user)])
@cache(key_prefix="vehicle", ttl=600, resource_id_param="vehicle_id")  # Cache for 10 minutes
async def get_vehicle_by_id(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
):
    """
    Get a specific vehicle by ID.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.get("/", response_model=List[schemas.vehicle_schemas.VehicleReadSchema],  dependencies=[Depends(dependencies.get_current_active_user)])
async def get_vehicles(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve a list of vehicles.
    """
    vehicles, total = vehicle_repo.get_multi(db, skip=skip, limit=limit)
    return vehicles

@router.put("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleReadSchema,  dependencies=[Depends(dependencies.get_current_active_user)])
async def update_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
    vehicle_update: schemas.vehicle_schemas.VehicleUpdateSchema,
):
    """
    Update a vehicle.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    try:
        updated_vehicle = vehicle_repo.update(db, db_obj=vehicle, obj_in=vehicle_update)
        
        # Invalidate cache after update
        await invalidate_vehicle_cache(str(vehicle_id))
        
        return updated_vehicle
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="Invalid data or constraint violation."
        )

@router.delete("/{vehicle_id}",  dependencies=[Depends(dependencies.get_current_active_user)])
async def delete_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
):
    """
    Delete a vehicle.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle_repo.remove(db, id=vehicle_id)
    
    # Invalidate cache after deletion
    await invalidate_vehicle_cache(str(vehicle_id))
    
    return {"message": "Vehicle deleted successfully"}

# New endpoint for getting vehicle location (example of specialized caching)
@router.get("/{vehicle_id}/location",dependencies=[Depends(dependencies.get_current_active_user)])
@cache(key_prefix="vehicle_location", ttl=300, resource_id_param="vehicle_id")  # Cache for 5 minutes
async def get_vehicle_location(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
):
    """
    Get latest location of a vehicle.
    This is an example of how to cache GPS/location data.
    """
    # This would typically query the locations TimescaleDB table
    # For now, return mock data
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    # Mock location data - replace with actual TimescaleDB query
    return {
        "vehicle_id": vehicle_id,
        "latitude": 21.0285,  # Mock Hanoi coordinates
        "longitude": 105.8542,
        "speed_kph": 45,
        "heading": 180,
        "timestamp": "2024-01-15T10:30:00Z",
        "engine_status": True
    } 