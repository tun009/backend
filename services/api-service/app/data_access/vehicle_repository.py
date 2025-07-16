from sqlalchemy.orm import Session

from app.models import Vehicle
from app.schemas.vehicle_schemas import VehicleCreateSchema, VehicleUpdateSchema
from .base_repository import BaseRepository

class VehicleRepository(BaseRepository[Vehicle, VehicleCreateSchema, VehicleUpdateSchema]):
    # You can add vehicle-specific methods here if needed
    def get_by_plate_number(self, db: Session, *, plate_number: str) -> Vehicle | None:
        return db.query(Vehicle).filter(Vehicle.plate_number == plate_number).first()

vehicle_repo = VehicleRepository(Vehicle) 