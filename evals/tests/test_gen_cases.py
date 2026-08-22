"""Tests for the synthetic case generator: determinism, label consistency
with the shipped fallback rules, and mock-mode end-to-end pass."""
from evals.gen_cases import generate_cases, expected_actions
from evals.runner import run_evals


def test_deterministic_per_seed():
    a = generate_cases(20, seed=7)
    b = generate_cases(20, seed=7)
    c = generate_cases(20, seed=8)
    assert a == b
    assert a != c
    assert [case["id"] for case in a] == [f"gen_{i:04d}" for i in range(20)]


def test_labels_agree_with_fallback_rules():
    """Generated labels must not drift from the shipped rules: every
    REQUIRED action must be one Agent.fallback() would take, and fallback
    must never take an action the case FORBIDS."""
    from gateway.agent import Agent
    agent = Agent(memory=None, tools=None, client=None)
    for case in generate_cases(100, seed=123):
        ctx = case["context"]
        fb = agent.fallback(ctx)  # fallback reads reported actuators.fan from ctx
        fb_names = [a["name"] for a in fb]
        for req in case["required"]:
            assert req in fb_names, (case["id"], req, fb_names)
        for a in fb:
            assert a["name"] not in case["forbidden"], \
                (case["id"], a["name"], case["forbidden"])
        for chk in case["arg_checks"]:
            match = [a for a in fb if a["name"] == chk["tool"]]
            assert match and match[0]["args"].get(chk["arg"]) == \
                chk["equals"], (case["id"], chk)


def test_expected_actions_rule_coverage():
    base = {"temp_c": 22.0, "light": 900, "motion": 0}
    assert expected_actions(base, fan_on=False) == []
    assert expected_actions({**base, "temp_c": 35.0}, fan_on=False) == \
        [{"name": "set_fan", "args": {"on": True}}]
    assert expected_actions({**base, "temp_c": 35.0}, fan_on=True) == []
    assert expected_actions({**base, "temp_c": 20.0}, fan_on=True) == \
        [{"name": "set_fan", "args": {"on": False}}]
    assert expected_actions({**base, "light": 100, "motion": 1},
                            fan_on=False) == \
        [{"name": "set_led", "args": {"color": "white"}}]


def test_generated_suite_passes_mock(tmp_path):
    out = run_evals(db_path=str(tmp_path / "t.db"), mode="mock",
                    extra_cases=generate_cases(50, seed=42),
                    suites=["generated"],
                    results_dir=str(tmp_path / "results"))
    assert out["summary"]["total"] == 50
    assert out["summary"]["passed"] == 50, \
        [r["case_id"] for r in out["results"] if not r["passed"]]
