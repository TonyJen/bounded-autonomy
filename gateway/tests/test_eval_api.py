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
