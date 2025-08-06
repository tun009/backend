from fastcrud import FastCRUD

from app.models import DeviceLog
from app.schemas.device_log_schemas import DeviceLogCreate, DeviceLogUpdate, DeviceLogRead

# FastCRUD pattern - all CRUD operations built-in!
CRUDDeviceLog = FastCRUD[DeviceLog, DeviceLogCreate, DeviceLogUpdate, DeviceLogUpdate, DeviceLogUpdate, DeviceLogRead]
crud_device_logs = CRUDDeviceLog(DeviceLog)
