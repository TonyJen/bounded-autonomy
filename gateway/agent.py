import json
import logging
import time

import httpx

from gateway.memory import Memory
from gateway.tools import TOOL_SCHEMAS, ToolRegistry, GuardrailError

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Grok Guardian, the decision layer of a room-monitoring device. "
    "You receive sensor snapshots (temperature °C, humidity %, light 0-4095, "
    "motion) and decide physical actions via the provided tools. "
    "Rules: fan on above 30°C, off below 26°C. At night (light<200) with "
    "motion, light the LED white and log an observation. When everything is "
    "normal, call log_observation only or nothing. Never exceed tool limits; "
    "the gateway enforces them and will reject abuse."
)


class GrokError(Exception):
    pass


class GrokClient:
    def __init__(self, settings):
        self.base_url = settings.xai_base_url.rstrip("/")
        self.api_key = settings.xai_api_key
        self.model = settings.xai_model

    async def chat(self, messages: list, tools: list) -> dict:
        payload = {"model": self.model, "messages": messages,
                   "tools": tools, "tool_choice": "auto", "temperature": 0.2}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions", json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}"})
            if resp.status_code != 200:
                raise GrokError(f"grok {resp.status_code}: {resp.text[:200]}")
            try:
                return resp.json()
            except ValueError as e:
                raise GrokError(f"bad json: {e}") from e
        except httpx.HTTPError as e:
            raise GrokError(str(e)) from e


class Agent:
    def __init__(self, memory: Memory, tools: ToolRegistry, client):
        self.memory = memory
        self.tools = tools
        self.client = client
        self._last_motion_ts: float | None = None
        self._fan_on = False

    def build_context(self, snapshot: dict) -> list[dict]:
        # SPEC §4 step 2: current snapshot + actuator states + last-10
        # decisions + time. Actuators ride in the sense payload, stored as
        # raw_json on the snapshot row (or carried inline in tests/evals).
        actuators = snapshot.get("actuators")
        if actuators is None and snapshot.get("raw_json"):
            try:
                actuators = json.loads(snapshot["raw_json"]).get("actuators")
            except (ValueError, TypeError):
                actuators = None
        user = {
            "trigger": snapshot.get("trigger"),
            "sensors": {
                "temp_c": snapshot.get("temp_c"),
                "humidity_pct": snapshot.get("humidity_pct"),
                "light": snapshot.get("light"),
                "motion": bool(snapshot.get("motion")),
            },
            "actuators": actuators,
            "time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if getattr(self, "memory", None) is not None:
            user["recent_decisions"] = [
                {"trigger": d.get("trigger"), "source": d.get("source"),
                 "tools": [c.get("name") for c in
                           json.loads(d.get("tool_calls_json") or "[]")]}
                for d in self.memory.recent_decisions(10)
            ]
        return [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user)},
        ]

    async def _execute_call(self, device_id: str, name: str, args: dict) -> dict:
        """Execute one tool call; convert failures into a tool-result error."""
        try:
            result = await self.tools.execute(
                device_id, name, args, {"motion_ts": self._last_motion_ts})
        except (GuardrailError, ValueError, TypeError) as e:
            return {"ok": False, "error": str(e)}
        if name == "set_fan" and result.get("ok"):
            self._fan_on = bool(args.get("on"))
        return result

    async def run_cycle(self, snapshot: dict) -> dict:
        start = time.monotonic()
        if snapshot.get("motion"):
            self._last_motion_ts = time.time()

        self.tools.begin_cycle()
        try:
            resp = await self.client.chat(self.build_context(snapshot),
                                          TOOL_SCHEMAS)
            message = resp["choices"][0]["message"]
            raw_calls = message.get("tool_calls") or []
            calls, results = [], []
            for tc in raw_calls:
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except json.JSONDecodeError:
                    args = {}
                calls.append({"name": name, "args": args})
                results.append(await self._execute_call(
                    snapshot["device_id"], name, args))
            latency = (time.monotonic() - start) * 1000
            self.memory.record_decision(
                snapshot.get("trigger", "?"), "agent",
                {"snapshot": snapshot}, calls, latency, resp.get("usage", {}))
            return {"source": "agent", "tool_calls": calls, "results": results,
                    "latency_ms": round(latency, 1),
                    "usage": resp.get("usage", {})}

        except (GrokError, KeyError, IndexError) as e:
            logger.warning("agent falling back to rules: %s", e)
            calls = self.fallback(snapshot)
            results = []
            self.tools.begin_cycle()
            for c in calls:
                results.append(await self._execute_call(
                    snapshot["device_id"], c["name"], c["args"]))
            latency = (time.monotonic() - start) * 1000
            self.memory.record_decision(
                snapshot.get("trigger", "?"), "fallback",
                {"snapshot": snapshot}, calls, latency, {})
            return {"source": "fallback", "tool_calls": calls,
                    "results": results, "latency_ms": round(latency, 1),
                    "usage": {}}

    def fallback(self, snapshot: dict) -> list[dict]:
        actions = []
        temp = snapshot.get("temp_c")
        light = snapshot.get("light")
        if temp is None:
            actions.append({"name": "set_led", "args": {"color": "amber"}})
            return actions
        if temp > 30:
            actions.append({"name": "set_fan", "args": {"on": True}})
        elif temp < 26 and self._fan_on:  # SPEC §4.1: only flip if fan on
            actions.append({"name": "set_fan", "args": {"on": False}})
        if snapshot.get("motion") and light is not None and light < 200:
            actions.append({"name": "set_led", "args": {"color": "white"}})
        return actions
