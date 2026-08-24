import argparse
import asyncio
import json
import os
import re
import signal
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx

from simulator.physics import RoomModel


class SimDevice:
    def __init__(self, gateway_url: str, device_token: str,
                 device_id: str = "sim-01", heartbeat_s: float = 300.0,
                 speed: float = 1.0):
        self.gateway_url = gateway_url.rstrip("/")
        self.device_token = device_token
        self.device_id = device_id
        self.heartbeat_s = heartbeat_s
        self.speed = speed
        self.room = RoomModel()
        self._seq = 0
        self._last_cmd = 0
        self._applied_push: set[str] = set()  # cmd_ids applied via push
        self._motion_clear_at: int | None = None  # ticks until motion auto-clear

    def _applied_push_ids(self) -> set:
        # tests construct with __new__ (no __init__); create lazily
        s = getattr(self, "_applied_push", None)
        if s is None:
            s = self._applied_push = set()
        return s

    # ── payload ──────────────────────────────────────────────────────
    def _sense_payload(self, type_: str, trigger: str) -> dict:
        self._seq += 1
        return {
            "device_id": self.device_id, "type": type_, "trigger": trigger,
            "seq": self._seq, "uptime_s": self._seq,
            "sensors": self.room.snapshot(),
            "actuators": {"fan": self.room.fan, "servo_deg": self.room.servo_deg,
                          "led": self.room.led, "buzzer": self.room.buzzer,
                          "oled": self.room.oled},
        }

    def _apply(self, action: str, args: dict) -> None:
        self.room.set_actuator(action, args)

    # ── sync (used by tests and simple scripts) ─────────────────────
    def _sync_client(self):
        # tests inject a TestClient as self._client; use it if present,
        # otherwise open a real connection to the gateway
        injected = getattr(self, "_client", None)
        if injected is not None:
            return injected, False
        return httpx.Client(timeout=10), True

    def send_sense_sync(self, type_: str, trigger: str) -> dict:
        c, owned = self._sync_client()
        try:
            r = c.post(f"{self.gateway_url}/sense",
                       json=self._sense_payload(type_, trigger),
                       headers={"X-Device-Token": self.device_token})
            r.raise_for_status()
            return r.json()
        finally:
            if owned:
                c.close()

    def poll_commands_sync(self) -> int:
        c, owned = self._sync_client()
        try:
            r = c.get(f"{self.gateway_url}/commands",
                      params={"device_id": self.device_id, "after": self._last_cmd},
                      headers={"X-Device-Token": self.device_token})
            r.raise_for_status()
            cmds = r.json()["commands"]
            for cmd in cmds:
                # skip commands already applied via push (dedupe by cmd_id)
                if cmd["cmd_id"] not in self._applied_push_ids():
                    self._apply(cmd["action"], cmd["args"])
                c.post(f"{self.gateway_url}/commands/{cmd['cmd_id']}/ack",
                       json={"ok": True},
                       headers={"X-Device-Token": self.device_token})
                self._last_cmd = max(self._last_cmd, cmd["id"])
            return len(cmds)
        finally:
            if owned:
                c.close()

    # ── async (used by run loop) ────────────────────────────────────
    async def send_sense(self, type_: str, trigger: str) -> dict:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.post(f"{self.gateway_url}/sense",
                             json=self._sense_payload(type_, trigger),
                             headers={"X-Device-Token": self.device_token})
            r.raise_for_status()
            return r.json()

    async def poll_commands(self) -> int:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"{self.gateway_url}/commands",
                            params={"device_id": self.device_id,
                                    "after": self._last_cmd},
                            headers={"X-Device-Token": self.device_token})
            r.raise_for_status()
            cmds = r.json()["commands"]
            for cmd in cmds:
                # skip commands already applied via push (dedupe by cmd_id)
                if cmd["cmd_id"] not in self._applied_push_ids():
                    self._apply(cmd["action"], cmd["args"])
                await c.post(f"{self.gateway_url}/commands/{cmd['cmd_id']}/ack",
                             json={"ok": True},
                             headers={"X-Device-Token": self.device_token})
                self._last_cmd = max(self._last_cmd, cmd["id"])
            return len(cmds)

    # ── push receiver (stdlib http.server) ──────────────────────────
    def run_push_server(self, port: int = 8080) -> ThreadingHTTPServer:
        device = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                if self.path not in ("/command", "/scenario", "/event"):
                    self._respond(404); return
                if self.headers.get("X-Device-Token") != device.device_token:
                    self._respond(401); return
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                if self.path == "/command":
                    self._handle_command(body)
                elif self.path == "/scenario":
                    self._handle_scenario(body)
                else:
                    self._handle_event(body)

            def _respond(self, status: int, payload: dict | None = None) -> None:
                try:
                    self.send_response(status)
                    if payload is not None:
                        body = json.dumps(payload).encode()
                        self.send_header("Content-Type", "application/json")
                        # Content-Length lets the caller finish reading
                        # immediately — without it the body is delimited by
                        # connection close, which now happens after the
                        # best-effort ack, not right after the response.
                        self.send_header("Content-Length", str(len(body)))
                        self.end_headers()
                        self.wfile.write(body)
                    else:
                        self.end_headers()
                except (ConnectionError, OSError):
                    pass  # caller already hung up; nothing left to do

            def _handle_command(self, body: dict) -> None:
                device._apply(body.get("action", ""), body.get("args", {}))
                cmd_id = body.get("cmd_id", "")
                device._applied_push_ids().add(cmd_id)
                # Respond FIRST: the gateway's push_timeout (2s) must never
                # race our best-effort ack callback — a slow ack used to
                # delay this response until the gateway hung up, and the
                # write then threw ConnectionAbortedError (WinError 10053).
                self._respond(200, {"ok": True})
                # best-effort ack so the gateway doesn't keep serving this
                # command to the poll path (which dedupes by cmd_id anyway)
                try:
                    c, owned = device._sync_client()
                    try:
                        c.post(
                            f"{device.gateway_url}/commands/{cmd_id}/ack",
                            json={"ok": True},
                            headers={"X-Device-Token": device.device_token})
                    finally:
                        if owned:
                            c.close()
                except Exception:
                    pass

            def _handle_scenario(self, body: dict) -> None:
                name = str(body.get("name", ""))
                if not re.fullmatch(r"[a-z_]+", name):
                    self._respond(400, {"ok": False,
                                        "error": "invalid scenario name"})
                    return
                path = os.path.join("simulator", "scenarios", f"{name}.json")
                if not os.path.exists(path):
                    self._respond(404, {"ok": False,
                                        "error": "unknown scenario"})
                    return
                with open(path) as f:
                    device.room.apply_scenario(json.load(f))
                self._respond(200, {"ok": True})

            def _handle_event(self, body: dict) -> None:
                trigger = body.get("trigger")
                if trigger == "motion":
                    device.room.force(motion=True)
                    device._motion_clear_at = 5  # ticks until auto-clear
                    # heartbeats only fire every ~300 ticks, so a manual
                    # motion press would almost never reach the gateway —
                    # push an immediate event sense (best-effort)
                    try:
                        device.send_sense_sync("event", "motion")
                    except Exception as e:
                        print(f"motion event sense failed: {e}")
                elif trigger == "heat":
                    device.room.force(temp_c=35.0)
                elif trigger == "dark":
                    device.room.force(light=50)
                else:
                    self._respond(400, {"ok": False,
                                        "error": "unknown trigger"})
                    return
                self._respond(200, {"ok": True})

            def log_message(self, *args):
                pass  # quiet

        return ThreadingHTTPServer(("0.0.0.0", port), Handler)

    # ── run loop ────────────────────────────────────────────────────
    async def run(self, cycles: int = 10_000,
                  stop_event: asyncio.Event | None = None) -> None:
        consecutive_errors = 0
        for i in range(cycles):
            if stop_event is not None and stop_event.is_set():
                break
            self.room.tick(1.0 * self.speed)
            if self._motion_clear_at is not None:
                self._motion_clear_at -= 1
                if self._motion_clear_at <= 0:
                    self.room.force(motion=False)
                    self._motion_clear_at = None
            try:
                if i % max(1, int(self.heartbeat_s)) == 0:
                    await self.send_sense("heartbeat", "periodic")
                await self.poll_commands()
                consecutive_errors = 0
            except httpx.HTTPError as e:
                # Gateway restart / transient network failure must not kill
                # the simulator — back off and keep running.
                consecutive_errors += 1
                backoff = min(2.0 * consecutive_errors, 30.0)
                print(f"gateway unreachable ({e}); retry in {backoff:.0f}s")
                await asyncio.sleep(backoff)
            await asyncio.sleep(1.0 / self.speed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://localhost:8000")
    parser.add_argument("--token",
                        default=os.environ.get("DEVICE_TOKEN", ""),
                        help="device auth token (default: $DEVICE_TOKEN; "
                             "required — the gateway no longer ships a "
                             "public default)")
    parser.add_argument("--device-id", default=None,
                        help="device identifier sent to gateway "
                             "(default: sim-<pid>)")
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--push-port", type=int, default=8080)
    parser.add_argument("--cycles", type=int, default=10_000_000,
                        help="loop iterations before exit; default runs "
                             "~69 days at speed 1 (10k was ~3 min at 60x)")
    args = parser.parse_args()
    if not args.token:
        parser.error("--token or DEVICE_TOKEN env var is required")

    device_id = args.device_id or f"sim-{os.getpid()}"
    dev = SimDevice(args.gateway, args.token, device_id=device_id,
                    speed=args.speed)
    if args.scenario:
        with open(f"simulator/scenarios/{args.scenario}.json") as f:
            dev.room.apply_scenario(json.load(f))
    server = dev.run_push_server(args.push_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    stop_event = asyncio.Event()

    def _shutdown(signum, frame):
        print(f"\nreceived signal {signum}, shutting down simulator...")
        loop.call_soon_threadsafe(stop_event.set)

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _shutdown)
        except ValueError:
            pass  # SIGTERM may not be available on all platforms

    try:
        loop.run_until_complete(dev.run(cycles=args.cycles,
                                        stop_event=stop_event))
    finally:
        server.shutdown()
        loop.close()
        sys.exit(0)


if __name__ == "__main__":
    main()
