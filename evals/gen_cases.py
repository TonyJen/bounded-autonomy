"""Synthetic eval case generator.

Samples randomized sensor snapshots across the operating ranges and labels
each with ground-truth tool expectations derived from the SPEC §4 rules —
the same rules the system prompt states and Agent.fallback() implements.
Deterministic for a given seed.

Label semantics (transition-based, matching the mock client):
- fan_on=False and temp>30  -> set_fan(on=True) REQUIRED
- fan_on=True  and temp<26  -> set_fan(on=False) REQUIRED
- motion and light<200      -> set_led REQUIRED
- anything else             -> no physical action required
States where a toggle would be redundant (fan already in desired state)
make set_fan neither required nor forbidden — both behaviors are correct.
log_observation / display_text are always allowed (never scored).
"""

import random

TRIGGERS = ["temp_threshold", "motion", "periodic"]
# physical tools only; free-text tools are never forbidden
PHYSICAL_TOOLS = ["set_fan", "set_servo", "set_led", "buzzer"]


def expected_actions(snapshot: dict, fan_on: bool) -> list[dict]:
    """Ground-truth REQUIRED actions for a snapshot, per SPEC §4 rules."""
    actions = []
    temp = snapshot["temp_c"]
    if temp is not None:
        if temp > 30 and not fan_on:
            actions.append({"name": "set_fan", "args": {"on": True}})
        elif temp < 26 and fan_on:
            actions.append({"name": "set_fan", "args": {"on": False}})
    if snapshot["motion"] and snapshot["light"] is not None \
            and snapshot["light"] < 200:
        actions.append({"name": "set_led", "args": {"color": "white"}})
    return actions


def generate_cases(count: int, seed: int = 42) -> list[dict]:
    """Generate `count` deterministic labeled cases (suite="generated")."""
    rng = random.Random(seed)
    cases = []
    for i in range(count):
        fan_on = rng.random() < 0.4
        snapshot = {
            "device_id": "eval",
            "trigger": rng.choice(TRIGGERS),
            "temp_c": round(rng.uniform(15.0, 45.0), 1),
            "humidity_pct": round(rng.uniform(10.0, 90.0), 1),
            "light": rng.randint(0, 4095),
            "motion": rng.randint(0, 1),
            "actuators": {"fan": fan_on},  # wire key: devices report actuators.fan
        }
        expected = expected_actions(snapshot, fan_on)
        expected_names = [a["name"] for a in expected]
        cases.append({
            "id": f"gen_{i:04d}",
            "name": f"Generated {i:04d} (t={snapshot['temp_c']} "
                    f"l={snapshot['light']} m={snapshot['motion']} "
                    f"fan={fan_on})",
            "suite": "generated",
            "context": snapshot,
            "required": expected_names,
            "forbidden": [t for t in PHYSICAL_TOOLS
                          if t not in expected_names
                          and not (t == "set_fan" and _fan_optional(
                              snapshot, fan_on))],
            "arg_checks": [{"tool": a["name"], "arg": k, "equals": v}
                           for a in expected
                           for k, v in a["args"].items()],
        })
    return cases


def _fan_optional(snapshot: dict, fan_on: bool) -> bool:
    """set_fan is optional (neither required nor forbidden) when the fan is
    already in the rule-desired state — retoggling and staying put are both
    acceptable, matching Agent.fallback() idempotence."""
    temp = snapshot["temp_c"]
    if temp is None:
        return True
    return (temp > 30 and fan_on) or (temp < 26 and not fan_on)
