# Chapter 4 — Implementation

## 4.1 Components

| Component | Language / stack | Lines of code* | Role |
|---|---|---:|---|
| `gateway/` | Python 3.12+, FastAPI, Pydantic, SQLite | 1,642 | agent loop, guardrails, memory, API, WS bus |
| `simulator/` | Python (stdlib HTTP + physics model) | 696 | virtual ESP-32 with scenario engine |
| `evals/` | Python, custom runner | 1,186 | behavior suites, scoring, judge, gates |
| `frontend/` | React + TypeScript + Vite | 1,657 | Room / Device / Agent / Evals views |
| `firmware/` | Arduino (ESP-32) | stub (`config.h.example`) | M7 hardware swap-in |

\* Excluding tests and generated assets; counted 2026-08-17.

## 4.2 Gateway

The gateway is a single FastAPI application (`gateway/app.py`, exposed as
`gateway.main:app`) organized into small, individually testable modules:

- `agent.py` — the cycle: load latest snapshot → assemble context → call
  Grok → collect tool calls → hand to guardrails → dispatch → record.
  On client failure it routes through the rule-based fallback instead.
- `tools.py` — tool schemas exposed to the model (`set_fan`, `set_led`,
  `set_servo`, `buzzer`, `log_observation`, …) plus the guardrail
  validators of §3.3.
- `device.py` — the push/poll command queue, ack tracking, and staleness.
- `memory.py` / `db.py` — SQLite persistence for snapshots, decisions,
  and eval runs; history endpoints read from here.
- `events.py` — the WebSocket bus (`/ws`) that streams snapshots and
  decisions to the dashboard live.
- `auth.py` — `X-Device-Token` dependency for device-facing routes.
- `config.py` — environment-driven settings; the only code that reads
  `.env`.

## 4.3 Simulator

Because the target hardware ships late in any build, the device tier has a
software twin: `simulator/device.py` is a virtual ESP-32 with a physics
model (`physics.py` — thermal drift, lamp coupling into the LDR, PIR
motion bursts) and a scripted scenario engine (`simulator/scenarios/`):
`heat_spike`, `night_intruder`, `quiet_afternoon`, `sensor_failure`. A
`--speed N` factor compresses time so a five-minute heartbeat becomes five
seconds, making a full demo cycle watchable. The simulator speaks the
*same* HTTP protocol as the firmware will — the gateway cannot tell the
difference, which is precisely the point: M7 becomes a transport swap, not
a redesign.

## 4.4 Evaluation harness

`evals/runner.py` replays scripted contexts through the real agent path
and scores the resulting tool calls:

- **Modes.** `--mode mock` swaps the xAI client for a deterministic
  `evals/mock_grok.py` (free, offline, CI-safe); `--mode live` calls the
  real model.
- **Suites.** normative (5 cases), boundary (7), adversarial (3),
  fallback (4), plus `--gen N` synthetic labeled cases from
  `gen_cases.py`.
- **Scoring.** required tools present 50% + forbidden absent 30% +
  argument validity 20%; pass ≥ 0.8.
- **Gates.** `--max-hallucination-rate`, `--latency-budget-ms`; any
  failure or gate trip exits nonzero. Runs persist to `evals/results/`
  and are diffed against the previous run.
- **Judge.** `evals/judge.py` scores free-text outputs with an LLM judge
  whose human-label calibration lives in `evals/calibration/`.

## 4.5 Frontend

A React SPA (built by Vite, served by the gateway from `frontend/dist`)
with four views — Room (live simulation), Device (animated SVG board of
the kit: thermometer, light arc, PIR ripple, spinning fan, OLED
typewriter), Agent (decision stream), and Evals (trigger runs, inspect
history) — all fed live over `/ws`. In development, Vite proxies API and
WebSocket traffic to the gateway; without a build, the gateway degrades
gracefully to a pure API.

## 4.6 Engineering process

The system was built milestone-first (M1 gateway+simulator → M6 frontend)
over 64 commits in seven days (2026-08-10 → 2026-08-17), under three
standing disciplines:

1. **TDD** — failing test first; 88 tests now guard the system
   (45 gateway, 17 simulator, 26 evals/acceptance).
2. **Pre-commit gate** (`scripts/install_hooks.ps1`) — every commit runs
   pytest and the mock-mode eval suite; nothing merges red.
3. **Typed, modern Python** — ≥ 3.12, async for I/O, Pydantic models at
   every boundary.

The process matters to the thesis: the guardrail layer and fallback path
were *tested before they were trusted*, and the commit gate means the
safety properties are re-proven on every change.
