from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import Settings
from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.memory import Memory


def make_client(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    return TestClient(create_app(settings, mem, DeviceRegistry(mem)))


def test_sim_scenario_device_offline(tmp_path):
    client = make_client(tmp_path)
    resp = client.post("/sim/scenario", json={"name": "heat_spike"})
    assert resp.status_code == 503


def test_sim_event_device_offline(tmp_path):
    client = make_client(tmp_path)
    resp = client.post("/sim/event", json={"trigger": "motion"})
    assert resp.status_code == 503
