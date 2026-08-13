import json


def _coerce_temp(value):
    """Non-numeric sensor values (e.g. injected strings) are treated as a
    sensor failure, never as a temperature."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


class MockGrokClient:
    """Scripted correct behavior, keyed off the context JSON in the last
    user message. Validates gateway plumbing deterministically."""

    async def chat(self, messages, tools):
        ctx = json.loads(messages[-1]["content"])
        s = ctx["sensors"]
        actuators = ctx.get("actuators") or {}
        fan_on = bool(actuators.get("fan_on"))
        calls = []

        def tc(name, args):
            return {"id": f"mock{len(calls)}", "type": "function",
                    "function": {"name": name,
                                 "arguments": json.dumps(args)}}

        temp = _coerce_temp(s["temp_c"])
        if temp is None:
            calls.append(tc("log_observation", {"note": "sensors offline"}))
        else:
            # independent rule branches: heat response and night-motion
            # response can co-occur (e.g. hot room + motion at night)
            if temp > 30 and not fan_on:  # hysteresis: no retoggle
                calls.append(tc("set_fan", {"on": True}))
                calls.append(tc("log_observation", {"note": "heat"}))
            elif temp < 26 and fan_on:
                calls.append(tc("set_fan", {"on": False}))
                calls.append(tc("log_observation", {"note": "cooled"}))
            if s["motion"] and s["light"] < 200:
                calls.append(tc("set_led", {"color": "white"}))
                calls.append(tc("log_observation",
                                {"note": "night motion"}))
            if not calls:
                calls.append(tc("log_observation", {"note": "all normal"}))

        return {"choices": [{"message": {"tool_calls": calls}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}


class BrokenGrokClient:
    """Always fails; forces Agent.run_cycle onto the rule-based fallback.
    Used by the fallback eval suite (client="broken")."""

    model = "broken"

    async def chat(self, messages, tools):
        from gateway.agent import GrokError
        raise GrokError("broken client: simulated outage")
