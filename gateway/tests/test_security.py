"""Publish-security gates: no public default credential, and operator
endpoints must not be open to the network.

- DEVICE_TOKEN unset -> ephemeral random token per boot (never "dev-token",
  which publication makes public knowledge).
- Operator endpoints (/status, /history, /sim/*, /evals/*) allow loopback
  clients zero-config (the local dashboard must keep working), but remote
  clients need OPERATOR_TOKEN.
"""
import pytest
from fastapi.testclient import TestClient

from gateway.config import Settings, get_settings
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry
from gateway.app import create_app

REMOTE = ("203.0.113.9", 5000)  # TEST-NET-3: definitely not loopback


def make_client(tmp_path, operator_token=""):
    db = str(tmp_path / "t.db")
    init_db(db)
    mem = Memory(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="device-secret", db_path=db,
                        operator_token=operator_token)
    app = create_app(settings, mem, DeviceRegistry(mem))
    return app


# ---- device token: no public default ------------------------------------

def test_settings_no_public_default_device_token(monkeypatch):
    monkeypatch.delenv("DEVICE_TOKEN", raising=False)
    s = get_settings()
    assert s.device_token != "dev-token"
    assert len(s.device_token) >= 20


def test_settings_uses_configured_device_token(monkeypatch):
    monkeypatch.setenv("DEVICE_TOKEN", "chosen-secret")
    assert get_settings().device_token == "chosen-secret"


# ---- operator endpoints: loopback open, remote gated ---------------------

def test_loopback_dashboard_needs_no_token(tmp_path):
    """Zero-config local demo: the dashboard's own machine is always allowed."""
    app = make_client(tmp_path)
    assert TestClient(app).get("/status").status_code == 200


def test_remote_status_denied_without_operator_token(tmp_path):
    app = make_client(tmp_path)
    r = TestClient(app, client=REMOTE).get("/status")
    assert r.status_code == 403


def test_remote_history_denied_without_operator_token(tmp_path):
    app = make_client(tmp_path)
    r = TestClient(app, client=REMOTE).get("/history")
    assert r.status_code == 403


def test_remote_evals_run_denied_without_operator_token(tmp_path):
    """The credit-spending endpoint must not be reachable from the network."""
    app = make_client(tmp_path)
    r = TestClient(app, client=REMOTE).post("/evals/run", json={"mode": "live"})
    assert r.status_code == 403


def test_remote_sim_event_denied_without_operator_token(tmp_path):
    app = make_client(tmp_path)
    r = TestClient(app, client=REMOTE).post(
        "/sim/event", json={"trigger": "motion"})
    assert r.status_code == 403


def test_remote_allowed_with_correct_operator_token(tmp_path):
    app = make_client(tmp_path, operator_token="op-secret")
    c = TestClient(app, client=REMOTE)
    assert c.get("/status").status_code == 403
    assert c.get("/status", headers={"X-Operator-Token": "wrong"}).status_code == 403
    assert c.get("/status", headers={"X-Operator-Token": "op-secret"}).status_code == 200
