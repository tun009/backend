import uuid
import logging
from typing import Annotated, Optional
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, update, func

from app import schemas
from app.api import dependencies
from app.db.session import get_async_db
from app.data_access import crud_journey_sessions, crud_vehicles, crud_drivers, crud_devices, crud_device_logs
from app.models import JourneySession, Vehicle, Driver, Device, DeviceLog

from app.core.redis_client import redis_client
from app.services.media_server_service import media_server_service
router = APIRouter()
logger = logging.getLogger(__name__)

# Múi giờ Việt Nam (UTC+7)
vietnam_tz = ZoneInfo("Asia/Ho_Chi_Minh")

@router.post("/", response_model=schemas.journey_session_schemas.JourneySessionRead, status_code=status.HTTP_201_CREATED)
async def create_journey_session(
    journey_in: schemas.journey_session_schemas.JourneySessionCreate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Tạo ca làm việc mới."""

    # 1. Kiểm tra vehicle tồn tại
    if not await crud_vehicles.exists(db=db, id=journey_in.vehicle_id):
        raise HTTPException(status_code=404, detail="Xe không tồn tại")

    # 2. Kiểm tra driver tồn tại
    if not await crud_drivers.exists(db=db, id=journey_in.driver_id):
        raise HTTPException(status_code=404, detail="Tài xế không tồn tại")

    # 3. Kiểm tra xe đã có ca làm việc active chưa
    existing_active = await db.execute(
        select(JourneySession).where(
            and_(
                JourneySession.vehicle_id == journey_in.vehicle_id,
                JourneySession.status == 'active',
                JourneySession.end_time.is_(None)
            )
        )
    )
    if existing_active.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Xe này đã có ca làm việc đang hoạt động. Vui lòng kết thúc ca hiện tại trước."
        )

    # 4. Kiểm tra tài xế đã có ca làm việc active chưa
    existing_driver_active = await db.execute(
        select(JourneySession).where(
            and_(
                JourneySession.driver_id == journey_in.driver_id,
                JourneySession.status == 'active'
            )
        )
    )
    if existing_driver_active.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Tài xế này đã có ca làm việc đang hoạt động. Vui lòng kết thúc ca hiện tại trước."
        )

    # 5. Kiểm tra trùng lịch cho xe (overlap checking)
    existing_vehicle_overlap = await db.execute(
        select(JourneySession).where(
            and_(
                JourneySession.vehicle_id == journey_in.vehicle_id,
                JourneySession.status.in_(['pending', 'active']),
                # Check overlap: new_start < existing_end AND new_end > existing_start
                and_(
                    journey_in.start_time < JourneySession.end_time,
                    journey_in.end_time > JourneySession.start_time
                )
            )
        )
    )
    if existing_vehicle_overlap.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Xe này đã có ca làm việc trong khoảng thời gian trùng lặp. Vui lòng chọn thời gian khác."
        )

    # 6. Kiểm tra trùng lịch cho tài xế (overlap checking)
    existing_driver_overlap = await db.execute(
        select(JourneySession).where(
            and_(
                JourneySession.driver_id == journey_in.driver_id,
                JourneySession.status.in_(['pending', 'active']),
                # Check overlap: new_start < existing_end AND new_end > existing_start
                and_(
                    journey_in.start_time < JourneySession.end_time,
                    journey_in.end_time > JourneySession.start_time
                )
            )
        )
    )
    if existing_driver_overlap.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Tài xế này đã có ca làm việc trong khoảng thời gian trùng lặp. Vui lòng chọn thời gian khác."
        )

    # 7. Tạo journey session với status='pending'
    return await crud_journey_sessions.create(db=db, object=journey_in)

@router.get("/", response_model=PaginatedListResponse[schemas.journey_session_schemas.JourneySessionWithDetails])
async def get_journey_sessions(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    page: int = 1,
    items_per_page: int = 10,
    status_filter: Optional[str] = None
):
    """Lấy danh sách ca làm việc với pagination và thông tin chi tiết."""

    # Build query với joins để lấy thông tin chi tiết
    stmt = (
        select(
            JourneySession,
            Vehicle.plate_number,
            Driver.full_name,
            Device.imei
        )
        .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
        .join(Driver, JourneySession.driver_id == Driver.id)
        .outerjoin(Device, Vehicle.id == Device.vehicle_id)
        .order_by(JourneySession.start_time.desc())
    )

    # Apply status filter if provided
    if status_filter:
        stmt = stmt.where(JourneySession.status == status_filter)

    # Apply pagination
    offset = compute_offset(page, items_per_page)
    stmt = stmt.offset(offset).limit(items_per_page)

    result = await db.execute(stmt)
    rows = result.all()

    # Transform to response schema
    journey_sessions = []
    for row in rows:
        journey, plate_number, driver_name, device_imei = row
        session_data = schemas.journey_session_schemas.JourneySessionWithDetails(
            id=journey.id,
            vehicle_id=journey.vehicle_id,
            driver_id=journey.driver_id,
            start_time=journey.start_time,
            end_time=journey.end_time,
            total_distance_km=journey.total_distance_km,
            notes=journey.notes,
            status=journey.status,
            activated_at=journey.activated_at,
            vehicle_plate_number=plate_number,
            driver_name=driver_name,
            device_imei=device_imei
        )
        journey_sessions.append(session_data)

    # Get total count for pagination
    count_stmt = select(func.count(JourneySession.id))
    if status_filter:
        count_stmt = count_stmt.where(JourneySession.status == status_filter)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # Tạo fake crud_data format để dùng với paginated_response()
    fake_crud_data = {
        "data": journey_sessions,
        "total_count": total or 0
    }

    return paginated_response(crud_data=fake_crud_data, page=page, items_per_page=items_per_page)

@router.get("/active", response_model=list[schemas.journey_session_schemas.JourneySessionWithDetails])
async def get_active_journey_sessions(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Lấy danh sách ca làm việc đang active - cho Processing Service."""

    # Query với join để lấy thông tin chi tiết
    stmt = (
        select(
            JourneySession,
            Vehicle.plate_number,
            Driver.full_name,
            Device.imei
        )
        .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
        .join(Driver, JourneySession.driver_id == Driver.id)
        .outerjoin(Device, Vehicle.id == Device.vehicle_id)
        .where(JourneySession.status == 'active')
        .order_by(JourneySession.activated_at.desc())
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Transform to response schema
    active_sessions = []
    for row in rows:
        journey, plate_number, driver_name, device_imei = row
        session_data = schemas.journey_session_schemas.JourneySessionWithDetails(
            id=journey.id,
            vehicle_id=journey.vehicle_id,
            driver_id=journey.driver_id,
            start_time=journey.start_time,
            end_time=journey.end_time,
            total_distance_km=journey.total_distance_km,
            notes=journey.notes,
            status=journey.status,
            activated_at=journey.activated_at,
            vehicle_plate_number=plate_number,
            driver_name=driver_name,
            device_imei=device_imei
        )
        active_sessions.append(session_data)

    return active_sessions

@router.get("/active/realtime", response_model=PaginatedListResponse[schemas.journey_session_schemas.JourneySessionRealtime])
async def get_active_journey_sessions_with_realtime(
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
    page: int = 1,
    items_per_page: int = 10
):

    # 1. Query active journey sessions với thông tin liên quan
    now = datetime.now(vietnam_tz)

    stmt = (
        select(
            JourneySession,
            Vehicle.plate_number,
            Driver.full_name,
            Device.imei
        )
        .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
        .join(Driver, JourneySession.driver_id == Driver.id)
        .outerjoin(Device, Vehicle.id == Device.vehicle_id)
        .where(
            and_(
                JourneySession.status == 'active',
                JourneySession.start_time <= now,
                JourneySession.end_time >= now
            )
        )
        .order_by(JourneySession.activated_at.desc())
    )

    # Apply pagination
    offset = compute_offset(page, items_per_page)
    stmt = stmt.offset(offset).limit(items_per_page)

    result = await db.execute(stmt)
    rows = result.all()

    # 2. Get total count for pagination
    count_stmt = (
        select(func.count(JourneySession.id))
        .where(
            and_(
                JourneySession.status == 'active',
                JourneySession.start_time <= now,
                JourneySession.end_time >= now
            )
        )
    )
    total_result = await db.execute(count_stmt)
    total = total_result.scalar()

    # 3. Transform to response schema and get latest GPS data
    sessions_with_realtime = []

    for row in rows:
        journey, plate_number, driver_name, device_imei = row

        # Initialize session data
        session_data = schemas.journey_session_schemas.JourneySessionRealtime(
            id=journey.id,
            vehicle_id=journey.vehicle_id,
            driver_id=journey.driver_id,
            start_time=journey.start_time,
            end_time=journey.end_time,
            status=journey.status,
            activated_at=journey.activated_at,
            plate_number=plate_number,
            driver_name=driver_name,
            imei=device_imei,
            realtime={}
        )

        # 4. Get latest GPS data from device_logs if device exists
        if device_imei:
            latest_log_stmt = (
                select(
                    DeviceLog.mqtt_response,
                    DeviceLog.collected_at
                )
                .where(DeviceLog.journey_session_id == journey.id)
                .order_by(DeviceLog.collected_at.desc())
                .limit(1)
            )

            log_result = await db.execute(latest_log_stmt)
            log_row = log_result.first()

            if log_row:
                mqtt_response, collected_at = log_row

                time_diff = now - collected_at
                if time_diff.total_seconds() > 60 * 5:
                    session_data.realtime = {}
                elif mqtt_response:
                    session_data.realtime = mqtt_response

        # 5. Get latest thumbnail from cache, with fallback to media server
        thumbnail_url = None
        if device_imei:
            cache_key = f"latest_thumbnail:{device_imei}"
            try:
                cached_url = await redis_client.get(cache_key)
                if cached_url and isinstance(cached_url, str):
                    thumbnail_url = cached_url
                else:
                    # Fallback: If not in cache, fetch from media server
                    logger.info(f"Cache miss for {cache_key}, fetching from media server...")
                    latest_video = await media_server_service.get_latest_video_info(device_imei)
                    if latest_video and latest_video.get('thumbnail_url'):
                        thumbnail_url_path = latest_video['thumbnail_url']
                        # Construct the full URL before caching and returning
                        full_thumbnail_url = f"{media_server_service.base_url}{thumbnail_url_path}"
                        thumbnail_url = full_thumbnail_url
                        # Cache the newly found thumbnail
                        await redis_client.set(cache_key, full_thumbnail_url, ttl=30 * 60) # Cache for 30m
            except Exception as e:
                logger.error(f"Failed to get/fetch thumbnail for device {device_imei}: {e}")
        session_data.thumbnail_url = thumbnail_url

        sessions_with_realtime.append(session_data)

    # 5. Return paginated response
    fake_crud_data = {
        "data": sessions_with_realtime,
        "total_count": total or 0
    }

    return paginated_response(crud_data=fake_crud_data, page=page, items_per_page=items_per_page)

@router.get("/{session_id}/history", response_model=schemas.journey_session_schemas.JourneySessionHistoryResponse)
async def get_journey_session_history(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Lấy lịch sử hành trình của ca làm việc theo session_id."""

    journey_stmt = (
        select(
            JourneySession.id,
            Vehicle.plate_number,
            Driver.full_name,
            Device.imei
        )
        .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
        .join(Driver, JourneySession.driver_id == Driver.id)
        .outerjoin(Device, Vehicle.id == Device.vehicle_id)
        .where(JourneySession.id == session_id)
    )

    journey_result = await db.execute(journey_stmt)
    journey_row = journey_result.first()

    if not journey_row:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    journey_id, plate_number, driver_name, device_imei = journey_row

    logs_stmt = (
        select(
            DeviceLog.id,
            DeviceLog.collected_at,
            DeviceLog.mqtt_response
        )
        .where(DeviceLog.journey_session_id == session_id)
        .order_by(DeviceLog.collected_at.asc())  # Sắp xếp theo thời gian tăng dần
    )

    logs_result = await db.execute(logs_stmt)
    log_rows = logs_result.all()

    history_points = []

    for row in log_rows:
        log_id, collected_at, mqtt_response = row

        history_point = schemas.journey_session_schemas.JourneyHistoryPoint(
            id=log_id,
            collected_at=collected_at
        )

        if mqtt_response and isinstance(mqtt_response, dict):
            gps_info = mqtt_response.get('GPS_INFO', {})
            if gps_info:
                history_point.latitude = gps_info.get('latitude')
                history_point.latitude_degree = gps_info.get('latitude_degree')
                history_point.longitude = gps_info.get('longitude')
                history_point.longitude_degree = gps_info.get('longitude_degree')
                history_point.gps_speed = gps_info.get('speed')
                history_point.gps_valid = gps_info.get('valid')
                history_point.gps_enable = gps_info.get('enable')

            battery_info = mqtt_response.get('BATTERY_INFO', {})
            if battery_info:
                history_point.bat_percent = battery_info.get('bat_percent')

        history_points.append(history_point)

    start_time = None
    end_time = None

    if history_points:
        start_time = history_points[0].collected_at
        end_time = history_points[-1].collected_at

    response = schemas.journey_session_schemas.JourneySessionHistoryResponse(
        data=history_points,
        plate_number=plate_number,
        driver_name=driver_name,
        imei=device_imei,
        id=journey_id,
        start_time=start_time,
        end_time=end_time
    )

    return response

@router.get("/{session_id}", response_model=schemas.journey_session_schemas.JourneySessionWithDetails)
async def get_journey_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Lấy chi tiết ca làm việc."""

    # Query với join để lấy thông tin chi tiết
    stmt = (
        select(
            JourneySession,
            Vehicle.plate_number,
            Driver.full_name,
            Device.imei
        )
        .join(Vehicle, JourneySession.vehicle_id == Vehicle.id)
        .join(Driver, JourneySession.driver_id == Driver.id)
        .outerjoin(Device, Vehicle.id == Device.vehicle_id)
        .where(JourneySession.id == session_id)
    )

    result = await db.execute(stmt)
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    journey, plate_number, driver_name, device_imei = row

    return schemas.journey_session_schemas.JourneySessionWithDetails(
        id=journey.id,
        vehicle_id=journey.vehicle_id,
        driver_id=journey.driver_id,
        start_time=journey.start_time,
        end_time=journey.end_time,
        total_distance_km=journey.total_distance_km,
        notes=journey.notes,
        status=journey.status,
        activated_at=journey.activated_at,
        vehicle_plate_number=plate_number,
        driver_name=driver_name,
        device_imei=device_imei
    )

@router.post("/{session_id}/start", response_model=schemas.journey_session_schemas.JourneySessionRead)
async def start_journey_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Bắt đầu ca làm việc - chuyển status thành 'active'."""

    # 1. Lấy journey session để kiểm tra status
    journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )
    if not journey:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    # 2. Kiểm tra status hiện tại - handle both dict and Pydantic model
    current_status = getattr(journey, 'status', journey.get('status') if isinstance(journey, dict) else None)
    if current_status != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Không thể bắt đầu ca làm việc. Trạng thái hiện tại: {current_status}"
        )

    # 3. Cập nhật status và activated_at bằng SQL update
    await db.execute(
        update(JourneySession)
        .where(JourneySession.id == session_id)
        .values(
            status='active',
            activated_at=datetime.now(vietnam_tz)
        )
    )
    await db.commit()

    # 4. Lấy lại data đã update
    updated_journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )


    return updated_journey

@router.post("/{session_id}/end", response_model=schemas.journey_session_schemas.JourneySessionRead)
async def end_journey_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Kết thúc ca làm việc - chuyển status thành 'completed'."""

    # 1. Lấy journey session để kiểm tra status
    journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )
    if not journey:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    # 2. Kiểm tra status hiện tại - handle both dict and Pydantic model
    current_status = getattr(journey, 'status', journey.get('status') if isinstance(journey, dict) else None)
    if current_status != 'active':
        raise HTTPException(
            status_code=400,
            detail=f"Không thể kết thúc ca làm việc. Trạng thái hiện tại: {current_status}"
        )

    # 3. Cập nhật status và end_time bằng SQL update
    await db.execute(
        update(JourneySession)
        .where(JourneySession.id == session_id)
        .values(
            status='completed',
            end_time=datetime.now(vietnam_tz)
        )
    )
    await db.commit()

    # 4. Lấy lại data đã update
    updated_journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )


    return updated_journey

@router.get("/{session_id}/status")
async def get_journey_session_status(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Kiểm tra trạng thái ca làm việc."""

    journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )
    if not journey:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    # Handle both dict and Pydantic model
    return {
        "session_id": session_id,
        "status": getattr(journey, 'status', journey.get('status') if isinstance(journey, dict) else None),
        "activated_at": getattr(journey, 'activated_at', journey.get('activated_at') if isinstance(journey, dict) else None),
        "start_time": getattr(journey, 'start_time', journey.get('start_time') if isinstance(journey, dict) else None),
        "end_time": getattr(journey, 'end_time', journey.get('end_time') if isinstance(journey, dict) else None)
    }

@router.put("/{session_id}", response_model=schemas.journey_session_schemas.JourneySessionRead)
async def update_journey_session(
    session_id: int,
    journey_update: schemas.journey_session_schemas.JourneySessionUpdate,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Cập nhật thông tin ca làm việc."""

    # Kiểm tra journey session tồn tại
    if not await crud_journey_sessions.exists(db=db, id=session_id):
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    # Cập nhật
    await crud_journey_sessions.update(db=db, object=journey_update, id=session_id)

    # Return updated object
    updated_journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )
    return updated_journey

@router.delete("/{session_id}")
async def delete_journey_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)]
):
    """Xóa ca làm việc."""

    # Kiểm tra journey session tồn tại
    journey = await crud_journey_sessions.get(
        db=db,
        id=session_id,
        schema_to_select=schemas.journey_session_schemas.JourneySessionRead
    )
    if not journey:
        raise HTTPException(status_code=404, detail="Ca làm việc không tồn tại")

    # Không cho phép xóa ca đang active - handle both dict and Pydantic model
    current_status = getattr(journey, 'status', journey.get('status') if isinstance(journey, dict) else None)
    if current_status == 'active':
        raise HTTPException(
            status_code=400,
            detail="Không thể xóa ca làm việc đang hoạt động. Vui lòng kết thúc ca trước."
        )

    # Xóa device_logs trước (để tránh foreign key constraint)
    await db.execute(
        DeviceLog.__table__.delete().where(DeviceLog.journey_session_id == session_id)
    )
    await crud_journey_sessions.delete(db=db, id=session_id)

    return {"message": "Ca làm việc và dữ liệu liên quan đã được xóa thành công"}



