# Import shared models từ api-service
import sys
from pathlib import Path

# Add api-service to path
api_service_path = Path(__file__).resolve().parent.parent.parent.parent / "api-service"
if str(api_service_path) not in sys.path:
    sys.path.insert(0, str(api_service_path))

# Direct import to avoid circular import
sys.path.insert(0, str(api_service_path))

# Import directly from api-service models module
from sqlalchemy import Column, String, Boolean, DateTime, BigInteger, Text, Numeric, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

# Create base
Base = declarative_base()

# Define models locally (copy from api-service to avoid import issues)
class JourneySession(Base):
    __tablename__ = "journey_sessions"
    id = Column(BigInteger, primary_key=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    total_distance_km = Column(Numeric(10, 2), default=0.0)
    notes = Column(Text)
    status = Column(String(20), server_default='pending', nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

class DeviceLog(Base):
    __tablename__ = "device_logs"
    id = Column(BigInteger, primary_key=True)
    journey_session_id = Column(BigInteger, ForeignKey("journey_sessions.id"), nullable=False)
    device_imei = Column(String(50), nullable=False)
    mqtt_response = Column(JSONB, nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), unique=True)
    imei = Column(String(50), unique=True, nullable=False, index=True)
    serial_number = Column(String(50), unique=True)
    firmware_version = Column(String(20))
    installed_at = Column(DateTime(timezone=True), server_default=func.now())

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(20), unique=True, index=True, nullable=False)
    type = Column(String(50))
    load_capacity_kg = Column(Integer)
    registration_expiry = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

__all__ = [
    "Base",
    "JourneySession",
    "DeviceLog",
    "Device",
    "Vehicle"
]
