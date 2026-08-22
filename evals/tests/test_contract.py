"""Contract tests: the eval harness must measure model behavior against the
actuator payload shape production devices actually send.

The wire contract (simulator/device.py, firmware net.cpp) reports fan state
as actuators.fan. An earlier drift had the evals seed and read
actuators.fan_on — a key no device ever sends — so hysteresis behavior was
only ever validated against a payload shape production never produces."""
import json

import pytest

from evals.cases import CASES
from evals.gen_cases import generate_cases
from evals.mock_grok import MockGrokClient


def _case_contexts(case):
    if "context" in case:
        return [case["context"]]
    return list(case.get("sequence", []))


def test_normative_cases_use_production_actuator_keys():
    for case in CASES:
        for ctx in _case_contexts(case):
            actuators = ctx.get("actuators") or {}
            assert "fan_on" not in actuators, case["id"]


def test_generated_cases_use_production_actuator_keys():
    for case in generate_cases(20, seed=42):
        actuators = case["context"].get("actuators") or {}
        assert "fan_on" not in actuators, case["id"]


@pytest.mark.asyncio
async def test_mock_client_hysteresis_reads_production_fan_key():
    """30.5C with the device reporting fan=True must NOT retoggle the fan.
    A mock reading a drifted key sees 'fan off' and emits set_fan(on) —
    passing evals for behavior production would call a bug."""
    ctx = {"sensors": {"temp_c": 30.5, "light": 600, "motion": 0},
           "actuators": {"fan": True}}
    resp = await MockGrokClient().chat(
        [{"role": "user", "content": json.dumps(ctx)}], [])
    calls = resp["choices"][0]["message"]["tool_calls"]
    names = [c["function"]["name"] for c in calls]
    assert "set_fan" not in names
