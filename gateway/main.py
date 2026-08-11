from gateway.app import create_app
from gateway.config import get_settings
from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.memory import Memory

settings = get_settings()
init_db(settings.db_path)
memory = Memory(settings.db_path)
registry = DeviceRegistry(memory)
app = create_app(settings, memory, registry)
