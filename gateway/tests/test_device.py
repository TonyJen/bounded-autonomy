import pytest
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry


def make_reg(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    return DeviceRegistry(Memory(db), online_window_s=600,
                          device_token="secret")


def test_offline_until_seen(tmp_path):
    reg = make_reg(tmp_path)
    assert not reg.is_online("esp32-01")
    reg.note_seen("esp32-01", "192.168.1.70")
    assert reg.is_online("esp32-01")


@pytest.mark.asyncio
async def test_dispatch_queues_when_offline(tmp_path, monkeypatch):
    reg = make_reg(tmp_path)
    pushed = []

    async def fake_push(ip, envelope):
        pushed.append(envelope)
        return True

    monkeypatch.setattr(reg, "_push", fake_push)
    cmd_id = await reg.dispatch("esp32-01", "set_fan", {"on": True})
    assert cmd_id.startswith("cmd_")
    assert pushed == []  # offline → no push attempt
    pending = reg.pending("esp32-01", 0)
    assert len(pending) == 1 and pending[0]["action"] == "set_fan"


@pytest.mark.asyncio
async def test_dispatch_pushes_when_online(tmp_path, monkeypatch):
    reg = make_reg(tmp_path)
    reg.note_seen("esp32-01", "192.168.1.70")

    async def fake_push(ip, envelope):
        assert ip == "192.168.1.70"
        return True

    monkeypatch.setattr(reg, "_push", fake_push)
    cmd_id = await reg.dispatch("esp32-01", "set_led", {"color": "green"})
    assert reg.pending("esp32-01", 0)[0]["status"] == "pushed"
