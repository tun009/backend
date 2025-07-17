from fastcrud import FastCRUD

from app.models import Device
from app.schemas.device_schemas import DeviceCreate, DeviceUpdate, DeviceRead

# FastCRUD pattern - all CRUD operations built-in!
CRUDDevice = FastCRUD[Device, DeviceCreate, DeviceUpdate, DeviceUpdate, DeviceUpdate, DeviceRead]
crud_devices = CRUDDevice(Device) 