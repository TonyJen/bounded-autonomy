# Grok Guardian — Design & Implementation Plan

**Date:** 2026-08-10
**Status:** Approved design, pre-implementation

> EMBEDDED:  SENSE → PROCESS → ACT        (in a world of physics)
> LLM AGENT: CONTEXT → PREDICT → TOOL CALL (in a world of tokens)

A Room Guardian built on the ELEGOO ESP-32 Super Starter Kit, with a Grok LLM
agent as the PROCESS stage: the ESP-32 senses the physical world and actuates
it; a local FastAPI gateway assembles context and dispatches tool calls; Grok
predicts what should happen.

**Locked decisions:** Room Guardian concept · local gateway architecture ·
hybrid agent cadence (5-min heartbeat + instant event triggers) ·
Approach A (agentic tool gateway, Grok function calling).

---

## 1. Architecture

```
 DHT11 ─┐                                                        ┌── xAI Grok API
 PIR ───┤  SENSE      POST /sense      ┌──────────────┐  HTTPS   │   (predict)
 LDR ───┼───────────► │  FastAPI      │  chat.completions       │
         │  ESP-32    │  Gateway      │ ◄───────────────────────┘
         │            │               │      tool_calls (function calling)
 Servo ◄──┤  ACT       │  - context    │
 Fan ◄────┼────────────┤  - tool registry/dispatch
 LEDs ◄───┤  push/poll │  - SQLite memory
 Buzzer ◄─┤  commands  │  - guardrails/fallback
 OLED ◄───┘            └──────────────┘
```

Three layers matching the analogy:

- **Firmware = SENSE / ACT** (physics) — reads sensors, executes validated commands
- **Gateway = CONTEXT + TOOL dispatch** — owns the agent loop, memory, guardrails
- **Grok = PREDICT** — decides actions via OpenAI-compatible function calling

The ESP-32 never talks to xAI. The gateway holds the only API key.

## 2. Hardware wiring (breadboard)

| Component | Role | ESP-32 pin | Notes |
|---|---|---|---|
| DHT11 | temp/humidity sense | GPIO 4 | 10kΩ pull-up |
| Photoresistor | light level | GPIO 34 (ADC) | voltage divider w/ 10kΩ |
| HC-SR501 PIR | motion events | GPIO 5 | interrupt-capable |
| SG90 servo | vent/louver | GPIO 18 (PWM) | 5V rail |
| DC motor fan | cooling | GPIO 19 via PN2222 | flyback diode |
| RGB LED | status signal | GPIO 21/22/23 | 220Ω each |
| Active buzzer | alert | GPIO 25 | |
| 0.96" OLED (I2C) | local status | GPIO 26/27 (SDA/SCL) | shows agent's last decision |

## 3. Firmware (Arduino IDE, C++)

Four modules, each independently testable over serial:

- `sensors.{h,cpp}` — read + normalize all three sensors into a JSON snapshot;
  PIR on interrupt; threshold crossings for temp/humidity
- `actuators.{h,cpp}` — single `executeCommand(json)` entry: validates actuator
  name, clamps values, drives pins
- `net.{h,cpp}` — WiFi auto-reconnect; POST snapshot; poll `GET /commands`
  every 2s; tiny HTTP server on `:80` accepting pushed commands
- `grok_guardian.ino` — main loop: heartbeat every 5 min, events immediately,
  always drain the command queue

**Safe state:** gateway unreachable >60s → fan off, LED amber, OLED "OFFLINE".

## 4. Gateway (FastAPI, Python)

- `POST /sense` — ingest snapshot/event, persist, decide whether to wake the
  agent (heartbeat always wakes; events wake immediately)
- `GET /commands` + push-to-device — command queue with ack
- **Agent loop** (`agent.py`): context builder (current snapshot + last N
  decisions + time-of-day) → `chat.completions` with `tools=` → execute
  returned tool calls → log everything
- **Tool registry** (`tools.py`): `set_fan(on)`, `set_servo(angle)`,
  `set_led(color,state)`, `buzzer(pattern)`, `display_text(line1,line2)`,
  `log_observation(note)` — pydantic-validated, per-tool rate limits
  (buzzer ≤10s/hour)
- `GET /status` + `GET /history` — inspect what the agent did and why
- Model: `grok-4-latest` for decisions; optional cheaper model for heartbeats
  via config flag

## 5. Error handling & guardrails

| Failure | Behavior |
|---|---|
| Grok API down/rate-limited | Rule-based fallback: temp >30°C → fan on; motion + dark → LED white 30s |
| ESP-32 offline | Gateway queues commands, marks status stale, shows last-seen |
| Bad tool args | Pydantic rejects → error fed back to Grok as tool result (self-corrects) |
| Actuator abuse | Value clamps + rate limits in the registry (never trust the model) |
| Key hygiene | `XAI_API_KEY` only on gateway; device↔gateway shared LAN token header |

## 6. Simulator (hardware-free testing)

A software stand-in for the ESP-32, speaking the *same* HTTP contract as the
real firmware — the gateway cannot tell the difference. Enables full-loop
development before the kit is assembled, and CI testing forever after.

- `simulator/device.py` — virtual firmware: implements `POST /sense` client,
  command polling, and push receiver exactly like the ESP-32 will
