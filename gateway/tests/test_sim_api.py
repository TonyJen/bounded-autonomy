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


def test_sim_scenario_device_unreachable_502(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    registry = DeviceRegistry(mem, push_port=19999)  # nothing listens there
    client = TestClient(create_app(settings, mem, registry))

    # register the device as online via a sense payload
    resp = client.post("/sense", json={
        "device_id": "sim-01", "type": "heartbeat", "trigger": "periodic",
        "seq": 1, "uptime_s": 1,
        "sensors": {"temp_c": 22.0, "humidity_pct": 40.0, "light": 500,
                    "motion": False},
        "actuators": {"fan": False, "servo_deg": 0, "led": False,
                      "buzzer": False, "oled": ""}},
        headers={"X-Device-Token": "secret"})
    assert resp.status_code == 200
    # point the device at an address where nothing is listening
    registry.note_seen("sim-01", "127.0.0.1")

    resp = client.post("/sim/scenario", json={"name": "heat_spike"})
    assert resp.status_code == 502
