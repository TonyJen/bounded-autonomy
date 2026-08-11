import json


class MockGrokClient:
    """Scripted correct behavior, keyed off the context JSON in the last
    user message. Validates gateway plumbing deterministically."""

    async def chat(self, messages, tools):
        ctx = json.loads(messages[-1]["content"])
        s = ctx["sensors"]
        calls = []

        def tc(name, args, i):
            return {"id": f"mock{i}", "type": "function",
                    "function": {"name": name,
                                 "arguments": json.dumps(args)}}

        if s["temp_c"] is None:
            calls.append(tc("log_observation", {"note": "sensors offline"}, 0))
        elif s["temp_c"] > 30:
            calls.append(tc("set_fan", {"on": True}, 0))
            calls.append(tc("log_observation", {"note": "heat"}, 1))
        elif s["motion"] and s["light"] < 200:
            calls.append(tc("set_led", {"color": "white"}, 0))
            calls.append(tc("log_observation", {"note": "night motion"}, 1))
        else:
            calls.append(tc("log_observation", {"note": "all normal"}, 0))

        return {"choices": [{"message": {"tool_calls": calls}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1}}
