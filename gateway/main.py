from gateway.app import create_app
from gateway.config import get_settings
from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.memory import Memory

settings = get_settings()
init_db(settings.db_path)
memory = Memory(settings.db_path)
registry = DeviceRegistry(memory)

from gateway.agent import Agent, GrokClient
from gateway.tools import ToolRegistry

agent = Agent(memory, ToolRegistry(registry), GrokClient(settings))
app = create_app(settings, memory, registry, on_wake=agent.run_cycle)
