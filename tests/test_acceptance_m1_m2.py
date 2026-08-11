"""SPEC §10 acceptance: M1 (simulator→gateway storage) + M2 (command round-trip)."""
import time

import pytest
from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry
from gateway.app import create_app
from simulator.device import SimDevice
from simulator.physics import RoomModel


@pytest.fixture
def stack(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    app = create_app(settings, mem, DeviceRegistry(mem))
    client = TestClient(app)
    client.__enter__()
    yield client, mem
    client.__exit__(None, None, None)


def _device(client):
    dev = SimDevice.__new__(SimDevice)
    dev.gateway_url = "http://test"
    dev.device_token = "secret"
    dev.device_id = "sim-01"
    dev.room = RoomModel()
    dev._seq = 0
    dev._last_cmd = 0
    return dev


def test_m1_simulator_ticks_are_stored(stack):
    client, mem = stack
    dev = _device(client)
    # TestClient is the sync ASGI-transport httpx client for the app
    r = client.post("/sense", json=dev._sense_payload("heartbeat", "periodic"),
                    headers={"X-Device-Token": "secret"})
    assert r.status_code == 200
    latest = mem.latest_snapshot()
    assert latest is not None and latest["device_id"] == "sim-01"
    status = client.get("/status").json()
    assert status["sensors"]["temp_c"] is not None


def test_m2_event_to_command_acked_under_3s(stack):
    client, mem = stack
    dev = _device(client)
    start = time.monotonic()
    h = {"X-Device-Token": "secret"}
    client.post("/sense", json=dev._sense_payload("event", "motion"), headers=h)
    mem.queue_command("sim-01", "set_led", {"color": "white"}, "cmd_acc")
    cmds = client.get("/commands", params={"device_id": "sim-01", "after": 0},
                      headers=h).json()["commands"]
    assert cmds and cmds[0]["action"] == "set_led"
    client.post(f"/commands/{cmds[0]['cmd_id']}/ack", json={"ok": True},
                headers=h)
    assert time.monotonic() - start < 3.0
    assert mem.commands_after("sim-01", 0) == []
