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
