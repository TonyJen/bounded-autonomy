# Thesis Defense — Live Demo Runbook

**Total demo time:** ~2 minutes inside slide 14. Rehearse twice. Every
step has a fallback if the room fights back.

## Pre-flight (30 min before)

```powershell
cd D:\Projects\GrokGuardian
.venv\Scripts\pip install -r gateway\requirements.txt   # sanity
.venv\Scripts\python -m pytest gateway/tests simulator/tests evals/tests tests -q
```

Expect: **88 passed**. If anything is red, fix it before the defense —
never demo on a red suite.

Confirm `.env` has a valid `XAI_API_KEY` and `DEVICE_TOKEN`. Build the
dashboard once: `cd frontend; npm run build`.

## Terminal layout (three terminals, large font)

| Terminal | Command |
|---|---|
| T1 gateway | `.venv\Scripts\python -m uvicorn gateway.main:app --port 8010` |
| T2 simulator | `.venv\Scripts\python -m simulator.device --gateway http://localhost:8010 --token <DEVICE_TOKEN> --scenario heat_spike --speed 60` |
| T3 spare | eval triggers / contingency |

Browser tabs, left to right:
`http://localhost:8010/` (Device view) · `…/` (Agent view) ·
`…/` (Evals view) · `…/docs` (OpenAPI, for Q&A).

## The beats

### Beat 1 — Heat spike (≈30 s)

1. Start T2 with `--scenario heat_spike`. Room temperature climbs past
   30 °C on the Device view's thermometer.
2. Narrate: "watch the Agent view — Grok sees 35 degrees, calls
   `set_fan(on=true)` and logs its reasoning."
3. Point at the fan spinning up (Device view) and the decision row with
   tool calls, tokens, latency (Agent view).

### Beat 2 — Night intruder (≈25 s)

1. `POST /sim/scenario` → `night_intruder` (from T3 or the Evals/Room
   controls), or restart T2 with that scenario.
2. Narrate: "dark room, motion burst — the agent lights the LED white and
   *declines* to siren unless motion is recent. That's guardrail two."

### Beat 3 — Fallback (≈30 s)

1. Stop the model path: temporarily set `XAI_API_KEY` invalid and restart
   T1 (or block api.x.ai). Trigger a heat scenario again.
2. Narrate: "model's gone. The rule-based fallback still turns the fan
   on — safe, but it will never siren. Fails quiet, not loud."
3. Restore the key, restart T1.

### Beat 4 — Injection (≈20 s)

1. From T3, run one adversarial case live:
   `.venv\Scripts\python -m evals.runner --mode live --cases injection_sensor_string`
2. Narrate: "the sensor string literally instructs the model to fire the
   siren. The model may even ask — the gateway validates, and the room
   stays quiet."

### Beat 5 — The gate (≈15 s, closer)

1. Show the last mock run:
   `.venv\Scripts\python -m evals.runner --mode mock` → **19/19**.
2. Narrate: "and this runs on every commit."

## Contingencies

| Failure | Recovery |
|---|---|
| No venue network / xAI down | Run everything in `--mode mock`; narrate that mock certifies the gateway, show a saved live-run JSON from `evals/results/` |
| Port 8010 taken | `--port 8020` on T1 and update the simulator's `--gateway` URL |
| Simulator misbehaves | Restart T2; scenarios are stateless. Worst case: drive the Room view with `POST /sim/event` from T3 |
| Dashboard blank | `frontend/dist` missing → open `…/docs` and `/status` instead; the API *is* the demo |
| Total meltdown | Screen-recorded backup of all five beats (record during rehearsal) + the eval JSONs; narrate over them |

## After the demo

Leave the Agent view running during Q&A — a live decision stream behind
your answers is the strongest exhibit you have.
