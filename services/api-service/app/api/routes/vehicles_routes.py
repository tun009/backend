import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_vehicles

router = APIRouter()

@router.post("/", response_model=schemas.vehicle_schemas.VehicleRead, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    vehicle_in: schemas.vehicle_schemas.VehicleCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Create a new vehicle."""
    # Check duplicate plate number using FastCRUD's exists method
    if await crud_vehicles.exists(db=db, plate_number=vehicle_in.plate_number):
        raise HTTPException(status_code=400, detail="Plate number already exists")
    
    return await crud_vehicles.create(db=db, object=vehicle_in)

@router.get("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleRead)
async def get_vehicle(
    vehicle_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Get vehicle by ID."""
    vehicle = await crud_vehicles.get(db=db, id=vehicle_id, schema_to_select=schemas.vehicle_schemas.VehicleRead)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.get("/", response_model=PaginatedListResponse[schemas.vehicle_schemas.VehicleRead])
async def get_vehicles(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    page: int = 1,
    items_per_page: int = 10,
    search: Optional[str] = None
):
    """Get vehicles with pagination and search."""
    filters = {}
    if search:
        # FastCRUD supports icontains filtering for plate number
        filters["plate_number__icontains"] = search
    
    vehicles_data = await crud_vehicles.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        schema_to_select=schemas.vehicle_schemas.VehicleRead,
        **filters
    )
    
    return paginated_response(crud_data=vehicles_data, page=page, items_per_page=items_per_page)

@router.patch("/{vehicle_id}", response_model=schemas.vehicle_schemas.VehicleRead)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    vehicle_update: schemas.vehicle_schemas.VehicleUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Update vehicle (partial update)."""
    # Check if vehicle exists
    if not await crud_vehicles.exists(db=db, id=vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    await crud_vehicles.update(db=db, object=vehicle_update, id=vehicle_id)
    
    return {"message": "Vehicle updated"}

@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vehicle(
    vehicle_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Delete vehicle."""
    if not await crud_vehicles.exists(db=db, id=vehicle_id):
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    await crud_vehicles.delete(db=db, id=vehicle_id)

@router.get("/plate/{plate_number}", response_model=schemas.vehicle_schemas.VehicleRead)
async def get_vehicle_by_plate(
    plate_number: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Get vehicle by plate number."""
    vehicle = await crud_vehicles.get(db=db, plate_number=plate_number, schema_to_select=schemas.vehicle_schemas.VehicleRead)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle 