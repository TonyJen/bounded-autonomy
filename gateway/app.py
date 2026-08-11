import asyncio
import json
import logging
from typing import Optional

from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from gateway.auth import make_device_auth
from gateway.config import Settings
from gateway.device import DeviceRegistry
from gateway.events import ConnectionManager
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
            await events.broadcast({"type": "actuator",
                                    "data": {"cmd_id": cmd_id,
                                             "ok": payload.ok}})
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

    return app
