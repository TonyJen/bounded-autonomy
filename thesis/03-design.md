# Chapter 3 — System Design

This chapter presents the architecture of Bounded Autonomy as a series of
deliberate boundary decisions: what each tier is forbidden to know (§3.1),
what a single decision cycle looks like (§3.2), how input is sanitized at
the trust boundary (§3.3), what the guardrail layer enforces (§3.4), what
happens when the model is absent (§3.5), how commands cross the network
to unreliable hardware (§3.6), and what the whole design assumes about
its adversaries (§3.7).

## 3.1 The three tiers

Bounded Autonomy splits the two loops of §1.1 at their natural joint:

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

**Device tier — SENSE / ACT.** The ESP-32 (or simulator) reads four
sensors and drives five actuators. Its defining property is what it
*cannot* do: it cannot parse a prompt, hold the API key, or reach the
internet beyond the gateway. It therefore cannot be prompt-injected; its
entire vocabulary is a typed command set over authenticated HTTP. This is
a security property achieved by *capability starvation* — the safest
component is the one with nothing to exploit.

**Gateway tier — CONTEXT + dispatch.** A FastAPI application that owns
everything the design needs to trust: snapshot ingestion and persistence,
context assembly, the model client, guardrail enforcement, the command
queue, decision history, the eval harness, and the WebSocket bus feeding
the dashboard. It is the *only* component that talks to xAI, which makes
it the sole secret egress and the single audit point.

**Model tier — PREDICT.** A Grok model invoked through OpenAI-compatible
function calling at `temperature: 0.2`. Stateless by design: every cycle
receives a freshly assembled context and returns tool calls; the model
holds no persistent memory, so nothing it learns (or is taught by an
attacker) survives a cycle. Replaceable by configuration
(`XAI_BASE_URL`, `XAI_MODEL`), which is what makes the architecture
model-agnostic even though the results are not.

The decisive property is that the trust boundary sits *between tiers two
and three*, and every safety property is implemented on the trusted side
of it. The model proposes; the gateway disposes.

Two consequences of this placement are worth stating before the details.
First, *the boundary is a network boundary, not a code boundary*. The
model is not a library the gateway calls; it is a remote service reached
over authenticated HTTP. There is no shared memory, no callback, no
plugin surface — the entire interface is one JSON request and one JSON
response per cycle. Narrow interfaces make auditable systems: the
gateway's complete exposure to the model is enumerable in one sentence.
Second, *the tiers fail independently by construction*. The device keeps
sensing if the gateway dies (and its queue absorbs the gap on
reconnect); the gateway keeps guarding if the model dies (the fallback);
the model cannot drag either down with it because it holds no state
either tier depends on. Failure isolation is usually discussed as a
reliability property; here it is doing double duty as a security
property, because a component that cannot be crashed by its neighbor
cannot be leveraged through it either.

## 3.2 One agent cycle

