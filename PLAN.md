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

## 6. Testing

- **Firmware:** serial bench test per module (read each sensor, fire each actuator)
- **Gateway:** pytest with mocked Grok client — scenario tests
  ("motion while dark → expect `set_led` + `log_observation`"; "35°C → `set_fan`")
- **Integration:** `scripts/demo_loop.py` injects fake snapshots, watches real
  commands reach the device

## 7. Build milestones

| Milestone | Deliverable | Effort |
|---|---|---|
| M0 | Kit assembled, all sensors read on OLED via serial test sketches | ~2h |
| M1 | Firmware POSTs snapshots; gateway ingests + SQLite history | ~3h |
| M2 | Command path: gateway → device → actuators move | ~3h |
| M3 | Grok agent loop live with function calling | ~3h |
| M4 | Hybrid cadence, guardrails, fallback rules | ~2h |
| M5 | Demo polish: `/status` page, scripted demo scenarios | ~2h |

## 8. Cost estimate

Hybrid cadence ≈ 350 calls/day (288 heartbeats + events). At mini-tier
pricing this is cents/day; on full `grok-4` keep heartbeat context small.
Config flag switches heartbeat model independently of event model.

## 9. Repo layout (planned)

```
GrokGuardian/
├── PLAN.md                  # ← this document
├── .env                     # XAI_API_KEY etc. (gitignored)
├── firmware/                # Arduino sketch + modules (M0–M2)
│   └── grok_guardian/
├── gateway/                 # FastAPI app (M1–M4)
│   ├── app.py
│   ├── agent.py
│   ├── tools.py
│   ├── memory.py
│   └── tests/
└── scripts/                 # demo_loop.py, bench tools
```
