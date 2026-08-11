import asyncio
import json
import logging
from typing import Optional

from fastapi import Depends, FastAPI, Request
from pydantic import BaseModel

from gateway.auth import make_device_auth
from gateway.config import Settings
from gateway.device import DeviceRegistry
from gateway.memory import Memory

logger = logging.getLogger(__name__)


class SensePayload(BaseModel):
    device_id: str
    type: str
    trigger: str
    seq: int
    uptime_s: int
    sensors: dict
    actuators: dict


class AckPayload(BaseModel):
    ok: bool
    error: Optional[str] = None


def create_app(settings: Settings, memory: Memory, registry: DeviceRegistry,
               on_wake=None) -> FastAPI:
    app = FastAPI(title="Grok Guardian Gateway")
    auth = make_device_auth(settings.device_token)

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    @app.post("/sense", dependencies=[Depends(auth)])
    async def sense(payload: SensePayload, request: Request):
        memory.insert_snapshot(payload.device_id, payload.type,
                               payload.trigger, payload.sensors,
                               payload.model_dump())
        client_ip = request.client.host if request.client else ""
        registry.note_seen(payload.device_id, client_ip)

        wake = payload.type == "heartbeat" or payload.type == "event"
        if wake and on_wake is not None:
            snapshot = memory.latest_snapshot()
            asyncio.create_task(on_wake(snapshot))
        return {"accepted": True, "agent_wake": wake and on_wake is not None}

    @app.get("/commands", dependencies=[Depends(auth)])
    async def commands(device_id: str, after: int = 0):
        rows = registry.pending(device_id, after)
        return {"commands": [
            {"id": r["id"], "cmd_id": r["cmd_id"], "action": r["action"],
             "args": json.loads(r["args_json"]),
             "issued_at": r["ts"], "ttl_s": 30}
            for r in rows]}

    @app.post("/commands/{cmd_id}/ack", dependencies=[Depends(auth)])
    async def ack(cmd_id: str, payload: AckPayload):
        memory.set_command_status(cmd_id, "acked" if payload.ok else "failed",
                                  payload.error)
        return {"recorded": True}

    @app.get("/status")
    async def status():
        latest = memory.latest_snapshot() or {}
        return {
            "device": {"online": bool(latest) and registry.is_online(
                latest.get("device_id", ""))},
            "sensors": {k: latest.get(k) for k in
                        ("temp_c", "humidity_pct", "light", "motion")},
            "last_seen": latest.get("ts"),
        }

    @app.get("/history")
    async def history(limit: int = 10):
        return {"snapshots": memory.recent_snapshots(limit),
                "decisions": memory.recent_decisions(limit)}

    return app
