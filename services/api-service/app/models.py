import uuid
from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Integer,
    String,
    DateTime,
    Text,
    Enum as SAEnum,
    Date,
    Numeric,
    BigInteger,
    Table
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    role = Column(String(50), nullable=False, default="admin")
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plate_number = Column(String(20), unique=True, nullable=False, index=True)
    type = Column(String(50))
    load_capacity_kg = Column(Integer)
    registration_expiry = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    device = relationship("Device", back_populates="vehicle", uselist=False, cascade="all, delete-orphan")
    journey_sessions = relationship("JourneySession", back_populates="vehicle")
    images = relationship("Image", back_populates="vehicle")
    alerts = relationship("Alert", back_populates="vehicle")

class Device(Base):
    __tablename__ = "devices"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), unique=True)
    imei = Column(String(50), unique=True, nullable=False, index=True)
    serial_number = Column(String(50), unique=True)
    firmware_version = Column(String(20))
    installed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    vehicle = relationship("Vehicle", back_populates="device")

class Driver(Base):
    __tablename__ = "drivers"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    card_id = Column(String(50), unique=True, index=True)
    phone_number = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    journey_sessions = relationship("JourneySession", back_populates="driver")

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

    vehicle = relationship("Vehicle", back_populates="journey_sessions")
    driver = relationship("Driver", back_populates="journey_sessions")
    device_logs = relationship("DeviceLog", back_populates="journey_session")

class ImageTypeEnum(str, enum.Enum):
    image = "image"
    video = "video"

class Image(Base):
    __tablename__ = "images"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    storage_path = Column(String(512), nullable=False)
    type = Column(SAEnum(ImageTypeEnum), nullable=False)
    event_type = Column(String(50))
    
    vehicle = relationship("Vehicle", back_populates="images")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(BigInteger, primary_key=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    alert_type = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    details = Column(JSONB)
    is_acknowledged = Column(Boolean, default=False, nullable=False)

    vehicle = relationship("Vehicle", back_populates="alerts")

class DeviceLog(Base):
    __tablename__ = "device_logs"
    id = Column(BigInteger, primary_key=True)
    journey_session_id = Column(BigInteger, ForeignKey("journey_sessions.id"), nullable=False)
    device_imei = Column(String(50), nullable=False)
    mqtt_response = Column(JSONB, nullable=False)
    collected_at = Column(DateTime(timezone=True), server_default=func.now())

    journey_session = relationship("JourneySession", back_populates="device_logs")

