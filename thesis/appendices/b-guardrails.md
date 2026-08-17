# Appendix B — Guardrail Specification and Enforcement

Normative text: `docs/SPEC.md` §5. Enforcement: `gateway/tools.py`.
Guardrails are validated **after** the model predicts and **before** any
command is queued — model output is untrusted input.

## B.1 The four rules

| # | Guardrail | Rule | Physical rationale |
|---|---|---|---|
| 1 | Servo clamp | angle ∈ [0°, 90°]; out-of-range values are clamped | SG90 travel limit |
| 2 | Buzzer budget | ≤ 10 s cumulative per rolling hour; `siren` pattern additionally requires a `motion` event within the last 60 s | annoyance budget; no sirens without a cause |
| 3 | Fan anti-short-cycle | ≥ 30 s between fan state transitions | motor longevity; mirrors thermal hysteresis |
| 4 | Cycle width | ≤ 5 tool calls dispatched per agent cycle | bounds runaway/injected cycles |

## B.2 Enforcement pseudocode

```
def dispatch(tool_calls, state, now):
    dispatched, rejected = [], []
    for call in tool_calls:
        self._cycle_calls += 1
        if self._cycle_calls > 5:                            # rule 4
            raise GuardrailError("cycle tool-call cap (5) exceeded")
        try:
            args = SCHEMAS[call.name].validate(call.args)  # unknown name → hallucination metric
        except ValidationError as e:
            rejected.append((call, e)); continue

        if call.name == "set_servo":
            args.angle = clamp(args.angle, 0, 90)          # rule 1
        elif call.name == "buzzer":
            if state.buzzer_seconds_last_hour + args.seconds > 10:
                rejected.append((call, "buzzer budget")); continue   # rule 2a
            if args.pattern == "siren" and not state.motion_within(60):
                rejected.append((call, "siren needs recent motion")) # rule 2b
        elif call.name == "set_fan":
            if now - state.fan_last_flip < 30:
                rejected.append((call, "fan anti-short-cycle"))      # rule 3
        dispatched.append(call)

    queue.push_all(dispatched)        # durable until acked
    record(dispatched, rejected)      # both are first-class metrics
    return dispatched, rejected
```

## B.3 Observability

Every validation outcome feeds the quality metrics of Chapter 5:

- **hallucination rate** — calls whose names match no schema
- **rejection rate** — schema-valid calls refused by rules 1–4
- **fallback rate** — cycles served by rules instead of the model
- **p95 latency** — snapshot → dispatch time, budgeted at 10 s

## B.4 Fallback rule table (SPEC §4.1)

Engaged when the Grok call raises or times out. Deliberately narrower
than the model's authority — the fallback never sounds the buzzer.

| Condition | Action |
|---|---|
| temperature > 30 °C | `set_fan(on=true)` |
| dark (< 200 lux) + recent motion | `set_led(white)` |
| sensor NaN | `set_led(amber)` |
| otherwise | observe; no actuation |
