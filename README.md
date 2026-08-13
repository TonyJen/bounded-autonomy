# Grok Guardian

**An LLM in the embedded control loop.**

> EMBEDDED:  SENSE → PROCESS → ACT          (in a world of physics)
> LLM AGENT: CONTEXT → PREDICT → TOOL CALL  (in a world of tokens)

A Room Guardian built for the ELEGOO ESP-32 Super Starter Kit. The ESP-32 (or
its software twin, the simulator) senses the physical world and actuates it;
a local FastAPI gateway assembles context and dispatches tool calls; a Grok
LLM decides what should happen via function calling.

## Architecture

```
  PHYSICAL WORLD (or simulator)                GATEWAY (this repo)              CLOUD
 ┌──────────────────────┐              ┌───────────────────────────┐    ┌────────────────┐
 │ DHT11  temp/humidity │              │  POST /sense  ◄── snapshots│    │                │
 │ PIR    motion        │  SENSE       │  GET  /commands ── poll ◄──┼──┐ │  xAI Grok API  │
 │ LDR    light         │─────────────►│  POST /command  ── push ──►┼──┤ │  (predict)     │
 │                      │  WiFi/HTTP   │                           │  │ │                │
 │ SG90   servo (vent)  │              │  agent.py  context → Grok ─┼──┼─►│ chat/completions
 │ DC motor fan         │  ACT         │  tools.py  guardrails      │  │ │  + tools=[]    │
 │ RGB LED / buzzer     │◄─────────────│  device.py push/poll queue │◄──┼─┘  tool_calls    │
 │ OLED   status        │  commands    │  memory.py SQLite          │  │                │
 └──────────────────────┘              │  evals     behavior suite  │    └────────────────┘
        ESP-32 firmware                └───────────────────────────┘
        (or simulator/device.py)                    │
                                          ┌─────────┴──────────┐
                                          │ frontend SPA (M6):  │
                                          │ room / agent / evals│
                                          └────────────────────┘
```

- **Firmware / simulator = SENSE / ACT** — physics only; no LLM knowledge
- **Gateway = CONTEXT + TOOL dispatch** — owns the agent loop, memory, guardrails
- **Grok = PREDICT** — function calling over OpenAI-compatible `chat/completions`

Guardrails (SPEC §5) are enforced in the gateway, never trusted to the model:
servo clamp 0–90°, buzzer ≤10s/hour (siren needs recent motion), fan 30s
anti-short-cycle, ≤5 tool calls per cycle. If Grok is unreachable, rule-based
fallback keeps the room safe (SPEC §4.1).

## Sequence — one agent cycle

```
Device/Sim          Gateway                    Grok            Actuators
    │                  │                         │                 │
    │ POST /sense      │                         │                 │
    │ (35.8°C,motion)  │                         │                 │
    │─────────────────►│ store snapshot          │                 │
    │                  │ build context           │                 │
    │                  │ (sensors+actuators+     │                 │
    │                  │  recent decisions)      │                 │
    │                  │ chat/completions        │                 │
    │                  │────────────────────────►│                 │
    │                  │      tool_calls:        │                 │
    │                  │◄────────────────────────│  PREDICT        │
    │                  │  set_fan(on), log_obs   │                 │
    │                  │ guardrails validate     │                 │
    │                  │ dispatch → queue        │                 │
    │                  │ push /command ──────────┼─────────────────►│ fan ON
    │   (or poll GET /commands + ack)            │                 │
    │◄─────────────────│                         │                 │
    │ POST /commands/<id>/ack                     │                 │
    │─────────────────►│ mark acked, record      │                 │
    │                  │ decision + tokens       │                 │
```

## Quickstart

```powershell
cd D:\Projects\GrokGuardian
python -m venv .venv; .venv\Scripts\pip install -r gateway\requirements.txt
# .env needs XAI_API_KEY / XAI_BASE_URL / XAI_MODEL / DEVICE_TOKEN

# terminal 1 — gateway
.venv\Scripts\python -m uvicorn gateway.main:app --port 8010

# terminal 2 — simulator (virtual ESP-32)
.venv\Scripts\python -m simulator.device --gateway http://localhost:8010 --token <DEVICE_TOKEN> --scenario heat_spike --speed 60

# terminal 3 — behavior evals
.venv\Scripts\python -m evals.runner --mode mock
```

## Frontend (M6 dashboard)

Three views — Room (live gauges), Agent (decision log), Evals (run & results) —
all updated over WebSocket with zero polling.

```powershell
# production: build once, the gateway serves it at http://localhost:8010
cd frontend; npm install; npm run build

# development: Vite dev server at http://localhost:5173
# (proxies /status, /history, /evals, /sim, /ws to the gateway on :8010)
cd frontend; npm run dev
```

Then see **docs/GUIDE.md** for the full user & developer guide.

## Docs

- [docs/PLAN.md](docs/PLAN.md) — design + milestones
- [docs/SPEC.md](docs/SPEC.md) — protocols, schemas, guardrails, acceptance criteria
- [docs/GUIDE.md](docs/GUIDE.md) — new-user + developer guide
- [docs/plans/](docs/plans/) — implementation plans

## Status

M1–M6 complete (gateway, simulator, agent loop, eval suite, WS bus,
frontend SPA — 81 tests).
M5, M7–M8 remaining: cadence polish, real-hardware swap-in, demo.
