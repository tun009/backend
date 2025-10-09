import uuid
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_devices
from app.models import Device
from app.services.mqtt_service import (
    get_mqtt_persistent_service,
    MQTTPersistentService,
    DeviceTimeoutError,
    MQTTConnectionError,
    InvalidResponseError
)

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=schemas.device_schemas.DeviceRead, status_code=status.HTTP_201_CREATED)
async def create_device(
    device_in: schemas.device_schemas.DeviceCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Create a new device."""
    # Check duplicate IMEI using FastCRUD's exists method
    if await crud_devices.exists(db=db, imei=device_in.imei):
        raise HTTPException(status_code=400, detail="Device no đã tồn tại trong hệ thống")

    # Vehicle logic removed - devices now contain vehicle info directly

    return await crud_devices.create(db=db, object=device_in)

@router.get("/unassigned", response_model=list[schemas.device_schemas.DeviceRead])
async def get_unassigned_devices(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Get all devices that are not assigned to any vehicle."""
    stmt = (
        select(Device)
        .where(Device.vehicle_id.is_(None))
        .order_by(Device.installed_at.desc())
    )

    result = await db.execute(stmt)
    devices = result.scalars().all()

    return [schemas.device_schemas.DeviceRead.model_validate(device) for device in devices]


@router.get("/{device_id}", response_model=schemas.device_schemas.DeviceRead)
async def get_device(
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Get device by ID."""
    device = await crud_devices.get(db=db, id=device_id, schema_to_select=schemas.device_schemas.DeviceRead)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device

from app.models import Vehicle

@router.get("/", response_model=PaginatedListResponse[schemas.device_schemas.DeviceReadWithRealtime])
async def get_devices(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    mqtt_service: Annotated[MQTTPersistentService, Depends(get_mqtt_persistent_service)],
    page: int = 1,
    items_per_page: int = 10,
    search: Optional[str] = None,
    include_realtime: bool = True
):
    """Get devices with pagination and search, including vehicle info."""

    # Build query with an outer join to include vehicle info
    stmt = (
        select(Device, Vehicle.plate_number)
        .outerjoin(Vehicle, Device.vehicle_id == Vehicle.id)
        .order_by(Device.installed_at.desc())
    )

    # Apply search filter if provided
    if search:
        stmt = stmt.where(Device.imei.icontains(search))

    # Get total count for pagination
    count_stmt = select(func.count()).select_from(stmt.alias())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = compute_offset(page, items_per_page)
    stmt = stmt.offset(offset).limit(items_per_page)

    result = await db.execute(stmt)
    rows = result.all()

    # Transform to response schema
    devices_with_details = []
    for device, plate_number in rows:
        device_data = schemas.device_schemas.DeviceReadWithRealtime(
            **device.__dict__,
            plate_number=plate_number,
            realtime={}
        )
        devices_with_details.append(device_data)

    # Handle realtime data (optional)
    # This part can be re-enabled if needed

    # Return paginated response
    return paginated_response(crud_data={"data": devices_with_details, "total_count": total}, page=page, items_per_page=items_per_page)

@router.patch("/{device_id}", response_model=schemas.device_schemas.DeviceRead)
async def update_device(
    device_id: uuid.UUID,
    device_update: schemas.device_schemas.DeviceUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Update device (partial update)."""
    # Check if device exists
    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")

    # UUID fields are properly typed, no need for string conversion

    await crud_devices.update(db=db, object=device_update, id=device_id)

    # Return updated object
    updated_device = await crud_devices.get(
        db=db,
        id=device_id,
        schema_to_select=schemas.device_schemas.DeviceRead
    )
    return updated_device

@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Delete device."""
    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")

    await crud_devices.delete(db=db, id=device_id)

# Removed unassigned devices endpoint - no longer relevant without vehicle concept

# Device assignment endpoints removed - no longer relevant without vehicle concept


@router.get("/{device_id}/realtime", response_model=dict)
async def get_device_realtime_info(
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    mqtt_service: Annotated[MQTTPersistentService, Depends(get_mqtt_persistent_service)]
):

    # 1. Kiểm tra device có tồn tại trong database không
    device = await crud_devices.get(db=db, id=device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Thiết bị không tồn tại")

    # 2. Lấy IMEI từ device object
    device_imei = getattr(device, 'imei', device.get('imei') if isinstance(device, dict) else None)
    if not device_imei:
        raise HTTPException(status_code=500, detail="Không tìm thấy IMEI của thiết bị")

    # 3. Gọi MQTT để lấy thông tin real-time



# Device assignment endpoints

@router.put("/{device_id}/assign", response_model=schemas.device_schemas.DeviceRead)
async def assign_device_to_vehicle(
    device_id: uuid.UUID,
    assignment_data: schemas.device_schemas.DeviceAssignment,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Assign device to a vehicle."""
    from app.data_access.vehicle_repository import crud_vehicles

    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")

    if assignment_data.vehicle_id:
        if not await crud_vehicles.exists(db=db, id=assignment_data.vehicle_id):
            raise HTTPException(status_code=400, detail="Vehicle not found")

        existing_device = await crud_devices.get(db=db, vehicle_id=assignment_data.vehicle_id)
        if existing_device and existing_device["id"] != device_id:
            raise HTTPException(status_code=400, detail="Vehicle already has a device assigned")

    update_data = schemas.device_schemas.DeviceUpdate(vehicle_id=assignment_data.vehicle_id)
    await crud_devices.update(db=db, object=update_data, id=device_id)

    return await crud_devices.get(db=db, id=device_id, schema_to_select=schemas.device_schemas.DeviceRead)

@router.put("/{device_id}/unassign", response_model=schemas.device_schemas.DeviceRead)
async def unassign_device_from_vehicle(
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Unassign device from vehicle."""
    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")

    unassign_data = schemas.device_schemas.DeviceUpdate(vehicle_id=None)
    await crud_devices.update(db=db, object=unassign_data, id=device_id)

    return await crud_devices.get(db=db, id=device_id, schema_to_select=schemas.device_schemas.DeviceRead)

