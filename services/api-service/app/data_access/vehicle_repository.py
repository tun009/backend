from fastcrud import FastCRUD

from app.models import Vehicle
from app.schemas.vehicle_schemas import VehicleCreate, VehicleUpdate, VehicleRead

# FastCRUD pattern for Vehicle model
CRUDVehicle = FastCRUD[Vehicle, VehicleCreate, VehicleUpdate, VehicleUpdate, VehicleUpdate, VehicleRead]
crud_vehicles = CRUDVehicle(Vehicle)

