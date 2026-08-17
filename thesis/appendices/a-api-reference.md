# Appendix A — API Reference

All routes are served by the gateway (`gateway/app.py`). Device-facing
routes require the `X-Device-Token` header.

## Device-facing

| Method | Path | Purpose |
|---|---|---|
| POST | `/sense` | Submit a sensor snapshot (temp, humidity, light, motion) |
| GET | `/commands` | Poll pending actuator commands |
| POST | `/commands/{cmd_id}/ack` | Acknowledge a executed command |

The device also exposes a receiver on its own HTTP server
(`simulator/device.py`): `POST /command` (push delivery),
`POST /scenario`, `POST /event`.

## Dashboard / operator

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Frontend SPA (if `frontend/dist` is built) |
| GET | `/status` | Current sensors + device online/staleness |
| GET | `/history` | Snapshots + agent decisions (tool calls, tokens, latency) |
| GET | `/health` | Liveness |
| GET | `/docs` | Interactive OpenAPI explorer |
| WS  | `/ws` | Live event bus: snapshots, decisions, actuator state |

## Evals

| Method | Path | Purpose |
|---|---|---|
| POST | `/evals/run` | Trigger an eval run |
| GET | `/evals/run/{run_id}` | Poll a running eval |
| POST | `/evals/record/{run_id}` | Persist a finished run |
| GET | `/evals/history` | Past runs and diffs |

## Simulator control

| Method | Path | Purpose |
|---|---|---|
| POST | `/sim/scenario` | Switch the running simulator's scenario |
| POST | `/sim/event` | Inject a one-off event (e.g., motion burst) |

## Configuration (environment)

| Key | Purpose | Default |
|---|---|---|
| `XAI_API_KEY` | Grok API key (required for live agent) | — |
| `XAI_BASE_URL` | xAI API base | `https://api.x.ai/v1` |
| `XAI_MODEL` | model name | `grok-4.5` |
| `DEVICE_TOKEN` | device shared secret | `dev-token` |
| `GUARDIAN_DB` | SQLite path | `gateway/guardian.db` |
| `GATEWAY_HOST` / `GATEWAY_PORT` | bind address | `0.0.0.0` / `8000` |
