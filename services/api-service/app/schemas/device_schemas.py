import uuid
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# --- Device Schemas - FastCRUD Pattern ---

class DeviceCreate(BaseModel):
    """Schema for creating a new Device."""
    imei: str = Field(..., max_length=50)
    serial_number: Optional[str] = Field(None, max_length=50)
    firmware_version: Optional[str] = Field(None, max_length=20)


class DeviceUpdate(BaseModel):
    """Schema for updating a Device."""
    imei: Optional[str] = None
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    vehicle_id: Optional[uuid.UUID] = None


class DeviceRead(BaseModel):
    """Schema for reading Device data."""
    id: uuid.UUID
    imei: str
    serial_number: Optional[str]
    firmware_version: Optional[str]

    installed_at: datetime
    vehicle_id: Optional[uuid.UUID] = None
    plate_number: Optional[str] = None

    class Config:
        from_attributes = True




# MQTT Response Schemas
class DeviceInfoSchema(BaseModel):
    sn: str
    device_name: str
    app_name: str
    manufacture: str
    hardware: str
    hardware_version: str
    product_id: str
    id_type: int
    vendor_id: str
    device_id: str
    extend_id: str
    software_version: str
    mcu_version: str
    cpu_type: int
    pcb_version: str
    mqtt_version: str
    with_mobile: int
    with_wifi: int


class SystemInfoSchema(BaseModel):
    cpu_speed: int
    cpu_usage: int
    memory_capacity: int
    memory_usage: int
    device_uptime: int
    system_uptime: int
    sleep_status: int
    temperature: int
    id_type: int
    time: str
    route_type: int
    route_name: str
    net_connect_status: int
    gateway: str
    dns0: str
    dns1: str
    language: int
    time_sync: int
    timezone: str


class UserInfoSchema(BaseModel):
    serialNo: str
    userId: str
    userName: str
    unitNo: str
    unitName: str
    collected: int


class BatteryInfoSchema(BaseModel):
    full_value: int
    alarm_value: int
    power_off_value: int
    bat_value: int
    bat_percent: int
    bat_status: int
    bat_health: int
    bat_current: int
    bat_mah: int


class GPSInfoSchema(BaseModel):
    enable: int
    power_save: int
    hardware_status: int
    valid: int
    longitude: float
    longitude_degree: int
    longitude_cent: int
    latitude: float
    latitude_degree: int
    latitude_cent: int
    speed: float
    direction: float
    height_ground: int
    height_sea: float
    time_year: int
    time_month: int
    time_day: int
    time_hour: int
    time_minute: int
    time_second: int
    mode: int
    satellite_used: List[int]
    satellite_visible: List[int]
    satellite_number: List[int]
    satellite_signal: List[int]
    server_enable: int
    report_time: int
    server_port: int
    server_ip: str
    device_no: str
    pass_field: str = Field(alias="pass")
    ns: str
    ew: str
    longitude_str: str
    latitude_str: str


class DeviceRealtimeDataSchema(BaseModel):
    DEVICE_INFO: DeviceInfoSchema
    SYSTEM_INFO: SystemInfoSchema
    USER_INFO: UserInfoSchema
    BATTERY_INFO: BatteryInfoSchema
    GPS_INFO: GPSInfoSchema


class DeviceRealtimeResponse(BaseModel):
    typeCode: str
    typeNo: str
    version: str
    dataEncryptionMode: str
    timestamp: int  # Fixed từ "timestap" typo trong MQTT response
    data: DeviceRealtimeDataSchema

    class Config:
        # Allow extra fields và populate by name
        extra = "allow"
        populate_by_name = True


class DeviceReadWithRealtime(DeviceRead):
    """Schema for reading Device data with realtime info."""
    realtime: dict = Field({}, description="Realtime data from the device")


class DeviceAssignment(BaseModel):
    """Schema for assigning a device to a vehicle."""
    vehicle_id: Optional[uuid.UUID] = None
