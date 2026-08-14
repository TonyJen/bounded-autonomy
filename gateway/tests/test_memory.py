from gateway.db import init_db
from gateway.memory import Memory


def make_mem(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    return Memory(db)


def test_snapshot_roundtrip(tmp_path):
    mem = make_mem(tmp_path)
    mem.insert_snapshot("esp32-01", "heartbeat", "periodic",
                        {"temp_c": 24.5, "humidity_pct": 41.0, "light": 612,
                         "motion": False}, {"raw": True})
    latest = mem.latest_snapshot()
    assert latest["device_id"] == "esp32-01"
    assert latest["temp_c"] == 24.5
    assert latest["motion"] == 0  # bool stored as int


def test_command_lifecycle(tmp_path):
    mem = make_mem(tmp_path)
    mem.queue_command("esp32-01", "set_fan", {"on": True}, "cmd_1")
    pending = mem.commands_after("esp32-01", 0)
    assert len(pending) == 1 and pending[0]["status"] == "queued"
    mem.set_command_status("cmd_1", "acked")
    assert mem.commands_after("esp32-01", 0) == []


def test_mark_pushed_only_from_queued(tmp_path):
    """Once the sim's fast push response lets the device's ack arrive before
    the gateway marks the push complete, 'pushed' must not clobber 'acked'
    (acked commands must stay out of the poll path)."""
    mem = make_mem(tmp_path)
    mem.queue_command("esp32-01", "set_fan", {"on": True}, "cmd_2")
    mem.mark_pushed("cmd_2")
    assert mem.get_command("cmd_2")["status"] == "pushed"
    mem.set_command_status("cmd_2", "acked")
    mem.mark_pushed("cmd_2")  # late duplicate push-complete → no-op
    assert mem.get_command("cmd_2")["status"] == "acked"


def test_get_command_returns_action_and_parsed_args(tmp_path):
    mem = make_mem(tmp_path)
    mem.queue_command("esp32-01", "set_servo", {"angle": 45}, "cmd_9")
    cmd = mem.get_command("cmd_9")
    assert cmd["action"] == "set_servo"
    assert cmd["args"] == {"angle": 45}
    assert mem.get_command("cmd_missing") is None


def test_recent_decisions_limit(tmp_path):
    mem = make_mem(tmp_path)
    for i in range(15):
        mem.record_decision("periodic", "agent", {"i": i}, [], 100.0, {})
    assert len(mem.recent_decisions(10)) == 10
