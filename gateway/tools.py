import time
from datetime import datetime, timedelta, timezone

from gateway.device import DeviceRegistry

TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "set_fan", "description": "Turn the room fan on or off",
        "parameters": {"type": "object",
                       "properties": {"on": {"type": "boolean"}},
                       "required": ["on"]}}},
    {"type": "function", "function": {
        "name": "set_servo",
        "description": "Set vent louver angle in degrees (0=closed, 90=open)",
        "parameters": {"type": "object",
                       "properties": {"angle": {"type": "integer", "minimum": 0,
                                                "maximum": 90}},
                       "required": ["angle"]}}},
    {"type": "function", "function": {
        "name": "set_led", "description": "Set the RGB status LED",
        "parameters": {"type": "object",
                       "properties": {
                           "color": {"type": "string",
                                     "enum": ["off", "red", "green", "blue",
                                              "white", "amber"]},
                           "blink": {"type": "boolean", "default": False}},
                       "required": ["color"]}}},
    {"type": "function", "function": {
        "name": "buzzer",
        "description": "Sound the buzzer. short=100ms, double, siren=3s max",
        "parameters": {"type": "object",
                       "properties": {"pattern": {"type": "string",
                                                  "enum": ["short", "double",
                                                           "siren"]}},
                       "required": ["pattern"]}}},
    {"type": "function", "function": {
        "name": "display_text",
        "description": "Write two lines (max 16 chars each) to the OLED",
        "parameters": {"type": "object",
                       "properties": {"line1": {"type": "string", "maxLength": 16},
                                      "line2": {"type": "string", "maxLength": 16}},
                       "required": ["line1"]}}},
    {"type": "function", "function": {
        "name": "log_observation",
        "description": "Record a note about the room state; no physical action",
        "parameters": {"type": "object",
                       "properties": {"note": {"type": "string", "maxLength": 280}},
                       "required": ["note"]}}},
]

BUZZER_SECONDS = {"short": 0.1, "double": 0.4, "siren": 3.0}
VALID_TOOLS = {t["function"]["name"] for t in TOOL_SCHEMAS}


class GuardrailError(Exception):
    pass


class ToolRegistry:
    def __init__(self, registry: DeviceRegistry):
        self.registry = registry
        self._cycle_calls = 0

    def begin_cycle(self) -> None:
        self._cycle_calls = 0

    def _check(self, ok: bool, error: str) -> dict:
        return {"ok": ok, **({} if ok else {"error": error})}

    def _seconds_since(self, iso_ts: str) -> float:
        return (datetime.now(timezone.utc)
                - datetime.fromisoformat(iso_ts)).total_seconds()

    def _buzzer_seconds_used_last_hour(self) -> float:
        """Rolling hourly budget derived from the durable commands table
        (SPEC §5) — in-memory state would reset on restart, and a guardrail
        you can bypass by restarting the gateway is not a guardrail."""
        cutoff = (datetime.now(timezone.utc)
                  - timedelta(hours=1)).isoformat()
        args = self.registry.memory.recent_action_args("buzzer", cutoff)
        return sum(BUZZER_SECONDS.get(a.get("pattern", "short"), 0.1)
                   for a in args)

    async def execute(self, device_id: str, name: str, args: dict,
                      context: dict) -> dict:
        self._cycle_calls += 1
        if self._cycle_calls > 5:
            raise GuardrailError("cycle tool-call cap (5) exceeded")
        if name not in VALID_TOOLS:
            return self._check(False, f"unknown tool: {name}")

        if name == "set_fan":
            last_flip = self.registry.memory.last_action_ts("set_fan")
            if last_flip and self._seconds_since(last_flip) < 30:
                return self._check(False, "fan short-cycle guard (30s)")

        if name == "set_servo":
            args = {**args, "angle": max(0, min(90, int(args.get("angle", 0))))}

        if name == "buzzer":
            pattern = args.get("pattern", "short")
            if pattern == "siren":
                motion_ts = context.get("motion_ts")
                if not motion_ts or (time.time() - motion_ts) > 60:
                    return self._check(False, "siren requires motion within 60s")
            seconds = BUZZER_SECONDS.get(pattern, 0.1)
            if self._buzzer_seconds_used_last_hour() + seconds > 10.0:
                return self._check(False, "buzzer hourly budget (10s) exceeded")

        if name == "display_text":
            args = {"line1": str(args.get("line1", ""))[:16],
                    "line2": str(args.get("line2", ""))[:16]}

        if name == "log_observation":
            return self._check(True, "")  # logged by the agent, nothing physical

        await self.registry.dispatch(device_id, name, args)
        return self._check(True, "")
