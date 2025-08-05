import uuid
import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_devices
from app.services.mqtt_service import (
    get_mqtt_realtime_service,
    MQTTRealtimeService,
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
        raise HTTPException(status_code=400, detail="IMEI already exists")
    
    # Check duplicate serial_number if provided
    if device_in.serial_number and await crud_devices.exists(db=db, serial_number=device_in.serial_number):
        raise HTTPException(status_code=400, detail="Serial number already exists")
    
    # Convert empty string vehicle_id to None
    if device_in.vehicle_id == "":
        device_in.vehicle_id = None
    
    # If vehicle_id provided, check if vehicle exists and is not already assigned
    if device_in.vehicle_id:
        from app.data_access import crud_vehicles
        if not await crud_vehicles.exists(db=db, id=device_in.vehicle_id):
            raise HTTPException(status_code=400, detail="Vehicle not found")
        
        # Check if vehicle already has a device (1-1 relationship)
        if await crud_devices.exists(db=db, vehicle_id=device_in.vehicle_id):
            raise HTTPException(status_code=400, detail="Vehicle already has a device assigned")
    
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
    mqtt_service: Annotated[MQTTRealtimeService, Depends(get_mqtt_realtime_service)],
    page: int = 1,
    items_per_page: int = 10,
    search: Optional[str] = None,
    include_realtime: bool = True
):
    """Get devices with pagination, search and optional realtime data."""
    filters = {}
    if search:
        # FastCRUD supports icontains filtering for IMEI or serial number
        filters["imei__icontains"] = search

    devices_data = await crud_devices.get_multi(
        db=db,
        offset=compute_offset(page, items_per_page),
        limit=items_per_page,
        schema_to_select=schemas.device_schemas.DeviceRead,
        **filters
    )

    # Nếu không cần realtime data, trả về như cũ
    if not include_realtime or not devices_data["data"]:
        # Convert to DeviceReadWithRealtime format (realtime = {})
        devices_with_realtime = []
        for device in devices_data["data"]:
            device_dict = device if isinstance(device, dict) else device.__dict__
            device_with_realtime = schemas.device_schemas.DeviceReadWithRealtime(
                **device_dict,
                realtime={}
            )
            devices_with_realtime.append(device_with_realtime)

        devices_data["data"] = devices_with_realtime
        return paginated_response(crud_data=devices_data, page=page, items_per_page=items_per_page)

    # Lấy danh sách IMEI từ devices
    device_imeis = []
    for device in devices_data["data"]:
        imei = device.get("imei") if isinstance(device, dict) else getattr(device, "imei", None)
        if imei:
            device_imeis.append(imei)

    # Fetch realtime data cho tất cả devices đồng thời
    realtime_data = {}
    if device_imeis:
        try:
            realtime_data = await mqtt_service.get_multiple_devices_realtime_info(device_imeis, max_concurrent=3)
        except Exception as e:
            logger.warning(f"Failed to fetch realtime data: {e}")

    # Combine device data với realtime data
    devices_with_realtime = []
    for device in devices_data["data"]:
        device_dict = device if isinstance(device, dict) else device.__dict__
        imei = device_dict.get("imei")

        # Lấy chỉ data object từ realtime response, bỏ metadata
        realtime_response = realtime_data.get(imei) if imei else None
        realtime_data_only = {}

        if realtime_response and hasattr(realtime_response, 'data'):
            # Convert DeviceRealtimeDataSchema to dict
            realtime_data_only = realtime_response.data.dict()

        device_with_realtime = schemas.device_schemas.DeviceReadWithRealtime(
            **device_dict,
            realtime=realtime_data_only
        )
        devices_with_realtime.append(device_with_realtime)

    devices_data["data"] = devices_with_realtime
    return paginated_response(crud_data=devices_data, page=page, items_per_page=items_per_page)

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

    # Convert empty string vehicle_id to None
    if device_update.vehicle_id == "":
        device_update.vehicle_id = None

    await crud_devices.update(db=db, object=device_update, id=device_id)
    
    return {"message": "device updated"}

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

@router.get("/unassigned", response_model=list[schemas.device_schemas.DeviceRead])
async def get_unassigned_devices(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Get all devices that are not assigned to any vehicle."""
    from sqlalchemy import select
    from app.models import Device
    
    # Query devices that don't have vehicle_id
    stmt = (
        select(Device)
        .where(Device.vehicle_id.is_(None))
        .order_by(Device.installed_at.desc())
    )
    
    result = await db.execute(stmt)
    devices = result.scalars().all()
    
    # Convert to schema and return
    return [schemas.device_schemas.DeviceRead.model_validate(device) for device in devices]

# Device assignment endpoints

@router.put("/{device_id}/assign", response_model=schemas.device_schemas.DeviceRead)
async def assign_device_to_vehicle(
    device_id: uuid.UUID,
    assignment_data: schemas.device_schemas.DeviceAssignment,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Assign device to a vehicle."""
    # Check if device exists
    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Convert empty string vehicle_id to None
    if assignment_data.vehicle_id == "":
        assignment_data.vehicle_id = None
    
    # Check if vehicle exists (only if vehicle_id is not None)
    if assignment_data.vehicle_id:
        from app.data_access import crud_vehicles
        if not await crud_vehicles.exists(db=db, id=assignment_data.vehicle_id):
            raise HTTPException(status_code=400, detail="Vehicle not found")
        
        # Check if vehicle already has a device (1-1 relationship)
        if await crud_devices.exists(db=db, vehicle_id=assignment_data.vehicle_id):
            raise HTTPException(status_code=400, detail="Vehicle already has a device assigned")
    
    # Update device with vehicle_id
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
    # Check if device exists
    if not await crud_devices.exists(db=db, id=device_id):
        raise HTTPException(status_code=404, detail="Device not found")
    
    # Update device to remove vehicle_id
    unassign_data = schemas.device_schemas.DeviceUpdate(vehicle_id=None)
    await crud_devices.update(db=db, object=unassign_data, id=device_id)
    
    return await crud_devices.get(db=db, id=device_id, schema_to_select=schemas.device_schemas.DeviceRead)


@router.get("/{device_id}/realtime", response_model=dict)
async def get_device_realtime_info(
    device_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    mqtt_service: Annotated[MQTTRealtimeService, Depends(get_mqtt_realtime_service)]
):
    """Lấy thông tin real-time của thiết bị qua MQTT (chỉ trả về data object)."""

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
        return realtime_response.data.dict()

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