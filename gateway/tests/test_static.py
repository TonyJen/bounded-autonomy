from fastapi.testclient import TestClient

from gateway.app import create_app
from gateway.config import Settings
from gateway.db import init_db
from gateway.device import DeviceRegistry
from gateway.memory import Memory


def test_root_serves_spa_when_dist_exists(tmp_path, monkeypatch):
    dist = tmp_path / "frontend" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html>spa</html>")
    monkeypatch.setattr("gateway.app.DIST_DIR", str(dist))
    db = str(tmp_path / "t.db")
    init_db(db)
    settings = Settings(xai_api_key="", xai_base_url="", xai_model="t",
                        device_token="secret", db_path=db)
    mem = Memory(db)
    client = TestClient(create_app(settings, mem, DeviceRegistry(mem)))
    resp = client.get("/")
    assert resp.status_code == 200 and "spa" in resp.text
