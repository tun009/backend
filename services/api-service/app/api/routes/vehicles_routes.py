import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models, schemas
from app.api import dependencies
from app.db.session import get_db
from app.data_access import vehicle_repo

router = APIRouter()

@router.post("/", response_model=schemas.vehicle_schemas.VehicleReadSchema, status_code=status.HTTP_201_CREATED)
def create_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_in: schemas.vehicle_schemas.VehicleCreateSchema,
    current_user: models.User = Depends(dependencies.get_current_active_user)
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
            detail="Invalid Organization ID or other integrity error."
        )

@router.get("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleReadSchema)
def get_vehicle_by_id(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    """
    Get a specific vehicle by ID.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.get("/", response_model=List[schemas.vehicle_schemas.VehicleReadSchema])
def get_vehicles(
    *,
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    """
    Retrieve a list of vehicles.
    """
    vehicles, total = vehicle_repo.get_multi(db, skip=skip, limit=limit)
    return vehicles

@router.put("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleReadSchema)
def update_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
    vehicle_in: schemas.vehicle_schemas.VehicleUpdateSchema,
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    """
    Update a vehicle.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle = vehicle_repo.update(db, db_obj=vehicle, obj_in=vehicle_in)
    return vehicle

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(
    *,
    db: Session = Depends(get_db),
    vehicle_id: uuid.UUID,
    current_user: models.User = Depends(dependencies.get_current_active_user)
):
    """
    Delete a vehicle.
    """
    vehicle = vehicle_repo.get(db, id=vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    vehicle_repo.remove(db, id=vehicle_id)
    return 