from fastcrud import FastCRUD

from app.models import Driver
from app.schemas.driver_schemas import DriverCreate, DriverUpdate, DriverRead
 
# FastCRUD pattern - all CRUD operations built-in!
CRUDDriver = FastCRUD[Driver, DriverCreate, DriverUpdate, DriverUpdate, DriverUpdate, DriverRead]
crud_drivers = CRUDDriver(Driver) 