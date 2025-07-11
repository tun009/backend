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

# The user_roles association table is removed.

class Organization(Base):
    __tablename__ = "organizations"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    address = Column(Text)
    tax_code = Column(String(20), unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    users = relationship("User", back_populates="organization")
    vehicles = relationship("Vehicle", back_populates="organization")
    drivers = relationship("Driver", back_populates="organization")

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    # Add a foreign key to the roles table
    role_id = Column(UUID(as_uuid=True), ForeignKey("roles.id"))
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="users")
    # Update relationship to one-to-many
    role = relationship("Role", back_populates="users")

class Role(Base):
    __tablename__ = 'roles'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    
    # Update relationship to one-to-many
    users = relationship("User", back_populates="role")

class Vehicle(Base):
    __tablename__ = "vehicles"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    plate_number = Column(String(20), unique=True, nullable=False, index=True)
    type = Column(String(50))
    load_capacity_kg = Column(Integer)
    registration_expiry = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="vehicles")
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
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    full_name = Column(String(100), nullable=False)
    license_number = Column(String(50), unique=True, nullable=False, index=True)
    card_id = Column(String(50), unique=True, index=True)
    phone_number = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    organization = relationship("Organization", back_populates="drivers")
    journey_sessions = relationship("JourneySession", back_populates="driver")

class JourneySession(Base):
    __tablename__ = "journey_sessions"
    id = Column(BigInteger, primary_key=True)
    vehicle_id = Column(UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False)
    driver_id = Column(UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    total_distance_km = Column(Numeric(10, 2), default=0.0)
    notes = Column(Text)
    
    vehicle = relationship("Vehicle", back_populates="journey_sessions")
    driver = relationship("Driver", back_populates="journey_sessions")

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

