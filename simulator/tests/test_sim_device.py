import json
import threading
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
def gateway(tmp_path):
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


@pytest.mark.asyncio
async def test_send_sense_and_poll(gateway):
    client, mem = gateway
    room = RoomModel()
    dev = SimDevice.__new__(SimDevice)  # constructed without network init
    dev.gateway_url = "http://test"
    dev.device_token = "secret"
    dev.device_id = "sim-01"
    dev.room = room
    dev._seq = 0
    dev._last_cmd = 0
    dev._client = client  # TestClient speaks the same httpx API (async via ASGI? no—sync)

    # use sync wrappers for testability
    resp = dev.send_sense_sync("heartbeat", "periodic")
    assert resp["accepted"] is True
    assert mem.latest_snapshot()["device_id"] == "sim-01"

    mem.queue_command("sim-01", "set_fan", {"on": True}, "cmd_t1")
    applied = dev.poll_commands_sync()
    assert applied == 1
    assert room.fan is True
    assert mem.commands_after("sim-01", 0) == []  # acked


def test_null_sensor_snapshot():
    room = RoomModel()
    room.force(temp_c=None, humidity_pct=None)
    snap = room.snapshot()
    assert snap["temp_c"] is None and snap["humidity_pct"] is None


def test_push_server_applies_command(tmp_path):
    room = RoomModel()
    dev = SimDevice.__new__(SimDevice)
    dev.room = room
    dev.device_token = "secret"
    server = dev.run_push_server(port=18099)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        import httpx
        resp = httpx.post("http://127.0.0.1:18099/command",
                          json={"cmd_id": "c1", "action": "set_servo",
                                "args": {"angle": 90}, "issued_at": "t",
                                "ttl_s": 30},
                          headers={"X-Device-Token": "secret"}, timeout=5)
        assert resp.status_code == 200
        assert room.servo_deg == 90
    finally:
        server.shutdown()


@pytest.mark.asyncio
async def test_push_round_trip_gateway_to_sim(tmp_path):
    """Regression (C1/I1): DeviceRegistry._push must send X-Device-Token or
    the sim push receiver 401s; and a command applied via push must not be
    re-applied when the poll path later serves it (dedupe by cmd_id)."""
    from gateway.db import init_db as _init_db

    db = str(tmp_path / "t.db")
    _init_db(db)
    mem = Memory(db)
    reg = DeviceRegistry(mem, device_token="secret", push_port=18099)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    app = create_app(settings, mem, reg)
    client = TestClient(app)
    client.__enter__()

    room = RoomModel()
    dev = SimDevice.__new__(SimDevice)
    dev.room = room
    dev.device_token = "secret"
    dev.gateway_url = "http://test"
    dev.device_id = "sim-01"
    dev._seq = 0
    dev._last_cmd = 0
    dev._client = client  # poll + push-ack go through the ASGI app

    applies = []
    orig_apply = dev._apply

    def counting_apply(action, args):
        applies.append(action)
        orig_apply(action, args)

    dev._apply = counting_apply

    server = dev.run_push_server(port=18099)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        reg.note_seen("sim-01", "127.0.0.1")
        cmd_id = await reg.dispatch("sim-01", "set_servo", {"angle": 45})
        # _push awaits the HTTP response, which the sim sends after applying
        assert room.servo_deg == 45
        assert mem.commands_after("sim-01", 0)[0]["status"] == "pushed"
        # I1: the poll path still serves status='pushed' commands, but the
        # sim must skip cmd_ids it already applied via push
        dev.poll_commands_sync()
        assert applies.count("set_servo") == 1
        assert room.servo_deg == 45
    finally:
        server.shutdown()
        client.__exit__(None, None, None)