@router.get(
    "/{session_id}/media",
    tags=["Journey Sessions"],
    summary="Get a JSON playlist for a journey session (frontend player logic)"
)
async def get_journey_playlist(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_async_db)],
    _current_user: Annotated[dict, Depends(dependencies.get_current_active_user)],
):
    """
    Returns a JSON-based playlist for a journey, intended for a client-side player.
    The player is responsible for handling playback, seeking, and transitions.
    """
    # 1. Get device IMEI from journey_id
    journey_stmt = select(Device.imei).select_from(JourneySession).join(Vehicle, JourneySession.vehicle_id == Vehicle.id).join(Device, Vehicle.id == Device.vehicle_id).where(JourneySession.id == session_id)
    device_imei_result = await db.execute(journey_stmt)
    device_no = device_imei_result.scalar_one_or_none()
    if not device_no:
        raise HTTPException(status_code=404, detail="Device not found for the given journey.")

    # 2. Get time range from journey_id
    time_stmt = select(func.min(DeviceLog.collected_at).label("start_time"), func.max(DeviceLog.collected_at).label("end_time")).where(DeviceLog.journey_session_id == session_id)
    time_result = await db.execute(time_stmt)
    time_row = time_result.first()
    if not time_row or not time_row.start_time:
        raise HTTPException(status_code=404, detail="No device logs found for this journey to determine time range.")

    vietnam_tz = timezone(timedelta(hours=7))
    start_time_utc = time_row.start_time.replace(tzinfo=timezone.utc)
    end_time_utc = time_row.end_time.replace(tzinfo=timezone.utc)
    start_time_vn = start_time_utc.astimezone(vietnam_tz)
    end_time_vn = end_time_utc.astimezone(vietnam_tz)
    start_time_iso = start_time_vn.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    end_time_iso = end_time_vn.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    # 3. Get video files list from Media Server
    try:
        video_files = await media_server_service.get_video_files(device_no, start_time_iso, end_time_iso)
        if not video_files:
            return [] # Return empty list if no videos
        # Sort videos by timestamp to ensure correct order
        video_files.sort(key=lambda x: x['taken_at'])
    except HTTPException as e:
        # Re-raise the exception from the service if it's an HTTP error
        raise e
    except Exception as e:
        # Handle other potential errors like network issues or parsing errors
        raise HTTPException(status_code=500, detail=f"An error occurred while fetching video files: {str(e)}")

    # 4. Build the final playlist for the frontend, including all fields from media server
    playlist = []
    for file_info in video_files:
        # Create a copy to avoid modifying the original list if it's used elsewhere
        item = file_info.copy()
        # Construct the full URL for the video file and update the item
        item['file_url'] = f"{media_server_service.base_url}{item['file_url']}"
        playlist.append(item)

    # 5. Cache the latest thumbnail URL to Redis
    if playlist:
        # The playlist is already sorted by taken_at
        latest_video = playlist[-1]
        thumbnail_url = latest_video.get('thumbnail_url')
        if thumbnail_url:
            # Construct the full URL before caching
            full_thumbnail_url = f"{media_server_service.base_url}{thumbnail_url}"
            cache_key = f"latest_thumbnail:{device_no}"
            try:
                await redis_client.set(cache_key, full_thumbnail_url, ttl=60 * 60 * 24 * 7) # Cache for 7 days
                logger.info(f"Cached latest thumbnail for device {device_no}")
            except Exception as e:
                logger.error(f"Failed to cache thumbnail for device {device_no}: {e}")


    return playlist



