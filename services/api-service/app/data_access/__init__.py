# This file makes the 'crud' directory a Python package.
# It also makes it easier to import CRUD functions from other modules.

from .user_repository import user_repo
from .vehicle_repository import crud_vehicles
from .driver_repository import crud_drivers
from .device_repository import crud_devices 