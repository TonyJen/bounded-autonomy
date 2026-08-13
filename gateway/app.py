import asyncio
import json
import logging
import os
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gateway.auth import make_device_auth
from gateway.config import Settings
from gateway.device import DeviceRegistry
from gateway.events import ConnectionManager
from gateway.memory import Memory

logger = logging.getLogger(__name__)

DIST_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
EVAL_RESULTS_DIR = os.getenv("EVAL_RESULTS_DIR", "evals/results")


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
               on_wake=None,
               events: ConnectionManager | None = None) -> FastAPI:
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
        if events is not None:
            await events.broadcast({"type": "snapshot",
                                    "data": payload.model_dump()})
        if wake and on_wake is not None:
            async def _wake_and_broadcast(snap):
                try:
                    result = await on_wake(snap)
                    if events is not None and result is not None:
                        await events.broadcast({"type": "decision",
                                                "data": result})
                except Exception:
                    logger.exception("on_wake failed")
            asyncio.create_task(_wake_and_broadcast(memory.latest_snapshot()))
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
        if events is not None:
            cmd = memory.get_command(cmd_id) or {}
            await events.broadcast({"type": "actuator",
                                    "data": {"cmd_id": cmd_id,
                                             "ok": payload.ok,
                                             "action": cmd.get("action"),
                                             "args": cmd.get("args")}})
        return {"recorded": True}

    @app.get("/status")
    async def status():
        latest = memory.latest_snapshot() or {}
        raw = latest.get("raw_json")
        actuators = (json.loads(raw).get("actuators") if raw else None)
        return {
            "device": {"online": bool(latest) and registry.is_online(
                latest.get("device_id", ""))},
            "sensors": {k: latest.get(k) for k in
                        ("temp_c", "humidity_pct", "light", "motion")},
            "actuators": actuators,
            "last_seen": latest.get("ts"),
        }

    @app.get("/history")
    async def history(limit: int = 10):
        return {"snapshots": memory.recent_snapshots(limit),
                "decisions": memory.recent_decisions(limit)}

    async def _forward_to_device(path: str, body: dict):
        from fastapi import HTTPException
        latest = memory.latest_snapshot() or {}
        device_id = latest.get("device_id", "")
        if not device_id or not registry.is_online(device_id):
            raise HTTPException(status_code=503, detail="device offline")
        ip = registry._seen[device_id][0]
        url = f"http://{ip}:{registry.push_port}{path}"
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.post(
                    url, json=body,
                    headers={"X-Device-Token": settings.device_token})
        except httpx.HTTPError:
            raise HTTPException(status_code=502, detail="device unreachable")
        return {"ok": resp.status_code == 200, "device_status": resp.status_code}

    @app.post("/sim/scenario")
    async def sim_scenario(payload: dict):
        return await _forward_to_device("/scenario", payload)

    @app.post("/sim/event")
    async def sim_event(payload: dict):
        return await _forward_to_device("/event", payload)

    EVAL_JOBS: dict = {}

    class EvalRunRequest(BaseModel):
        mode: str = "mock"
        cases: Optional[list] = None

    @app.post("/evals/run")
    async def evals_run(req: EvalRunRequest):
        import uuid as _uuid
        run_id = _uuid.uuid4().hex[:12]
        EVAL_JOBS[run_id] = {"status": "running"}

        async def _job():
            from evals.runner import run_evals
            import asyncio as _asyncio
            try:
                out = await _asyncio.to_thread(
                    run_evals, db_path=settings.db_path, mode=req.mode,
                    case_ids=req.cases)
                # run_evals mints its own timestamp run_id; re-key the job
                # under it so /evals/history ids resolve on the job endpoint
                job = {"status": "completed", "result": out,
                       "eval_run_id": out["run_id"]}
                EVAL_JOBS[run_id] = job
                EVAL_JOBS[out["run_id"]] = job
                if events is not None:
                    await events.broadcast({"type": "eval_progress",
                                            "data": {"run_id": run_id,
                                                     "status": "completed"}})
            except Exception as e:
                EVAL_JOBS[run_id] = {"status": "failed", "error": str(e)}
                if events is not None:
                    await events.broadcast({"type": "eval_progress",
                                            "data": {"run_id": run_id,
                                                     "status": "failed"}})

        asyncio.create_task(_job())
        return {"run_id": run_id, "status": "running"}

    @app.get("/evals/run/{run_id}")
    async def evals_run_status(run_id: str):
        from fastapi import HTTPException
        job = EVAL_JOBS.get(run_id)
        if not job:
            raise HTTPException(status_code=404, detail="run not found")
        return job

    @app.get("/evals/history")
    async def evals_history(limit: int = 10):
        import json as _json
        from gateway.db import get_conn
        conn = get_conn(settings.db_path)
        try:
            rows = conn.execute(
                "SELECT run_id, ts, mode, model, summary_json FROM eval_runs"
                " ORDER BY id DESC LIMIT ?", (max(1, min(limit, 50)),)
            ).fetchall()
            return {"runs": [{"run_id": r["run_id"], "ts": r["ts"],
                              "mode": r["mode"], "model": r["model"],
                              "summary": _json.loads(r["summary_json"])}
                             for r in rows]}
        finally:
            conn.close()

    @app.get("/evals/record/{run_id}")
    async def evals_record(run_id: str):
        """Full stored run record (per-case correctness + performance) for
        drill-down from the history list. Reads the durable JSON artifact,
        so it works across restarts — unlike the in-memory job store."""
        import json as _json
        import re
        from fastapi import HTTPException
        if not re.fullmatch(r"[0-9A-Za-z]+", run_id):
            raise HTTPException(status_code=400, detail="bad run id")
        path = os.path.join(EVAL_RESULTS_DIR, f"run_{run_id}.json")
        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail="run record not found")
        with open(path, encoding="utf-8") as f:
            return _json.load(f)

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        if events is None:
            await ws.close(code=1008)
            return
        await events.connect(ws)
        try:
            while True:
                await ws.receive_text()  # discard client messages
        except WebSocketDisconnect:
            events.disconnect(ws)

    if os.path.isdir(DIST_DIR):
        app.mount("/", StaticFiles(directory=DIST_DIR, html=True),
                  name="spa")

    return app
