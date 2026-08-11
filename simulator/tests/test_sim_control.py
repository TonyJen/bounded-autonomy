import threading

import httpx
import pytest

from simulator.device import SimDevice


@pytest.fixture
def sim_server():
    dev = SimDevice.__new__(SimDevice)
    from simulator.physics import RoomModel
    dev.room = RoomModel()
    dev.device_token = "secret"
    dev.device_id = "sim-01"
    dev.gateway_url = "http://127.0.0.1:19999"  # unreachable; sense is best-effort
    server = dev.run_push_server(port=18101)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    yield dev
    server.shutdown()


def test_scenario_endpoint_applies_scenario(sim_server):
    resp = httpx.post("http://127.0.0.1:18101/scenario",
                      json={"name": "heat_spike"},
                      headers={"X-Device-Token": "secret"}, timeout=5)
    assert resp.status_code == 200
    sim_server.room.tick(1.0)
    assert sim_server.room.temp_c >= 34.9  # keyframe fired


def test_scenario_unknown_404(sim_server):
    resp = httpx.post("http://127.0.0.1:18101/scenario",
                      json={"name": "nonexistent"},
                      headers={"X-Device-Token": "secret"}, timeout=5)
    assert resp.status_code == 404


def test_scenario_name_traversal_rejected(sim_server):
    resp = httpx.post("http://127.0.0.1:18101/scenario",
                      json={"name": "../../etc/passwd"},
                      headers={"X-Device-Token": "secret"}, timeout=5)
    assert resp.status_code in (400, 404)


def test_event_motion_injection(sim_server):
    resp = httpx.post("http://127.0.0.1:18101/event",
                      json={"trigger": "motion"},
                      headers={"X-Device-Token": "secret"}, timeout=5)
    assert resp.status_code == 200
    assert sim_server.room.motion is True


def test_event_motion_fires_immediate_sense(sim_server, monkeypatch):
    calls = []

    def fake_send(type_, trigger):
        calls.append((type_, trigger))
        return {}

    monkeypatch.setattr(sim_server, "send_sense_sync", fake_send)
    resp = httpx.post("http://127.0.0.1:18101/event",
                      json={"trigger": "motion"},
                      headers={"X-Device-Token": "secret"}, timeout=5)
    assert resp.status_code == 200
    assert ("event", "motion") in calls
    assert sim_server.room.motion is True
