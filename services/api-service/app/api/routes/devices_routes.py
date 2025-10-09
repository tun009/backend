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
    """Get devices with pagination and search."""

    # Build query for devices only (vehicle info now in device table)
    stmt = (
        select(Device)
        .order_by(Device.installed_at.desc())
    )

    # Apply search filter if provided
    if search:
        stmt = stmt.where(Device.imei.icontains(search))

    # Apply pagination
    offset = compute_offset(page, items_per_page)
    stmt = stmt.offset(offset).limit(items_per_page)

    result = await db.execute(stmt)
    rows = result.scalars().all()

    # Transform to response schema
    devices_with_details = []
    for device in rows:
        # Convert SQLAlchemy model to Pydantic schema
        device_dict = {
            "id": device.id,
            "imei": device.imei,
            "serial_number": device.serial_number,
            "firmware_version": device.firmware_version,
            "installed_at": device.installed_at,
            
            "realtime": {}
        }
        device_data = schemas.device_schemas.DeviceReadWithRealtime.model_validate(device_dict)
        devices_with_details.append(device_data)

    # Get total count for pagination
    count_stmt = select(func.count(Device.id))
    if search:
        count_stmt = count_stmt.where(Device.imei.icontains(search))

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # # Handle realtime data if needed
    # if include_realtime and devices_with_details:
    #     device_imeis = [device.imei for device in devices_with_details]

    #     try:
    #         realtime_data = await mqtt_service.get_multiple_devices_realtime_info(device_imeis, max_concurrent=3)
    #     except Exception as e:
    #         logger.warning(f"Failed to fetch realtime data: {e}")
    #         realtime_data = {}

    #     # Add realtime data to devices
    #     for device in devices_with_details:
    #         realtime_response = realtime_data.get(device.imei)
    #         if realtime_response and hasattr(realtime_response, 'data'):
    #             device.realtime = realtime_response.data.model_dump()

    # Return paginated response
    fake_crud_data = {
        "data": devices_with_details,
        "total_count": total or 0
    }

    return paginated_response(crud_data=fake_crud_data, page=page, items_per_page=items_per_page)

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
    try:
        realtime_response = await mqtt_service.get_device_realtime_info(device_imei)

        if not realtime_response:
            raise HTTPException(
                status_code=408,
                detail="Thiết bị không phản hồi. Vui lòng kiểm tra kết nối thiết bị."
            )

        # Chỉ trả về data object, bỏ metadata
        return realtime_response.data.model_dump()

    except DeviceTimeoutError as e:
        raise HTTPException(
            status_code=408,
            detail=f"Thiết bị không phản hồi: {str(e)}"
        )
    except MQTTConnectionError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Lỗi kết nối MQTT: {str(e)}"
        )
    except InvalidResponseError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Dữ liệu từ thiết bị không hợp lệ: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi không xác định: {str(e)}"
        )