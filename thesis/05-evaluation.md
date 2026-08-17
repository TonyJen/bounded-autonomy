# Chapter 5 — Evaluation

## 5.1 Questions

The evaluation answers four questions, in order of increasing difficulty:

1. **Plumbing:** does the loop work — sensing, context, dispatch, ack,
   persistence? (unit/integration tests)
2. **Behavior:** given scripted disturbances, does the agent take the
   specified actions and refrain from forbidden ones? (behavior suites)
3. **Robustness:** does safety survive a failed model and a hostile
   context? (fallback and adversarial suites)
4. **Quality:** at what rates does the agent hallucinate tools, get
   rejected by guardrails, fall back, and how fast is it? (quality gates)

## 5.2 Plumbing: 88 tests

`pytest gateway/tests simulator/tests evals/tests tests -q` → **88
passed** (45 gateway, 17 simulator, 26 evals/acceptance), ~15 s. Coverage
includes the agent cycle, tool guardrails, device queue/ack, memory,
the WS bus, the sim control API, static hosting, and an end-to-end
M1–M2 acceptance test that runs a real snapshot→decision→ack loop.

## 5.3 Behavior: the suite design

Each case scripts a context (sensor values or an event stream), runs it
through the real agent path, and scores the tool calls:

> score = 0.5·(required tools present) + 0.3·(forbidden absent)
>         + 0.2·(arguments valid);  pass ≥ 0.8.

The suites probe distinct failure modes:

| Suite | Cases | What it probes | Example case |
|---|---:|---|---|
| normative | 5 | the core scenarios | `heat_spike` → `set_fan(on)` + log |
| boundary | 7 | threshold edges, hysteresis | `temp_just_above_30` fans on; `temp_at_30` does not; `fan_hysteresis` forbids re-toggling |
| adversarial | 3 | prompt injection | `injection_sensor_string` — malicious text in a sensor field must be ignored |
| fallback | 4 | rule-based path, model down | `fb_heat` → fallback still fans on |

## 5.4 Results (mock mode, run `20260817T013509855302Z`, git `9534b41`)

| Metric | Result | Gate |
|---|---:|---|
| Cases passed | **19/19** (avg score 1.000) | all suites |
| normative / boundary / adversarial / fallback | 5/5 · 7/7 · 3/3 · 4/4 | — |
| Hallucination rate (unknown tools) | **0.000** (0 of 32 calls) | ≤ 0.02 |
| Guardrail rejection rate | 0.000 | observed |
| Fallback rate | 0.167 (4 of 24 cycles, all in fallback suite) | observed |
| p95 cycle latency (mock) | 9.4 ms | < 10,000 ms budget |

Mock mode is deterministic by construction, so these numbers certify the
*gateway* — context assembly, tool dispatch, guardrails, fallback, and
scoring — rather than the model. That separation is deliberate: plumbing
correctness is a precondition for any live-model number to mean anything.

## 5.5 Live mode and judge calibration

`--mode live` replays the same suites against the real Grok API and adds
LLM-judge scoring of free-text outputs (`log_observation` rationales),
with the judge calibrated against human labels
(`evals/judge.py --calibrate`, labels in `evals/calibration/`). A live
campaign with quality gates (`--max-hallucination-rate 0.02
--latency-budget-ms 10000`) is part of the M8 demo-polish milestone and
is reported as future work rather than claimed here.

## 5.6 Threats to validity

1. **Mock determinism ≠ model behavior.** The 19/19 result certifies the
   harness; live-model rates may differ and will be measured, not
   assumed.
2. **Simulator fidelity.** Physics are hand-tuned; real DHT11 noise,
   WiFi loss, and timing jitter arrive only with M7 hardware.
3. **Suite coverage.** 19 hand-written cases cannot span the context
   space; `--gen` synthetic cases widen it but share the generator's
   biases.
4. **Single model.** Results are for one Grok model; the architecture is
   model-agnostic, the numbers are not.

## 5.7 Summary

The evidence supports the thesis statement's "if" direction: with
guardrails outside the trust boundary and a fallback behind the model, a
full sense→predict→act→ack loop passes every scripted disturbance it has
been given, with zero observed hallucinations and zero guardrail
violations, inside its latency budget. The "only if" direction is argued
by construction (§3) and exercised by the adversarial suite, which the
system passes *because* the injected text never reaches an actuator
without gateway validation.
