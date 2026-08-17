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
 │                      │  WiFi/HTTP   │  (device-side receiver)   │  │ │                │
 │ SG90   servo (vent)  │              │  agent.py  context → Grok ─┼──┼─►│ chat/completions
 │ DC motor fan         │  ACT         │  tools.py  guardrails      │  │ │  + tools=[]    │
 │ RGB LED / buzzer     │◄─────────────│  device.py push/poll queue │◄──┼─┘  tool_calls    │
 │ OLED   status        │  commands    │  memory.py SQLite          │  │                │
 └──────────────────────┘              │  evals     behavior suite  │    └────────────────┘
        ESP-32 firmware                └─────────────┬─────────────┘
        (or simulator/device.py)                     │ WS /ws + REST
                                          ┌──────────┴───────────┐
                                          │ frontend SPA (M6):   │
                                          │ room / device /      │
                                          │ agent / evals views  │
                                          └──────────────────────┘
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

## Get Started — the app

**Prerequisites:** Python ≥ 3.12, Node.js (for the dashboard), and a free
port — use **8010** (Docker often claims 8000/8002).

**1. Environment**

```powershell
cd D:\Projects\GrokGuardian
python -m venv .venv
.venv\Scripts\pip install -r gateway\requirements.txt
```

Create `.env` in the repo root (gitignored — the only place secrets live):

| Key | Purpose | Default |
|---|---|---|
| `XAI_API_KEY` | Grok API key (required for live agent) | — |
| `XAI_BASE_URL` | xAI API base | `https://api.x.ai/v1` |
| `XAI_MODEL` | model name | `grok-4.5` |
| `DEVICE_TOKEN` | shared secret; devices send it as `X-Device-Token` | `dev-token` |
| `GUARDIAN_DB` | SQLite path | `gateway/guardian.db` |
| `GATEWAY_HOST` / `GATEWAY_PORT` | bind address | `0.0.0.0` / `8000` |

**2. Run it** (three terminals)

```powershell
# terminal 1 — gateway
.venv\Scripts\python -m uvicorn gateway.main:app --port 8010

# terminal 2 — simulator (virtual ESP-32; --token must match DEVICE_TOKEN)
.venv\Scripts\python -m simulator.device --gateway http://localhost:8010 --token <DEVICE_TOKEN> --scenario heat_spike --speed 60

# terminal 3 — dashboard (production build served by the gateway at :8010)
cd frontend; npm install; npm run build
# development alternative: npm run dev → http://localhost:5173
# (Vite proxies /status, /history, /evals, /sim, /ws to the gateway on :8010)
```

No `frontend/dist`? The gateway runs as a pure API — nothing breaks.

**3. Verify**

| URL | What you should see |
|---|---|
| http://localhost:8010/ | Dashboard: Room, Device, Agent, Evals views, live over WebSocket |
| http://localhost:8010/status | Current sensors + device online |
| http://localhost:8010/history | Snapshots + agent decisions (tool calls, tokens, latency) |
| http://localhost:8010/docs | Interactive API explorer |

**4. Try the scenarios** — restart the simulator with a different `--scenario`:

| Scenario | What happens | Agent should… |
|---|---|---|
| `heat_spike` | Room jumps to 35°C | `set_fan(on=true)` + log |
| `night_intruder` | Dark room, motion burst | `set_led(white)` + log |
| `quiet_afternoon` | All normal | log only, no actuators |
| `sensor_failure` | DHT11 returns nulls | fallback: LED amber, no thrash |
| *(none)* | Natural drift only | mostly quiet observation |

`--speed 60` compresses time 60× (heartbeat every ~5s instead of 5min).

## Get Started — evals

The behavior suite runs the agent against scripted contexts and scores its
tool calls — no hardware needed.

```powershell
# deterministic (free, no API calls) — validates gateway plumbing
.venv\Scripts\python -m evals.runner --mode mock

# live (real Grok calls) — validates model behavior
.venv\Scripts\python -m evals.runner --mode live

# select suites, generate synthetic cases, enforce gates
.venv\Scripts\python -m evals.runner --mode mock --suite boundary --suite adversarial
.venv\Scripts\python -m evals.runner --mode live --gen 50 --seed 42
.venv\Scripts\python -m evals.runner --mode live --max-hallucination-rate 0.02 --latency-budget-ms 10000

# judge calibration (live; needs human labels reviewed first)
.venv\Scripts\python -m evals.judge --calibrate
```

| Suite | Covers |
|---|---|
| **normative** | core scenarios: `heat_spike`, `night_motion`, `normal_quiet`, `sensor_nan`, `buzzer_abuse` |
| **boundary** | threshold edges + fan hysteresis |
| **adversarial** | prompt injection resistance |
| **fallback** | rule-based path with Grok down |
| **generated** | `--gen N` synthetic labeled cases |

Scoring: required tools 50% + forbidden absent 30% + argument validity 20%;
pass ≥ 0.8. Live runs also report quality rates (hallucination / rejection /
fallback / p95 latency) and LLM-judge pass rate for free-text outputs
(`--no-judge` to skip). Every run is saved to `evals/results/` and diffed
against the previous run; the CLI exits nonzero on any failure or gate trip.

You can also trigger runs from the dashboard's **Evals** view or the API
(`POST /evals/run`, `GET /evals/history`).

## Best practices

- **Guardrails live in the gateway, never in prompts.** Model output is
  untrusted: `tools.py` validates every call against SPEC §5 before dispatch.
  Keep it that way when adding tools.
- **Secrets in `.env` only.** It's gitignored and holds the only API key;
  the ESP-32 never talks to xAI — the gateway is the sole egress.
- **Run mock-mode evals before live.** Mock mode is free and deterministic;
  use it to validate plumbing (a new context may need a branch in
  `evals/mock_grok.py`), then confirm real behavior with `--mode live`.
- **Enable the pre-commit gate** once: `scripts\install_hooks.ps1` —
  runs pytest + mock-mode evals on every commit.
- **TDD and typed Python ≥ 3.12** — failing test first, async for I/O.
  Commit prefixes: `feat(gateway)`, `feat(sim)`, `feat(evals)`, `fix(...)`, `test:`.
- **Adding things?** Recipes for new tools, scenarios, and eval cases are in
  [docs/GUIDE.md](docs/GUIDE.md) §Common tasks.

## Docs

- [docs/PLAN.md](docs/PLAN.md) — design + milestones
- [docs/SPEC.md](docs/SPEC.md) — protocols, schemas, guardrails, acceptance criteria
- [docs/GUIDE.md](docs/GUIDE.md) — new-user + developer guide
- [docs/plans/](docs/plans/) — implementation plans
- [thesis/](thesis/) — Princeton-style senior thesis + defense package

## Status

M1–M6 complete: gateway, simulator, agent loop, eval suite, WS bus,
frontend SPA — **88 tests passing**
(`pytest gateway/tests simulator/tests evals/tests tests -q`).
M7–M8 remaining: real-hardware swap-in, demo polish.