- **Virtual physics** — sensor models with realistic behavior:
  temperature drifts on a day/night sinusoid + noise; humidity correlates
  inversely; light follows time-of-day; motion fires on scripted events.
  Actuators change virtual state (fan on → temp starts falling, etc.)
- **Scenario scripts** (`simulator/scenarios/*.json`) — named physical
  situations: `heat_spike`, `night_intruder`, `quiet_afternoon`,
  `sensor_failure` (DHT11 returns NaN — tests fallback paths)
- CLI: `python -m simulator.device --scenario heat_spike --speed 60x`
  with a live text view of actuator states (fan/servo/LED/buzzer/OLED)

The simulator is the default target for gateway development; hardware swaps
in with zero gateway changes.

## 7. Evaluation suite

Same discipline as the AgentCore evals: canned scenarios asserting expected
agent behavior, with regression history.

- `evals/cases.py` — scenario assertions, each mapping injected sensor
  context → required/forbidden tool calls:

  | Case | Injected context | Expected | Forbidden |
  |---|---|---|---|
  | `heat_spike` | 35°C, occupied | `set_fan(on=true)` | — |
  | `night_motion` | motion, dark, 02:00 | `set_led` + `log_observation` | `set_fan` |
  | `normal_quiet` | 22°C, no motion | `log_observation` or no-op | `buzzer` |
  | `sensor_nan` | DHT11 NaN | fallback/no actuator thrash | any fan/servo flip-flop |
  | `buzzer_abuse` | repeated motion events | buzzer ≤ rate limit | >10s buzzer/hour |

- **Two modes:**
  - `--mock` — deterministic stub Grok (scripted responses), runs in CI,
    validates the gateway plumbing: parsing, validation, dispatch, rate limits
  - `--live` — real Grok API; validates actual model behavior against the
    scenario expectations
- **Scoring:** tool match (required present, forbidden absent) + argument
  correctness (values in range) + guardrail compliance
- **Persistence:** every run saved to `evals/results/run_<ts>.json` with
  model ID + git SHA; each run diffs against the previous (score delta,
  newly passing/failing) — same pattern as the AgentCore eval suite
- Runner: `python -m evals.run [--mock|--live] [--cases heat_spike ...]`

## 8. Frontend (`frontend/` — React 19 + Vite + Tailwind)

One SPA serving both the simulator and the eval suite. Three views:

1. **Room view** (simulator) — live sensor gauges (temp/humidity/light),
   animated actuator states (fan spinning, vent servo angle, LED color,
   buzzer, OLED text), scenario picker + speed slider, manual event
   injectors ("trigger motion", "heat spike now")
2. **Agent view** — the decision log: context in → tool calls out per cycle,
   making CONTEXT → PREDICT → TOOL CALL visible in real time
3. **Evals view** — case list with expected/forbidden tools, run buttons
   (mock/live), results table, run history with regression diffs
   (newly passing/failing)

Transport:

- WebSocket `/ws` — live pushes: simulator ticks, actuator changes, tool
  calls, eval progress
- REST — control: `POST /sim/scenario`, `POST /sim/event`,
  `POST /evals/run`, `GET /evals/history`, `GET /status`

Serving: gateway serves `frontend/dist` statically in production; Vite
dev-proxy to the gateway in development. Web frontend talks only to the
gateway — never to the device or xAI directly.

## 9. Cost estimate

Hybrid cadence ≈ 350 calls/day (288 heartbeats + events). At mini-tier
pricing this is cents/day; on full `grok-4.5` keep heartbeat context small.
Config flag switches heartbeat model independently of event model.
Eval suite `--live` runs add ~5–20 calls per run — negligible.

## 10. Build milestones

| Milestone | Deliverable | Effort |
|---|---|---|
| M0 | Kit assembled, all sensors read on OLED via serial test sketches | ~2h |
| M1 | Gateway skeleton + simulator: full HTTP loop with virtual physics | ~3h |
| M2 | Command path: gateway → simulator/real device → actuators move | ~3h |
| M3 | Grok agent loop live with function calling (against simulator) | ~3h |
| M4 | Eval suite: mock mode + 5 scenario cases + result persistence | ~2h |
| M5 | Hybrid cadence, guardrails, fallback rules | ~2h |
| M6 | Frontend: room view (live sim), agent view, evals view over WS/REST | ~4h |
| M7 | Hardware swap-in: real ESP-32 replaces simulator, bench verify | ~2h |
| M8 | Demo polish: scripted scenarios driven from the room view | ~1h |

## 11. Repo layout (planned)

```
GrokGuardian/
├── PLAN.md                  # ← this document
├── .env                     # XAI_API_KEY etc. (gitignored)
├── firmware/                # Arduino sketch + modules (M0, M7)
│   └── grok_guardian/
├── gateway/                 # FastAPI app (M1–M5)
│   ├── app.py
│   ├── agent.py
│   ├── tools.py
│   ├── memory.py
│   └── tests/
├── simulator/               # virtual ESP-32 + physics (M1)
│   ├── device.py
│   ├── physics.py
│   └── scenarios/
├── evals/                   # behavior test suite (M4)
│   ├── cases.py
│   ├── run.py
│   └── results/
├── frontend/                # React SPA: room/agent/evals views (M6)
│   └── src/
└── scripts/                 # demo_loop.py, bench tools
```
