import time

import pytest

from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.memory import Memory
from gateway.tools import TOOL_SCHEMAS, GuardrailError, ToolRegistry


def make_tools(tmp_path):
    db = str(tmp_path / "t.db")
    init_db(db)
    mem = Memory(db)
    return ToolRegistry(DeviceRegistry(mem)), mem


def test_schemas_match_spec():
    names = {t["function"]["name"] for t in TOOL_SCHEMAS}
    assert names == {"set_fan", "set_servo", "set_led", "buzzer",
                     "display_text", "log_observation"}


@pytest.mark.asyncio
async def test_servo_clamped(tmp_path):
    tools, mem = make_tools(tmp_path)
    r = await tools.execute("d1", "set_servo", {"angle": 270}, {})
    assert r["ok"] is True
    assert '"angle": 90' in mem.commands_after("d1", 0)[0]["args_json"]


@pytest.mark.asyncio
async def test_unknown_tool_rejected(tmp_path):
    tools, _ = make_tools(tmp_path)
    r = await tools.execute("d1", "self_destruct", {}, {})
    assert r["ok"] is False and "unknown" in r["error"].lower()


@pytest.mark.asyncio
async def test_fan_short_cycle_blocked(tmp_path):
    tools, _ = make_tools(tmp_path)
    assert (await tools.execute("d1", "set_fan", {"on": True}, {}))["ok"]
    r = await tools.execute("d1", "set_fan", {"on": False}, {})
    assert r["ok"] is False and "short-cycle" in r["error"]


@pytest.mark.asyncio
async def test_siren_requires_recent_motion(tmp_path):
    tools, _ = make_tools(tmp_path)
    r = await tools.execute("d1", "buzzer", {"pattern": "siren"},
                            {"motion_ts": None})
    assert r["ok"] is False
    ok = await tools.execute("d1", "buzzer", {"pattern": "siren"},
                             {"motion_ts": time.time()})
    assert ok["ok"] is True


@pytest.mark.asyncio
async def test_buzzer_hourly_budget(tmp_path):
    tools, _ = make_tools(tmp_path)
    ctx = {"motion_ts": time.time()}
    for _ in range(3):
        assert (await tools.execute("d1", "buzzer", {"pattern": "siren"}, ctx))["ok"]  # 3×3s = 9s
    r = await tools.execute("d1", "buzzer", {"pattern": "double"}, ctx)  # +~0.4s... then siren over
    assert r["ok"] is True
    r2 = await tools.execute("d1", "buzzer", {"pattern": "siren"}, ctx)  # 9+0.4+3 > 10
    assert r2["ok"] is False and "budget" in r2["error"]


@pytest.mark.asyncio
async def test_cycle_call_cap(tmp_path):
    tools, _ = make_tools(tmp_path)
    tools.begin_cycle()
    for i in range(5):
        await tools.execute("d1", "log_observation", {"note": f"n{i}"}, {})
    with pytest.raises(GuardrailError):
        await tools.execute("d1", "log_observation", {"note": "six"}, {})


@pytest.mark.asyncio
async def test_log_observation_no_dispatch(tmp_path):
    tools, mem = make_tools(tmp_path)
    r = await tools.execute("d1", "log_observation", {"note": "quiet"}, {})
    assert r["ok"] is True
    assert mem.commands_after("d1", 0) == []  # nothing physical queued
