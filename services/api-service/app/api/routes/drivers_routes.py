import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_drivers
from app.models import Driver

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
    # Uniqueness checks are removed as per new requirements.
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

    # Build query for drivers
    stmt = select(Driver).order_by(Driver.created_at.desc())

    # Apply search filter if provided (search in both full_name and phone_number)
    if search:
        stmt = stmt.where(
            or_(
                Driver.full_name.icontains(search),
                Driver.phone_number.icontains(search)
            )
        )

    # Apply pagination
    offset = compute_offset(page, items_per_page)
    stmt = stmt.offset(offset).limit(items_per_page)

    # Execute query
    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Convert to response schema
    drivers_list = []
    for driver in rows:
        driver_dict = {
            "id": driver.id,
            "full_name": driver.full_name,
            "phone_number": driver.phone_number,
            "created_at": driver.created_at
        }
        driver_data = schemas.driver_schemas.DriverRead.model_validate(driver_dict)
        drivers_list.append(driver_data)

    # Get total count for pagination
    count_stmt = select(func.count(Driver.id))
    if search:
        count_stmt = count_stmt.where(
            or_(
                Driver.full_name.icontains(search),
                Driver.phone_number.icontains(search)
            )
        )

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Return paginated response
    fake_crud_data = {
        "data": drivers_list,
        "total_count": total or 0
    }

    return paginated_response(
        crud_data=fake_crud_data, page=page, items_per_page=items_per_page
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



