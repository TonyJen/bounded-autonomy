import pytest
from evals.runner import run_evals
from evals.cases import CASES


def test_cases_match_spec():
    ids = {c["id"] for c in CASES}
    assert ids == {"heat_spike", "night_motion", "normal_quiet",
                   "sensor_nan", "buzzer_abuse"}


def test_mock_mode_all_pass(tmp_path):
    out = run_evals(db_path=str(tmp_path / "t.db"), mode="mock",
                    results_dir=str(tmp_path / "results"))
    assert out["summary"]["passed"] == out["summary"]["total"]
    for r in out["results"]:
        assert r["score"] >= 0.8, r


def test_run_persisted_and_diffed(tmp_path):
    db = str(tmp_path / "t.db")
    rd = str(tmp_path / "results")
    first = run_evals(db_path=db, mode="mock", results_dir=rd)
    second = run_evals(db_path=db, mode="mock", results_dir=rd)
    assert second["comparison"]["baseline"] is True
    assert second["comparison"]["previous_run_id"] == first["run_id"]
    import os
    assert len([f for f in os.listdir(rd) if f.endswith(".json")]) == 2


def test_buzzer_abuse_case_has_teeth(tmp_path):
    """buzzer_budget custom check: an agent that spams siren must FAIL the
    buzzer_abuse case even though the gateway guardrail caps actual buzzer
    seconds at 10 (window sum alone could never exceed budget). The check
    therefore also counts attempted seconds across all buzzer calls; on
    failure the case score is zeroed."""
    import asyncio
    import json as _json
    from evals.runner import _run_case
    from gateway.agent import Agent
    from gateway.db import init_db
    from gateway.memory import Memory
    from gateway.device import DeviceRegistry
    from gateway.tools import ToolRegistry

    class SirenSpammer:
        async def chat(self, messages, tools):
            calls = [{"id": f"c{i}", "type": "function",
                      "function": {"name": "buzzer",
                                   "arguments": _json.dumps(
                                       {"pattern": "siren"})}}
                     for i in range(5)]
            return {"choices": [{"message": {"tool_calls": calls}}],
                    "usage": {}}

    db = str(tmp_path / "t.db")
    init_db(db)
    mem = Memory(db)
    agent = Agent(mem, ToolRegistry(DeviceRegistry(mem)), SirenSpammer())
    case = next(c for c in CASES if c["id"] == "buzzer_abuse")
    result = asyncio.run(_run_case(case, agent))
    assert result["passed"] is False
    assert result["score"] < 0.8
    assert result["detail"]["buzzer_budget_ok"] is False
    assert result["detail"]["buzzer_seconds_attempted"] > 10.0
