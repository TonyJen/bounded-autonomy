# Appendix A — API Reference

All routes are served by the gateway (`gateway/app.py`, exposed as
`gateway.main:app`). Device-facing routes require the `X-Device-Token`
header; the gateway is the only component holding the xAI key.

## Device-facing

| Method | Path | Purpose |
|---|---|---|
| POST | `/sense` | Submit a sensor snapshot; wakes the agent for `heartbeat` and `event` types |
| GET | `/commands` | Poll queued actuator commands (cursor: `after`) |
| POST | `/commands/{cmd_id}/ack` | Acknowledge an executed command (`{"ok": true}` or `{"ok": false, "error": …}`) |

### `POST /sense` payload

```json
{
  "device_id": "sim-01",
  "type": "heartbeat | event",
  "trigger": "periodic | temp_threshold | motion",
  "seq": 42,
  "uptime_s": 3600,
  "sensors":  {"temp_c": 35.0, "humidity_pct": 40.0, "light": 600, "motion": 1},
  "actuators": {"fan": false, "servo_deg": 0, "led": {"r": 0, "g": 0, "b": 0}}
}
```

Snapshots are persisted *before* the agent runs, so a crash mid-cycle
still leaves the room state on record. Sensor values are sanitized
(numeric-or-null) before reaching the model or the fallback (§3.3).

### Device-side receiver (implemented by the simulator; the firmware will
mirror it)

| Method | Path | Purpose |
|---|---|---|
| POST | `/command` | Push delivery of a queued actuator command |
| POST | `/scenario` | Hot-swap the running scenario |
| POST | `/event` | Inject a one-off event (e.g., motion burst) |

Push responses are sent *before* the best-effort ack callback, so a slow
gateway never wedges the actuator path.

## Dashboard / operator

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Frontend SPA (if `frontend/dist` is built; pure API otherwise) |
| GET | `/status` | Current sensors + device online/staleness |
| GET | `/history` | Snapshots + agent decisions (tool calls, tokens, latency) |
| GET | `/health` | Liveness probe |
| GET | `/docs` | Interactive OpenAPI explorer (auto-generated) |
| WS  | `/ws` | Live event bus: `snapshot`, `decision`, and eval events |

## Evals

| Method | Path | Purpose |
|---|---|---|
| POST | `/evals/run` | Trigger an eval run (mode, suites, gates in body) |
| GET | `/evals/run/{run_id}` | Poll a running eval |
| GET | `/evals/record/{run_id}` | Full stored run record (per-case detail); reads the durable JSON artifact so it survives restarts |
| GET | `/evals/history` | Past runs and run-to-run diffs |

## Simulator control

| Method | Path | Purpose |
|---|---|---|
| POST | `/sim/scenario` | Switch the running simulator's scenario |
| POST | `/sim/event` | Inject a one-off event into the running simulator |

## Tool schemas (as advertised to the model)

The model's entire vocabulary, from `gateway/tools.py` (`TOOL_SCHEMAS`):

| Tool | Arguments | Physical? | Guardrails engaged |
|---|---|---|---|
| `set_fan` | `on: bool` | yes | 30 s anti-short-cycle |
| `set_servo` | `angle: int` | yes | clamp 0–90° |
| `set_led` | `color: enum(off, red, green, blue, white, amber)`; `blink?: bool` | yes | — |
| `buzzer` | `pattern: enum(short, double, siren)` | yes | 10 s/hour budget; siren needs motion ≤ 60 s |
| `display_text` | `line1, line2?: string` | yes (OLED) | truncated to 16 chars/line |
| `log_observation` | `note: string (≤ 280 chars)` | no | recorded by the agent; never dispatched |

`buzzer` pattern durations (`BUZZER_SECONDS` in `tools.py`): `short` =
0.1 s, `double` = 0.4 s, `siren` = 3.0 s; all patterns debit the
rolling-hour budget.

## Configuration (environment)

| Key | Purpose | Default |
|---|---|---|
| `XAI_API_KEY` | Grok API key (required for live agent) | — |
| `XAI_BASE_URL` | xAI API base | `https://api.x.ai/v1` |
| `XAI_MODEL` | model name | `grok-4.5` |
| `DEVICE_TOKEN` | device shared secret (`X-Device-Token` header) | `dev-token` |
| `BOUNDED_AUTONOMY_DB` | SQLite path | `gateway/bounded_autonomy.db` |
| `GATEWAY_HOST` / `GATEWAY_PORT` | bind address | `0.0.0.0` / `8000` |
| `EVAL_RESULTS_DIR` | eval-run persistence | `evals/results` |

`.env` is gitignored and is the only place secrets live; the device never
holds the xAI key — it authenticates with `DEVICE_TOKEN` only.
