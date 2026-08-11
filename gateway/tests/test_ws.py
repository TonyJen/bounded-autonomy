import pytest
from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import Settings
from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.events import ConnectionManager
from gateway.memory import Memory

SENSE = {
    "device_id": "esp32-01", "type": "heartbeat", "trigger": "periodic",
    "seq": 1, "uptime_s": 60,
    "sensors": {"temp_c": 24.5, "humidity_pct": 41.0, "light": 612,
                "motion": False},
    "actuators": {"fan": False, "servo_deg": 0, "led": {"r": 0, "g": 0, "b": 0},
                  "buzzer": False, "oled": ["a", "b"]},
}


def make_client(tmp_path, on_wake=None):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    app = create_app(settings, mem, DeviceRegistry(mem),
                     on_wake=on_wake, events=ConnectionManager())
    return TestClient(app)


def test_ws_receives_snapshot_on_sense(tmp_path):
    client = make_client(tmp_path)
    with client.websocket_connect("/ws") as ws:
        client.post("/sense", json=SENSE, headers={"X-Device-Token": "secret"})
        msg = ws.receive_json()
    assert msg["type"] == "snapshot"
    assert msg["data"]["sensors"]["temp_c"] == 24.5


def test_ws_receives_decision_after_wake(tmp_path):
    async def fake_wake(snapshot):
        return {"source": "agent", "tool_calls": [], "results": []}

    client = make_client(tmp_path, on_wake=fake_wake)
    with client.websocket_connect("/ws") as ws:
        client.post("/sense", json=SENSE, headers={"X-Device-Token": "secret"})
        first = ws.receive_json()
        second = ws.receive_json()
    assert first["type"] == "snapshot"
    assert second["type"] == "decision"
    assert second["data"]["source"] == "agent"
