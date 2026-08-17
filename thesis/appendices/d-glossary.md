# Appendix D — Glossary

**Agent cycle.** One pass of sense → context → predict → validate →
dispatch → ack, recorded as a single decision row with source, latency,
and token usage.

**Anti-short-cycle.** The fan guardrail: ≥ 30 s between state flips,
protecting the motor from chatter. Control-engineering hysteresis
enforced in code against a language model.

**Behavior suite.** A set of scripted disturbance cases replayed through
the real agent path and scored on required/forbidden tools and argument
validity. Four ship: normative, boundary, adversarial, fallback.

**Boundary case.** An eval case placed exactly at (and exactly beside) a
policy threshold — 30.0 vs. 30.1 °C — to catch off-by-one and
inclusive/exclusive drift.

**Broken client.** `BrokenGrokClient`: a model client that always raises,
forcing the fallback path. How the fallback suite proves the degraded
mode without unplugging anything.

**Cycle width.** The number of tool calls dispatched in one agent cycle,
capped at five. The bound on runaway or injected loops.

**Fallback.** The deterministic rule table (SPEC §4.1) that replaces the
model when it fails or times out. Deliberately less capable: never
sirens, never moves the servo.

**Guardrail.** A deterministic rule in `gateway/tools.py` that validates,
clamps, rate-limits, or rejects a predicted tool call before dispatch.
Enforced on the only path to an actuator; parameters are constants the
model cannot influence.

**Hallucination rate.** Fraction of dispatched-intent calls whose tool
name matches no schema. Counted at the guardrail layer; gated at ≤ 0.02
in live runs.

**Heartbeat.** A periodic `POST /sense` with `type: "heartbeat"` — the
device's proof of life and the default agent trigger. Every 300 s in real
time, ~5 s under `--speed 60`.

**Hysteresis.** Separate on/off thresholds (fan: > 30 °C on, < 26 °C off)
with state held between, so noise near a setpoint cannot chatter an
actuator.

**Judge.** The calibrated LLM that scores free-text `log_observation`
rationales against a rubric. Calibrated against human labels; no
authority over pass/fail.

**Mock mode.** Eval runs against `MockGrokClient`, a deterministic
scripted-correct client. Certifies the gateway; free, offline, CI-safe.
Says nothing by itself about live-model behavior — by design.

**Push / poll.** The two command-delivery modes: gateway-initiated
`POST /command` to a reachable device, and device-initiated
`GET /commands` + explicit ack against the durable queue. Deduped by
command ID across both.

**Sanitization boundary.** The coercion of all sensor values to
numeric-or-null before the model or the fallback sees them. Malformed
input is defined as sensor failure; injection by sensor string is
destroyed by the type system.

**Scenario.** A scripted disturbance for the simulator: a duration plus
timestamped keyframes, after which physics drifts naturally. Ships with
`heat_spike`, `night_intruder`, `quiet_afternoon`, `sensor_failure`.

**Snapshot.** One persisted sensor reading: device ID, type, trigger,
sequence, uptime, the four sensor values, actuator states, and raw JSON.

**Staleness.** Explicit device-liveness derivation from last-seen time,
shown on the dashboard. A silent device is a visible device.

**Trust boundary.** The line between the gateway (trusted) and the model
(untrusted). Every safety property is implemented on the trusted side.
