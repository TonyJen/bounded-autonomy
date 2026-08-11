import time
import pytest
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry
from gateway.tools import ToolRegistry
from gateway.agent import Agent, GrokError


class StubClient:
    def __init__(self, response=None, fail=False):
        self.response = response
        self.fail = fail
        self.calls = []

    async def chat(self, messages, tools):
        self.calls.append({"messages": messages, "tools": tools})
        if self.fail:
            raise GrokError("api down")
        return self.response


def make_agent(tmp_path, client):
    db = str(tmp_path / "t.db")
    init_db(db)
    mem = Memory(db)
    return Agent(mem, ToolRegistry(DeviceRegistry(mem)), client), mem


SNAP = {"device_id": "d1", "trigger": "motion", "temp_c": 35.0,
        "humidity_pct": 40.0, "light": 600, "motion": 1}


def tool_call(name, args, _id="t1"):
    return {"id": _id, "type": "function",
            "function": {"name": name, "arguments": __import__("json").dumps(args)}}


@pytest.mark.asyncio
async def test_agent_dispatches_tool_calls(tmp_path):
    resp = {"choices": [{"message": {"tool_calls": [
        tool_call("set_fan", {"on": True})]}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5}}
    agent, mem = make_agent(tmp_path, StubClient(resp))
    out = await agent.run_cycle(SNAP)
    assert out["source"] == "agent"
    assert out["tool_calls"][0]["name"] == "set_fan"
    assert mem.commands_after("d1", 0)[0]["action"] == "set_fan"
    assert mem.recent_decisions(1)[0]["source"] == "agent"


@pytest.mark.asyncio
async def test_agent_falls_back_on_grok_failure(tmp_path):
    agent, mem = make_agent(tmp_path, StubClient(fail=True))
    out = await agent.run_cycle(SNAP)  # 35°C → fallback fan on
    assert out["source"] == "fallback"
    assert any(c["name"] == "set_fan" and c["args"]["on"] for c in out["tool_calls"])
    assert mem.commands_after("d1", 0)[0]["action"] == "set_fan"


@pytest.mark.asyncio
async def test_fallback_dark_motion_lights_led(tmp_path):
    agent, _ = make_agent(tmp_path, StubClient(fail=True))
    dark = {**SNAP, "temp_c": 22.0, "light": 50, "motion": 1}
    out = await agent.run_cycle(dark)
    assert any(c["name"] == "set_led" for c in out["tool_calls"])


@pytest.mark.asyncio
async def test_normal_conditions_no_fallback_action(tmp_path):
    agent, _ = make_agent(tmp_path, StubClient(fail=True))
    calm = {**SNAP, "temp_c": 22.0, "light": 900, "motion": 0}
    out = await agent.run_cycle(calm)
    assert out["tool_calls"] == []


@pytest.mark.asyncio
async def test_malformed_tool_args_fed_back(tmp_path):
    bad = {"choices": [{"message": {"tool_calls": [
        tool_call("set_servo", {"angle": "ninety"})]}}], "usage": {}}
    agent, _ = make_agent(tmp_path, StubClient(bad))
    out = await agent.run_cycle(SNAP)
    assert out["results"][0]["ok"] is False


def test_context_includes_snapshot():
    agent = Agent.__new__(Agent)
    agent.memory = None
    msgs = agent.build_context(SNAP)
    assert msgs[0]["role"] == "system"
    assert "35.0" in msgs[-1]["content"]
