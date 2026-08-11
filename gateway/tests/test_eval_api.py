import time
from fastapi.testclient import TestClient

from gateway.config import Settings
from gateway.db import init_db
from gateway.memory import Memory
from gateway.device import DeviceRegistry
from gateway.app import create_app


def test_eval_run_endpoints(tmp_path, monkeypatch):
    db = str(tmp_path / "t.db")
    init_db(db)
    monkeypatch.setenv("GUARDIAN_DB", db)
    monkeypatch.setattr("evals.runner.run_evals", lambda **kw: {
        "run_id": "r1", "summary": {"total": 5, "passed": 5, "failed": 0,
                                    "average_score": 1.0},
        "results": [], "comparison": {"baseline": False}})
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    app = create_app(settings, mem, DeviceRegistry(mem))
    client = TestClient(app)

    resp = client.post("/evals/run", json={"mode": "mock"})
    assert resp.status_code == 200
    run_id = resp.json()["run_id"]
    for _ in range(50):
        job = client.get(f"/evals/run/{run_id}").json()
        if job["status"] == "completed":
            break
        time.sleep(0.05)
    assert job["status"] == "completed"
    assert job["result"]["summary"]["passed"] == 5
    # I5: the completed job must expose the eval record's run_id, and the
    # job endpoint must also resolve under that id (history ids no 404)
    assert job["eval_run_id"] == "r1"
    by_eval_id = client.get("/evals/run/r1")
    assert by_eval_id.status_code == 200
    assert by_eval_id.json()["status"] == "completed"


def test_eval_record_drilldown(tmp_path, monkeypatch):
    """GET /evals/record/{run_id} serves the durable JSON artifact."""
    import json
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    record = {"run_id": "20260811T101523123456Z",
              "metadata": {"mode": "mock"},
              "summary": {"total": 5, "passed": 5},
              "results": [{"case_id": "heat_spike", "passed": True,
                           "score": 1.0,
                           "detail": {"required_ok": True},
                           "perf": {"latency_ms": 10.0, "input_tokens": 1,
                                    "output_tokens": 1}}]}
    (results_dir / f"run_{record['run_id']}.json").write_text(
        json.dumps(record))
    monkeypatch.setattr("gateway.app.EVAL_RESULTS_DIR", str(results_dir))

    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    client = TestClient(create_app(settings, mem, DeviceRegistry(mem)))

    resp = client.get(f"/evals/record/{record['run_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["results"][0]["perf"]["latency_ms"] == 10.0
    assert body["results"][0]["detail"]["required_ok"] is True

    assert client.get("/evals/record/doesnotexist").status_code == 404
    assert client.get("/evals/record/..%2F..%2Fetc").status_code in (400, 404)
