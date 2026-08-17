import pytest
from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry
from gateway.app import create_app


def make_client(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="test",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    app = create_app(settings, mem, DeviceRegistry(mem))
    return TestClient(app), mem


SENSE = {
    "device_id": "esp32-01", "type": "heartbeat", "trigger": "periodic",
    "seq": 1, "uptime_s": 60,
    "sensors": {"temp_c": 24.5, "humidity_pct": 41.0, "light": 612,
                "motion": False},
    "actuators": {"fan": False, "servo_deg": 0,
                  "led": {"r": 0, "g": 0, "b": 0}, "buzzer": False,
                  "oled": ["a", "b"]},
}


def test_sense_requires_token(tmp_path):
    client, _ = make_client(tmp_path)
    assert client.post("/sense", json=SENSE).status_code == 401


def test_startup_prunes_old_snapshots(tmp_path):
    """SPEC §7: snapshots older than 7 days are pruned on gateway startup."""
    from datetime import datetime, timedelta, timezone
    from gateway.db import get_conn
    client, mem = make_client(tmp_path)
    old = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
    conn = get_conn(mem.db_path)
    conn.execute(
        "INSERT INTO snapshots (device_id, ts, type, trigger, raw_json)"
        " VALUES ('d1', ?, 'heartbeat', 'periodic', '{}')", (old,))
    conn.commit()
    conn.close()
    with client:  # entering the TestClient fires lifespan startup
        pass
    assert mem.recent_snapshots(10) == []


def test_sense_stores_snapshot(tmp_path):
    client, mem = make_client(tmp_path)
    resp = client.post("/sense", json=SENSE, headers={"X-Device-Token": "secret"})
    assert resp.status_code == 200
    assert resp.json()["accepted"] is True
    assert mem.latest_snapshot()["temp_c"] == 24.5


def test_command_poll_and_ack(tmp_path):
    client, mem = make_client(tmp_path)
    mem.queue_command("esp32-01", "set_fan", {"on": True}, "cmd_x")
    h = {"X-Device-Token": "secret"}
    cmds = client.get("/commands", params={"device_id": "esp32-01", "after": 0},
                      headers=h).json()["commands"]
    assert cmds[0]["action"] == "set_fan"
    ok = client.post("/commands/cmd_x/ack", json={"ok": True}, headers=h)
    assert ok.status_code == 200
    assert client.get("/commands", params={"device_id": "esp32-01", "after": 0},
                      headers=h).json()["commands"] == []


class _RecordingEvents:
    def __init__(self):
        self.messages = []

    async def broadcast(self, message):
        self.messages.append(message)


def test_ack_broadcast_includes_action_and_args(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="test",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    events = _RecordingEvents()
    app = create_app(settings, mem, DeviceRegistry(mem), events=events)
    client = TestClient(app)
    mem.queue_command("esp32-01", "set_fan", {"on": True}, "cmd_b")
    h = {"X-Device-Token": "secret"}
    resp = client.post("/commands/cmd_b/ack", json={"ok": True}, headers=h)
    assert resp.status_code == 200
    actuator_msgs = [m for m in events.messages if m["type"] == "actuator"]
    assert actuator_msgs == [
        {"type": "actuator",
         "data": {"cmd_id": "cmd_b", "ok": True,
                  "action": "set_fan", "args": {"on": True}}}]


def test_status_includes_actuators(tmp_path):
    client, _ = make_client(tmp_path)
    h = {"X-Device-Token": "secret"}
    # no snapshot yet: actuators is null
    assert client.get("/status").json()["actuators"] is None
    client.post("/sense", json=SENSE, headers=h)
    status = client.get("/status").json()
    assert status["actuators"] == SENSE["actuators"]


def test_status_and_history(tmp_path):
    client, _ = make_client(tmp_path)
    h = {"X-Device-Token": "secret"}
    client.post("/sense", json=SENSE, headers=h)
    status = client.get("/status").json()
    assert status["device"]["online"] is True
    assert status["sensors"]["temp_c"] == 24.5
    history = client.get("/history").json()
    assert len(history["snapshots"]) == 1
