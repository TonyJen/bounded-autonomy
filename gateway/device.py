import time
import uuid
from datetime import datetime, timezone

import httpx

from gateway.memory import Memory


class DeviceRegistry:
    def __init__(self, memory: Memory, push_timeout: float = 2.0,
                 online_window_s: int = 600, device_token: str = "",
                 push_port: int = 8080):
        self.memory = memory
        self.push_timeout = push_timeout
        self.online_window_s = online_window_s
        self.device_token = device_token
        self.push_port = push_port
        self._seen: dict[str, tuple[str, float]] = {}  # device_id -> (ip, ts)

    def note_seen(self, device_id: str, ip: str) -> None:
        self._seen[device_id] = (ip, time.monotonic())

    def is_online(self, device_id: str) -> bool:
        entry = self._seen.get(device_id)
        if not entry:
            return False
        return (time.monotonic() - entry[1]) < self.online_window_s

    async def _push(self, ip: str, envelope: dict) -> bool:
        url = f"http://{ip}:{self.push_port}/command"
        try:
            async with httpx.AsyncClient(timeout=self.push_timeout) as client:
                resp = await client.post(
                    url, json=envelope,
                    headers={"X-Device-Token": self.device_token})
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def dispatch(self, device_id: str, action: str, args: dict) -> str:
        cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
        self.memory.queue_command(device_id, action, args, cmd_id)
        if self.is_online(device_id):
            ip = self._seen[device_id][0]
            envelope = {
                "cmd_id": cmd_id,
                "issued_at": datetime.now(timezone.utc).isoformat(),
                "ttl_s": 30,
                "action": action,
                "args": args,
            }
            if await self._push(ip, envelope):
                self.memory.set_command_status(cmd_id, "pushed")
        return cmd_id

    def pending(self, device_id: str, after_id: int) -> list[dict]:
        return self.memory.commands_after(device_id, after_id)
