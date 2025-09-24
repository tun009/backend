import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_drivers

router = APIRouter()


@router.post(
    "/",
    response_model=schemas.driver_schemas.DriverRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_driver(
    driver_in: schemas.driver_schemas.DriverCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """Create a new driver."""
    # Check duplicates using FastCRUD's exists method
    if await crud_drivers.exists(db=db, license_number=driver_in.license_number):
        raise HTTPException(status_code=400, detail="License number already exists")

    if driver_in.phone_number and await crud_drivers.exists(
        db=db, phone_number=driver_in.phone_number
    ):
        raise HTTPException(status_code=400, detail="Phone number already exists")

    # if driver_in.card_id and await crud_drivers.exists(
    #     db=db, card_id=driver_in.card_id
    # ):
    #     raise HTTPException(status_code=400, detail="Card ID already exists")

    return await crud_drivers.create(db=db, object=driver_in)


@router.get("/{driver_id}", response_model=schemas.driver_schemas.DriverRead)
async def get_driver(
    driver_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """Get driver by ID."""
    driver = await crud_drivers.get(
        db=db, id=driver_id, schema_to_select=schemas.driver_schemas.DriverRead
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver


@router.get(
    "/", response_model=PaginatedListResponse[schemas.driver_schemas.DriverRead]
)
async def get_drivers(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    page: int = 1,
    items_per_page: int = 10,
    search: Optional[str] = None,
):
    """Get drivers with pagination and search."""
    filters = {}
    if search:
        # FastCRUD supports icontains filtering
        filters["full_name__icontains"] = search

    drivers_data = await crud_drivers.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        schema_to_select=schemas.driver_schemas.DriverRead,
        **filters
    )

    return paginated_response(
        crud_data=drivers_data, page=page, items_per_page=items_per_page
    )


@router.patch("/{driver_id}", response_model=schemas.driver_schemas.DriverRead)
async def update_driver(
    driver_id: uuid.UUID,
    driver_update: schemas.driver_schemas.DriverUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """Update driver (partial update)."""
    # Check if driver exists
    if not await crud_drivers.exists(db=db, id=driver_id):
        raise HTTPException(status_code=404, detail="Driver not found")

    await crud_drivers.update(db=db, object=driver_update, id=driver_id)

    # Return updated object
    updated_driver = await crud_drivers.get(
        db=db,
        id=driver_id,
        schema_to_select=schemas.driver_schemas.DriverRead
    )
    return updated_driver


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_driver(
    driver_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """Delete driver."""
    if not await crud_drivers.exists(db=db, id=driver_id):
        raise HTTPException(status_code=404, detail="Driver not found")

    await crud_drivers.delete(db=db, id=driver_id)


@router.get(
    "/license/{license_number}", response_model=schemas.driver_schemas.DriverRead
)
async def get_driver_by_license(
    license_number: str,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """Get driver by license number."""
    driver = await crud_drivers.get(
        db=db,
        license_number=license_number,
        schema_to_select=schemas.driver_schemas.DriverRead,
    )
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    return driver
