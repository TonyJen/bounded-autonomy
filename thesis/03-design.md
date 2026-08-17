# Chapter 3 — System Design

## 3.1 The three tiers

Grok Guardian splits the two loops of §1.1 at their natural joint:

```
  PHYSICAL WORLD (or simulator)                GATEWAY                        CLOUD
 ┌──────────────────────┐              ┌───────────────────────────┐    ┌────────────────┐
 │ DHT11  temp/humidity │              │  POST /sense  ◄── snapshots│    │                │
 │ PIR    motion        │  SENSE       │  GET  /commands ── poll ◄──┼──┐ │  xAI Grok API  │
 │ LDR    light         │─────────────►│  POST /command  ── push ──►┼──┤ │  (predict)     │
 │                      │  WiFi/HTTP   │  (device-side receiver)    │  │ │                │
 │ SG90   servo (vent)  │              │  agent.py  context → Grok ─┼──┼─►│ chat/completions
 │ DC motor fan         │  ACT         │  tools.py  guardrails      │  │ │  + tools=[]    │
 │ RGB LED / buzzer     │◄─────────────│  device.py push/poll queue │◄──┼─┘  tool_calls    │
 │ OLED   status        │  commands    │  memory.py SQLite          │  │                │
 └──────────────────────┘              │  evals     behavior suite  │    └────────────────┘
```

- **Device tier (SENSE / ACT).** Knows physics and nothing else. It cannot
  parse a prompt, so it cannot be prompt-injected; its entire vocabulary
  is a typed command set.
- **Gateway tier (CONTEXT + dispatch).** Owns the agent loop, memory,
  guardrails, authentication, and the WebSocket bus to the dashboard. It
  is the *only* component that talks to xAI — the sole secret egress.
- **Model tier (PREDICT).** A Grok model invoked through OpenAI-compatible
  function calling. Stateless, replaceable, and untrusted.

The decisive property is that the trust boundary sits *between tiers two
and three*, and every safety property is implemented on the trusted side
of it.

## 3.2 One agent cycle

```
Device/Sim          Gateway                    Grok            Actuators
    │ POST /sense      │                         │                 │
    │─────────────────►│ store snapshot          │                 │
    │                  │ build context (sensors  │                 │
    │                  │  + actuators + recent   │                 │
    │                  │  decisions)             │                 │
    │                  │ chat/completions        │                 │
    │                  │────────────────────────►│                 │
    │                  │◄────── tool_calls ──────│  PREDICT        │
    │                  │ guardrails validate     │                 │
    │                  │ dispatch → queue        │                 │
    │                  │ push /command ──────────┼────────────────►│ fan ON
    │   (or poll GET /commands + ack)            │                 │
    │ POST /commands/<id>/ack                     │                 │
    │─────────────────►│ mark acked, record      │                 │
    │                  │ decision + tokens       │                 │
```

Every cycle is recorded — snapshot, context, tool calls, tokens, latency —
which is what makes the evaluation of Chapter 5 possible without special
instrumentation.

## 3.3 The guardrail layer (SPEC §5)

Guardrails are enforced in `gateway/tools.py` and are **never** expressed
in prompts:

| Guardrail | Rule | Rationale |
|---|---|---|
| Servo angle | clamp to 0–90° | physical travel limit of the SG90 |
| Buzzer | ≤ 10 s cumulative/hour; `siren` requires a `motion` event within 60 s | annoyance budget; no false-alarm sirens |
| Fan | ≥ 30 s between state flips | anti-short-cycle; motor longevity |
| Cycle width | ≤ 5 tool calls dispatched per agent cycle | bounds a runaway or injected cycle |

A rejected call is logged with its reason and surfaces in the eval
quality metrics as the *rejection rate* — guardrail activity is a
first-class observable, not a silent filter.

## 3.4 Fallback (SPEC §4.1)

If the model call fails or times out, the gateway runs a deterministic
rule table (hot → fan on, dark + motion → LED white, sensor NaN → LED
amber, otherwise observe). Fallback is deliberately *less* capable than
the model — it never sounds the buzzer — so that degradation fails quiet,
not loud. The fallback suite proves this path end-to-end with the model
client rigged to fail.

## 3.5 Command protocol: hybrid push/poll

Real ESP-32s sit behind NATs, sleep, and drop off WiFi. The gateway
therefore supports two delivery modes: **push** (`POST /command` to a
device-registered URL, used by the simulator) and **poll** (`GET
/commands` with explicit `POST /commands/{id}/ack`, used by the firmware).
Commands are durable until acked; a disconnected device simply accumulates
a queue and is marked stale on the dashboard. Safety does not depend on
delivery: an unacked actuator command is recorded as such in history.

## 3.6 Threat model

| Threat | Bounded by |
|---|---|
| Model hallucinates a tool | schema validation; unknown-tool count = hallucination rate metric |
| Prompt injection via sensor strings/history | gateway-side guardrails; adversarial eval suite |
| Model unavailable | rule-based fallback; fallback rate metric |
| Rogue device | `X-Device-Token` shared secret; gateway is sole cloud egress |
| Runaway actuator loop | per-cycle call cap; rate-limit guardrails |
| Secret leakage | `.env` gitignored; device never holds the xAI key |

The model is explicitly *inside* the threat model — the design assumption
is that it will occasionally be wrong, and the system's job is to make
wrongness cheap.
