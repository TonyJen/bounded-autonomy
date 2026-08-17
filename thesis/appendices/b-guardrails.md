# Appendix B — Guardrail Specification and Enforcement

Normative text: `docs/SPEC.md` §5. Enforcement: `gateway/tools.py`
(`ToolRegistry.execute`). Guardrails are validated **after** the model
predicts and **before** any command is queued — model output is untrusted
input, and `ToolRegistry.execute` is the *only* path from prediction to
dispatch.

## B.1 The four rules

| # | Guardrail | Rule | Physical rationale |
|---|---|---|---|
| 1 | Servo clamp | angle clamped to [0°, 90°] — `max(0, min(90, int(angle)))` | SG90 travel limit; clamped rather than rejected because an out-of-range angle still carries usable intent |
| 2 | Buzzer budget | ≤ 10 s cumulative per rolling hour (`_buzzer_window` pruned to `time.time() - 3600`); pattern seconds from a table (`short` = 0.1 s … `siren` = 3 s); `siren` additionally requires `motion_ts` within 60 s | annoyance budget; the most aggressive actuator has a physical precondition no context string can fabricate |
| 3 | Fan anti-short-cycle | ≥ 30 s between state flips (`time.monotonic()` against `_fan_last_flip`) | motor longevity; control-engineering hysteresis enforced against a language model |
| 4 | Cycle width | per-cycle counter incremented on entry to `execute`; the 6th call raises `GuardrailError("cycle tool-call cap (5) exceeded")` | bounds runaway or injected cycles at a constant cost |

Unknown tool names are rejected before any rule runs
(`unknown tool: {name}`) and counted — that count is the
hallucination-rate metric.

## B.2 Enforcement pseudocode (as implemented)

```python
async def execute(self, device_id, name, args, context):
    self._cycle_calls += 1
    if self._cycle_calls > 5:                              # rule 4
        raise GuardrailError("cycle tool-call cap (5) exceeded")
    if name not in VALID_TOOLS:                            # hallucination metric
        return reject(f"unknown tool: {name}")

    if name == "set_fan":                                  # rule 3
        if time.monotonic() - self._fan_last_flip < 30:
            return reject("fan short-cycle guard (30s)")
        self._fan_last_flip = time.monotonic()

    if name == "set_servo":                                # rule 1
        args["angle"] = max(0, min(90, int(args.get("angle", 0))))

    if name == "buzzer":                                   # rule 2
        if args.pattern == "siren":
            if not context.motion_ts or time.time() - context.motion_ts > 60:
                return reject("siren requires motion within 60s")
        seconds = BUZZER_SECONDS[args.pattern]
        self._buzzer_window = prune_to_last_hour(self._buzzer_window)
        if sum(self._buzzer_window) + seconds > 10.0:
            return reject("buzzer hourly budget (10s) exceeded")
        self._buzzer_window.append((time.time(), seconds))

    if name == "display_text":                             # argument hygiene
        args = truncate_to_oled(args, 16)                  # 16-char lines

    if name == "log_observation":
        return ok()  # recorded by the agent; nothing physical

    await self.registry.dispatch(device_id, name, args)    # the only way out
    return ok()
```

## B.3 Observability

Every validation outcome feeds the quality metrics of Chapter 5:

- **hallucination rate** — calls whose names match no schema
- **rejection rate** — schema-valid calls refused by rules 1–4, logged
  with reasons
- **fallback rate** — cycles served by rules instead of the model
  (recorded with `source: "fallback"`)
- **p95 latency** — snapshot → dispatch time, budgeted at 10 s

## B.4 Fallback rule table (SPEC §4.1)

Engaged when the Grok call raises or times out (`GrokError`). Runs on the
*sanitized* snapshot, and its calls pass through the same guardrails.
Deliberately narrower than the model's authority — the fallback never
sounds the buzzer, moves the servo, or writes the OLED.

| Condition | Action |
|---|---|
| `temp_c is None` | `set_led(amber)` — and nothing else; sensor failure dominates |
| `temp_c > 30` | `set_fan(on=true)` |
| `temp_c < 26` **and fan currently on** | `set_fan(on=false)` — hysteresis: never flip a fan that isn't running |
| `motion` and `light < 200` | `set_led(white)` |
| otherwise | observe; no actuation |

Note the second row's precedence: a null temperature short-circuits the
table, so a failed sensor can never simultaneously trigger both the amber
LED and a thermal response.

## B.5 Guardrail test matrix

Each rule is pinned by unit tests (`gateway/tests/test_tools.py`) and
exercised end-to-end by at least one eval case:

| Rule | Unit-test probes | Eval-suite exercise |
|---|---|---|
| Servo clamp | angle −10 → 0; angle 200 → 90; non-integer coerced | boundary suite (argument validity) |
| Buzzer budget | cumulative seconds across the rolling hour; window pruning | `buzzer_abuse` (custom check tallies attempted vs. used) |
| Siren precondition | siren with no motion → reject; motion 61 s old → reject; 59 s → pass | adversarial suite forbids `buzzer` under injection |
| Fan anti-short-cycle | flip at 29 s → reject; at 31 s → pass | `fan_hysteresis` (one toggle across four cycles) |
| Cycle cap | 6th call raises `GuardrailError` | normative cases stay ≤ 2 calls by spec |
| Unknown tool | name not in schema → reject, counted | hallucination-rate metric across all runs |

The matrix is the audit trail for the thesis's central move: every rule
is tested in isolation *and* observed in the integrated system, so the
guardrail layer is neither dead code nor unobserved machinery.
