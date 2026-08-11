import argparse
import asyncio
import json
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
                if self.path != "/command":
                    self.send_response(404); self.end_headers(); return
                if self.headers.get("X-Device-Token") != device.device_token:
                    self.send_response(401); self.end_headers(); return
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
                device._apply(body.get("action", ""), body.get("args", {}))
                cmd_id = body.get("cmd_id", "")
                device._applied_push_ids().add(cmd_id)
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
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"ok": true}')

            def log_message(self, *args):
                pass  # quiet

        return ThreadingHTTPServer(("0.0.0.0", port), Handler)

    # ── run loop ────────────────────────────────────────────────────
    async def run(self, cycles: int = 10_000) -> None:
        for i in range(cycles):
            self.room.tick(1.0 * self.speed)
            if i % max(1, int(self.heartbeat_s)) == 0:
                await self.send_sense("heartbeat", "periodic")
            await self.poll_commands()
            await asyncio.sleep(1.0 / self.speed)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gateway", default="http://localhost:8000")
    parser.add_argument("--token", default="dev-token")
    parser.add_argument("--scenario", default=None)
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--push-port", type=int, default=8080)
    args = parser.parse_args()

    dev = SimDevice(args.gateway, args.token, speed=args.speed)
    if args.scenario:
        with open(f"simulator/scenarios/{args.scenario}.json") as f:
            dev.room.apply_scenario(json.load(f))
    server = dev.run_push_server(args.push_port)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    asyncio.run(dev.run())


if __name__ == "__main__":
    main()
