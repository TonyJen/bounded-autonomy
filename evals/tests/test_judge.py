"""Tests for the LLM judge: verdict parsing, runner integration via a stub
judge (no network), and calibration-set integrity."""
import asyncio
import json
import os

from evals.judge import Judge, _parse_verdict, _calibration_path
from evals.runner import _run_case, run_evals
from evals.cases import CASES


class StubJudgeClient:
    """Returns a canned verdict; records the prompt it was given."""
    def __init__(self, content):
        self.content = content
        self.seen = None

    async def chat(self, messages, tools):
        self.seen = messages
        return {"choices": [{"message": {"content": self.content}}],
                "usage": {}}


def test_parse_verdict_clean_json():
    v = _parse_verdict('{"passed": true, "reason": "grounded"}')
    assert v == {"pass": True, "reason": "grounded"}


def test_parse_verdict_with_reasoning_prefix():
    v = _parse_verdict('Criterion 1 ok. Criterion 2 ok.\n'
                       '{"passed": false, "reason": "fabricated temp"}')
    assert v["pass"] is False
    assert v["reason"] == "fabricated temp"


def test_parse_verdict_unparseable_fails_closed():
    v = _parse_verdict("I cannot decide")
    assert v["pass"] is False
    assert v["reason"].startswith("judge_error")


def test_judge_sends_rubric_and_context():
    client = StubJudgeClient('{"passed": true, "reason": "ok"}')
    judge = Judge(client)
    verdict = asyncio.run(judge.judge(
        [{"temp_c": 35.0}], ["set_fan"],
        [{"tool": "log_observation", "args": {"note": "hot"}}]))
    assert verdict["pass"] is True
    assert "Rubric" in client.seen[0]["content"]
    payload = json.loads(client.seen[1]["content"])
    assert payload["actions_taken"] == ["set_fan"]
    assert payload["free_text_outputs"][0]["args"]["note"] == "hot"


def test_runner_records_judge_verdict(tmp_path):
    """A case with free-text outputs gets detail.judge when a judge is on."""
    from gateway.agent import Agent
    from gateway.db import init_db
    from gateway.memory import Memory
    from gateway.device import DeviceRegistry
    from gateway.tools import ToolRegistry
    from evals.mock_grok import MockGrokClient

    init_db(str(tmp_path / "t.db"))
    mem = Memory(str(tmp_path / "t.db"))
    agent = Agent(mem, ToolRegistry(DeviceRegistry(mem)), MockGrokClient())
    judge = Judge(StubJudgeClient('{"passed": false, "reason": "stub says no"}'))
    case = next(c for c in CASES if c["id"] == "heat_spike")
    result = asyncio.run(_run_case(case, agent, judge))
    assert result["detail"]["judge"] == {"pass": False,
                                         "reason": "stub says no"}


def test_mock_mode_never_judges(tmp_path):
    out = run_evals(db_path=str(tmp_path / "t.db"), mode="mock",
                    case_ids=["heat_spike"],
                    results_dir=str(tmp_path / "results"))
    assert "judge" not in out["results"][0]["detail"]
    assert "judge" not in out["summary"]


def test_calibration_set_integrity():
    path = _calibration_path()
    assert os.path.exists(path)
    with open(path) as f:
        examples = json.load(f)
    assert len(examples) >= 15
    labels = set()
    for ex in examples:
        assert isinstance(ex["label"], bool), ex["id"]
        assert ex["contexts"] and ex["free_text_outputs"]
        labels.add(ex["label"])
    assert labels == {True, False}  # both passes and fails represented