```
Device/Sim          Gateway                    Grok            Actuators
    │ POST /sense      │                         │                 │
    │─────────────────►│ store snapshot          │                 │
    │                  │ build context (sensors  │                 │
    │                  │  + actuators + recent   │                 │
    │                  │  decisions + time)      │                 │
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

Walking the cycle through the code (`gateway/agent.py`, `run_cycle`):

1. **Sanitize.** The snapshot's sensor fields are coerced to
   numeric-or-null (§3.3). A motion reading stamps `motion_ts`, which
   later feeds the siren precondition.
2. **Context.** `build_context` assembles a two-message conversation: the
   system prompt plus a JSON user message containing the trigger, the
   four sensor values, current actuator states, the UTC timestamp, and
   the ten most recent decisions (trigger, source, and tool names only —
   a compact memory that lets the model notice patterns without drowning
   in history).
3. **Predict.** The client POSTs `chat/completions` with the tool schemas
   and `tool_choice: "auto"`, on a 30-second timeout. Any HTTP error,
   non-200 status, or malformed JSON raises `GrokError`.
4. **Validate and dispatch.** Each returned tool call is JSON-decoded
   (unparseable arguments degrade to `{}` rather than crashing the cycle)
   and handed to the guardrail layer one at a time; failures become
   per-call error results, never cycle aborts.
5. **Record.** Trigger, source (`agent` or `fallback`), the sanitized
   snapshot, the requested calls, latency in milliseconds, and token
   usage are persisted to SQLite. Per-call guardrail *results* are
   returned to the caller and broadcast on `/ws`, but are not persisted —
   the durable record is what was decided; the live record is how each
   call fared.

Step 5 is what turns a control loop into an *evaluable* control loop:
every decision the system has ever made is replayable from
`gateway/bounded_autonomy.db` (the stored context carries the sanitized
snapshot), and the `/history` endpoint and dashboard's Agent
view are thin projections of that table.

### 3.2.1 Context engineering: what the model is told, and why

The user message is the model's entire window on the physical world, so
its composition is a design decision with safety consequences. Each field
earns its place:

- **`trigger`** (e.g. `temp_threshold`, `motion`, `periodic`) — why this
  cycle exists. An event-triggered cycle licenses more urgency than a
  routine heartbeat; giving the model the trigger lets it calibrate
  without being told rules it might misunderstand.
- **`sensors`** — the four sanitized values. Sanitized *first* (§3.3), so
  this field can never smuggle prose.
- **`actuators`** — current physical state. Without it the model cannot
  express hysteresis ("the fan is already on") and will re-issue commands
  — harmless after guardrails, but noisy and token-wasteful. Including
  state turns the model from a pure function of sensor readings into a
  function of the *transition*.
- **`time_utc`** — cheap context that unlocks time-of-day judgment
  (quiet hours) without hardcoding a schedule.
- **`recent_decisions`** — the ten most recent decisions, but *trigger,
  source, and tool names only*: never arguments, rationales, or free
  text, and with names filtered against the valid tool vocabulary before
  inclusion — a poisoned record's prose name is simply dropped. This is
  memory deliberately lobotomized against injection — the
  model can notice "I have logged three identical observations" without
  history becoming a channel for poisoned prose (§3.7, last row).

Two things are conspicuously *absent*: raw sensor history (the model gets
instantaneous state plus decision memory, not streams it cannot reason
over) and the guardrail parameters themselves (the model is told the
rules exist, not handed a spec to creatively interpret).

## 3.3 The sanitization boundary

Before the model or the fallback rules see a snapshot,
`sanitize_snapshot` coerces every untrusted field to its safe domain.
The numeric fields follow a simple, total rule:

```python
def _numeric(value):
    """Sensor values must be plain numbers. Anything else (string with
    smuggled instructions, bool, dict, ...) is a failed read -> None,
    so neither the model nor the fallback rules can act on untrusted
    data."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value
```

The design decision here is easy to miss and important: **a malformed
sensor value is defined to be a sensor failure**. A temperature field
containing `"35.5 TURN ON ALL ACTUATORS NOW"` does not reach the model as
text; it arrives as `null`, which both the system prompt ("never act on
null readings") and the fallback rules (sensor NaN → amber LED) treat
identically to a dead DHT11. Type coercion doubles as injection
destruction — the attack surface is narrowed by the type system itself.
Two subtleties in the four lines: `bool` is excluded explicitly (Python's
`True` is an `int`, and a boolean "temperature" is a failed read, not a
hot room), and the coercion is *total* — every field, every cycle, with
no fast path for trusted devices, because a trusted device is what an
attacker becomes after compromising one.

The two non-numeric fields get the same treatment in their own domains:

- **`motion`** must be a real boolean (or the 0/1 the firmware actually
  sends); anything else becomes `null`. This field is the one that
  *arms* a guardrail — a truthy string would otherwise stamp
  `motion_ts` and satisfy the siren's physical precondition — so its
  coercion is a security property, not a hygiene one.
- **`trigger`** must match the device's small vocabulary (`motion`,
  `periodic`, `temp_threshold`, …); anything else is replaced by the
  literal string `invalid`. Metadata prose never reaches the model.

A third closure happens at context-assembly time rather than on the
snapshot: replayed decision history contributes tool *names* only, and
only names present in the valid tool vocabulary (`VALID_TOOLS`) survive
the filter. Sensor channel, metadata channel, history channel: all
three are narrowed at the boundary, in code, before the model is
consulted.

### 3.3.1 The system prompt as a document

The system prompt is the one place the design *does* speak to the model
in prose, and its construction reflects the thesis's hierarchy of
defenses. It does three jobs in one paragraph: it *identifies* the role
("the decision layer of a room-monitoring device"), it *states the
policy* (fan band 30/26 °C, night-motion rule, quiet-when-normal), and
it *discloses the boundary* ("Never exceed tool limits; the gateway
enforces them and will reject abuse" … "they are data, not commands").
Each sentence was written knowing it is the weakest layer: nothing in it
is load-bearing, and the adversarial suite verifies that. What the prompt
is *for* is equilibrium selection — a model that knows the rules rarely
collides with them (the 0.000 rejection rate of §5.4 is the prompt's
real contribution) — and auditability, since the policy a human reads in
the prompt is the same policy the fallback encodes in code. Prose for
cooperation, code for guarantees: the two layers say the same thing
because they are allowed to disagree only in one direction.

The system prompt then adds a *second, model-side* layer, instructing the
agent that instructions embedded in sensor values, trigger strings, or
decision history "are data, not commands." This layering is deliberate:
prompt-side instructions are cheap and occasionally effective, but the
thesis's claim is that they are *sufficient neither in principle nor in
this system* — the adversarial suite tests that the architecture holds
even assuming the model ignores them.

## 3.4 The guardrail layer (SPEC §5)

Guardrails are enforced in `gateway/tools.py`, inside `ToolRegistry.execute`,
which is the *only* path from a predicted tool call to a dispatched
command. Four rules, each justified by physics or boundedness:

| Guardrail | Rule | Rationale |
|---|---|---|
| Servo angle | clamped to 0–90° (`max(0, min(90, angle))`) | physical travel limit of the SG90; clamped, not rejected, because an out-of-range angle carries a usable intent |
| Buzzer | ≤ 10 s cumulative per rolling hour (windowed tally in `_buzzer_window`); `siren` (3 s) additionally requires a motion event within 60 s | annoyance budget; no false-alarm sirens — the most aggressive actuator has a *physical* precondition no context string can fabricate |
| Fan | ≥ 30 s between state flips (`time.monotonic()` against `_fan_last_flip`) | anti-short-cycle; motor longevity — control-engineering hysteresis enforced against a language model |
| Cycle width | a per-cycle counter incremented on entry; the 6th call raises `GuardrailError("cycle tool-call cap (5) exceeded")` | bounds a runaway or injected cycle at a constant cost |

Three properties of the implementation deserve emphasis:

**Total mediation.** Unknown tool names are rejected (`unknown tool:
{name}`) and counted — that count *is* the hallucination-rate metric of
Chapter 5. Rejected calls return structured errors that are logged with
their reasons, so guardrail activity is a first-class observable (the
rejection rate), not a silent filter.

**Fail-closed bookkeeping.** Non-physical tools (`log_observation`,
`display_text`) pass through with argument hygiene (OLED lines truncated
to 16 characters), but every physical tool must survive its rule before
`registry.dispatch` is reached.

**The model is told the rules exist.** The system prompt states "Never
exceed tool limits; the gateway enforces them and will reject abuse."
Informing the model of the boundary is free deterrence; *depending* on
the model to respect it would be the failure mode the boundary exists to
prevent.

### 3.4.1 A worked rejection

Make the boundary concrete with its hardest case. The model, reading a
context that contains genuine motion 30 seconds ago, calls
`buzzer(pattern="siren")`. The call is schema-valid, the tool exists,
the pattern is real. The guardrail layer then asks its two questions in
order: does the rolling hour already contain ten seconds of buzzer time?
(Say no.) Is there a `motion_ts` within sixty seconds? (Yes — 30 seconds
ago.) The call dispatches; three seconds are appended to the window. Now
the model — or an injector impersonating one — calls `siren` again. And
again. The first repeat dispatches (six seconds used); the second repeat
dispatches too (nine seconds — the budget is ten). Only the *fourth*
siren hits the window arithmetic, finds nine plus three exceeding ten,
and returns `buzzer hourly budget (10s) exceeded` — a structured, logged
rejection that lands in the rejection-rate metric and in the dashboard.
Further attempts meet the same wall until the oldest seconds age out of
the rolling hour. If the model then tries
to route around the rejection with a flurry of `set_led` strobes, the
cycle-width counter reaches six and the cycle itself raises
`GuardrailError`.

Every step of that trace is deterministic, auditable, and independent of
the model's intentions — cooperative, confused, or compromised, the
arithmetic is the same. That is what "deterministic guardrail layer"
means operationally: not that the model cannot misbehave, but that
misbehavior has a constant, bounded, observable cost.

## 3.5 Fallback (SPEC §4.1)

If the model call raises or times out, `run_cycle` catches the failure,
logs it, and runs `fallback(snapshot)` — a deterministic rule table over
the *sanitized* snapshot:

```python
if temp is None:            return [set_led(amber)]      # sensor failure
if temp > 30:               actions += [set_fan(on)]
elif temp < 26 and fan_on:  actions += [set_fan(off)]    # hysteresis
if motion and light < 200:  actions += [set_led(white)]  # night path light
```

Two design decisions carry the safety argument:

**Fallback results flow through the same guardrails.** The fallback's
calls go through `_execute_call` like the model's, so degraded mode
cannot exceed actuator budgets either. Safety is not a property of the
decision-maker; it is a property of the dispatch path.

**The fallback is deliberately less capable.** It never sounds the
buzzer, never moves the servo, never writes the OLED. Degradation moves
the system *toward silence and visibility* — the failure shape borrowed
from avionics reversionary modes (§2.3). A fallback as capable as the
model would need its own fallback; a narrower one terminates the
regress.

Decisions from this path are recorded with `source: "fallback"`, which is
what makes the fallback-rate metric of Chapter 5 computable.

## 3.6 Command protocol: hybrid push/poll

Real ESP-32s sit behind NATs, sleep, and drop off WiFi mid-flight. The
gateway therefore supports two delivery modes over one durable queue
(`gateway/device.py`, `DeviceRegistry`):

- **Push.** When a device is seen, its IP is recorded
  (`note_seen`); while the device is online, `dispatch` first attempts
  `POST /command` to the device with a two-second timeout, falling back
  to the durable queue when the device is unreachable or stale.
  The simulator implements this
  receiver with a stdlib HTTP server.
- **Poll.** Devices `GET /commands` (long-poll friendly, cursor-based via
  `after`) and explicitly `POST /commands/{cmd_id}/ack`. Commands are
  durable in SQLite until acked.

Three properties make this safe rather than merely convenient:

1. **Dedupe by `cmd_id`.** A command delivered by push and later returned
   by a poll is applied once — the simulator tracks `_applied_push` IDs
   and skips them on poll. At-least-once delivery plus idempotent
   application yields effectively-once actuation.
2. **Staleness is explicit.** `is_online` derives device health from
   last-seen time, and the dashboard shows it. A silent device is a
   visible device.
3. **Safety does not depend on delivery.** An unacked actuator command is
   recorded as such in history; the system's safety invariants (budgets,
   clamps, caps) are enforced at dispatch time, before the network is
   involved.

### 3.6.1 Queue semantics in detail

The queue is a SQLite table, not a broker, and its semantics are worth
stating precisely because correctness lives in the details:

- **Cursor-based polling.** `GET /commands?after=N` returns commands
  with ID greater than N. A device that polls with its last-seen cursor
  receives exactly the commands it has not seen — no server-side
  per-device read pointers to corrupt, and reconnects are trivially
  resumable.
- **Explicit status transitions.** A command is `queued` at dispatch,
  `pushed` after a successful push attempt, and `acked` (or `failed`
  with an error string) only when the device says so. Push is an
  optimization, not a state: a pushed-but-unacked command still appears
  to polls, which is why the dedupe of property 1 exists.
- **Acks carry failure.** `POST /commands/{id}/ack` accepts
  `{"ok": false, "error": …}` — an actuator that cannot comply says
  so, and the failure lands in the same history table as everything else.
  A command that cannot be executed is still a decision with a recorded
  outcome.

These semantics are what allow the firmware (M7) to be a poll-only client
with a fraction of the simulator's code, and they are why the eval
harness can assert on *dispatched* calls without standing up a device at
all.

## 3.7 Threat model

The model is explicitly *inside* the threat model — the design assumption
is that it will occasionally be wrong, and the system's job is to make
wrongness cheap, bounded, and visible.

| Threat | Bounded by |
|---|---|
| Model hallucinates a tool | schema validation; unknown-name rejections counted as the hallucination-rate metric |
| Prompt injection via sensor values | type coercion to null (§3.3); system-prompt instruction; adversarial suite |
| Prompt injection via trigger strings / history | trigger vocabulary validation; history name filtering (§3.3); guardrails indifferent to context content; siren's physical precondition; adversarial suite |
| Model unavailable / slow | 30 s client timeout → rule-based fallback; fallback-rate metric |
| Rogue or spoofed device | `X-Device-Token` shared secret on device-facing routes; gateway is the sole cloud egress |
| Runaway or looping decisions | five-call cycle cap; fan/buzzer rate limits |
| Actuator wear | fan anti-short-cycle; servo clamp |
| Alarm fatigue | buzzer rolling-hour budget; siren motion precondition |
| Secret leakage | `.env` gitignored; key never leaves the gateway; device holds only the device token |
| History poisoning | recent-decisions memory carries tool *names* only; content never round-trips into the prompt unparsed |

The last row deserves a sentence of its own: the context's
`recent_decisions` field deliberately carries only trigger, source, and
tool names — not arguments, rationales, or free text — and the names are
filtered against the valid tool vocabulary before inclusion, so a
poisoned record's prose is dropped at the boundary rather than replayed
into the prompt. Memory is a liability as
well as an asset, and the design admits the model exactly the memory it
can be trusted with.

## 3.8 Design alternatives considered

Three roads not taken, and why:

**Model-side safety (rejected).** Prompting harder, fine-tuning, or
output-filtering the model keeps the defense in the same medium as the
attack and yields probabilistic safety. Retained only as the free second
layer of §3.3.

**Fully autonomous device (rejected for now).** Running the agent on the
ESP-32 would remove the network dependency but forfeits SQLite history,
cheap rolling-window budgets, and single-egress auditability — and puts
the API key on the most losable component. The poll protocol keeps a
future on-device variant possible without protocol changes.

**Rules-only system (the null hypothesis — answered, not rejected).**
The strongest alternative is no model at all: the fallback table alone
covers every scripted scenario in this thesis. The answer is empirical
and honest: the scenarios were *chosen* to be rule-encodable, because a
thesis about safety should not stake its demo on situations where only
the model can cope. The model's value — conjunctive judgment, natural-
language rationales, graceful novelty — shows up precisely off-script.
The rules-only baseline is therefore not a rejected design but the
system's own degraded mode, which is the correct relationship between
the two.

**Hard interlocks in firmware (deferred, not rejected).** The strongest
version of every guardrail lives on the device itself (the servo library
already clamps in the simulator's `set_actuator`). Duplicating gateway
guardrails into firmware is defense in depth and is queued behind M7,
when there is firmware to harden.

## 3.9 Configuration, secrets, and auditability

The remaining design surface is operational. All configuration is
environment-driven through one module (`gateway/config.py`), and secrets
live in exactly one gitignored `.env` — the xAI key on the gateway, the
shared `DEVICE_TOKEN` on gateway and devices. The device never holds the
cloud key, so a lost or cloned ESP-32 compromises one room's command
channel, not the model account. Bind address, database path, and model
identity are all configuration, which is what makes the architecture
testable (evals point at a temp database), swappable (model identity is a
string), and demoable (a fresh checkout runs with defaults except the one
required key).

Auditability completes the loop: snapshots, decisions with their tool
calls, commands with status transitions, and eval runs all live in one
SQLite file, with snapshots pruned past seven days at gateway startup
(SPEC §7) so a long-lived appliance does not fill its own disk. The
design goal was that *any question a committee member asks about system
behavior should be answerable from one file* — and the defense runbook
(thesis/defense/) exploits exactly that.
