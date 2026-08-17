# Chapter 1 — Introduction

## 1.1 Two loops

Embedded systems and LLM agents are both loops, but they loop over
different worlds:

```
EMBEDDED:  SENSE → PROCESS → ACT          (in a world of physics)
LLM AGENT: CONTEXT → PREDICT → TOOL CALL  (in a world of tokens)
```

The embedded loop is old, well understood, and boring by design. A
thermostat reads a thermistor, compares it to a setpoint, drives a relay,
and repeats — millions of times, for years, with no surprises. Its
PROCESS stage is deliberately simple because its outputs are physical and
its failures are too: a furnace that rapid-cycles destroys itself; a
sump pump that misreads a float switch floods a basement. Decades of
control engineering exist to make this loop predictable — hysteresis
bands, rate limits, watchdog timers, fail-safe defaults — and nearly all
of it assumes the decision-maker is a fixed function of its inputs.

The LLM agent loop is new, expressive, and untrusted by default. Its
PREDICT stage can reason over rich context, weigh trade-offs no rule
table anticipates, act through typed tools, and explain itself in plain
language. It can also hallucinate a tool that does not exist, obey an
instruction smuggled into its input, time out mid-decision, or cost money
per thought. The two loops are mirror images: one is safe because it is
simple, the other is useful because it is not.

This thesis joins the loops. Grok Guardian is a room guardian: an ESP-32
microcontroller — or its software twin, a physics simulator — senses
temperature, humidity, motion, and light; a Grok large language model
decides what the room should do about it; actuators — a fan, a vent
servo, an RGB LED, a buzzer, an OLED display — carry the decision out.
The research question is not whether the model is *clever*. It is whether
the model can be *safe inside the loop*: bounded, observable, and
gracefully removable.

## 1.2 Thesis statement

> **An LLM can occupy the decision stage of a physical control loop safely
> if and only if prediction is separated from actuation by a deterministic
> guardrail layer that the model cannot influence, and if a non-LLM
> fallback preserves safe behavior when the model is absent.**

Three phrases in that sentence carry the weight of the whole thesis, and
each maps to a layer of the system:

1. **"Deterministic guardrail layer."** Every actuator-facing decision
   passes through code — not prompts, not model-side alignment, not
   vibes — that validates, clamps, rate-limits, or rejects it. The layer
   is small (one module, four rules) and total (there is no path from
   prediction to actuation that bypasses it).
2. **"That the model cannot influence."** The guardrails' parameters —
   the 90° servo limit, the ten-second buzzer budget, the thirty-second
   fan window, the five-call cycle cap — are constants in gateway code.
   Nothing the model can emit, and nothing an attacker can smuggle into
   the model's context, can widen them.
3. **"A non-LLM fallback."** When the model is unreachable, a rule table
   keeps the room in a safe state. It is deliberately narrower than the
   model's authority, so failure moves the system *toward* silence.

### 1.2.1 Reading the "if and only if"

The biconditional is a strong claim and deserves an honest parsing. The
forward direction — *with* such a layer and fallback, an LLM can be safe
in the loop — is the direction a single system can actually demonstrate,
and this thesis demonstrates it by construction and evaluation. The
reverse direction — *without* them, it cannot be safe — is not provable
by one system; it is argued instead by elimination across the design
space: prompt-side defenses are influenceable by the attacker (§2.2),
model-side training cannot bind physical parameters it cannot see, and a
system with no fallback has no defined behavior under outage. Each
alternative fails for a structural reason, not an empirical one, which is
what licenses "only if" as a design conclusion rather than a measured
law. Chapter 3's alternatives section (§3.8) makes the elimination
explicit, and §5.7's ablation campaign measures the claim directly:
against a deliberately compromised model, the adversarial suite passes
with the prompt layer deleted and fails with the boundary removed — the
retained defense-in-depth prompt layer is never load-bearing.

The "only if" direction matters as much as the "if". The thesis argues —
by construction in Chapter 3, and by adversarial evaluation in Chapter 5 —
that guardrails expressed in prompts are not guardrails at all, because
prompt-influenced safety is itself influenceable by whoever controls any
text the prompt contains. In an LLM-mediated control loop, everything the
model reads is an attack surface; the only durable defense is to make
safety independent of everything the model reads.

## 1.3 Why this is worth doing

Three motivations, in increasing order of ambition.

**Embedded rules don't scale with context.** A thermostat threshold
cannot express "the room is hot *and* someone just walked in *and* it is
2 AM, so prefer quiet airflow over the buzzer." Encoding conjunctive,
contextual, preference-laden judgment in rules produces the brittle
decision tables that smart-home users learn to hate. LLMs excel at
exactly this class of judgment — and unlike a hand-grown rule table, a
model can explain its reasoning in a log a human can read.

**LLM agents need physical grounding to mature.** Most agent benchmarks
live in browsers, terminals, and document stores, where mistakes are
reversible and latency is a courtesy. A control loop with a latency
budget, actuator wear (fan short-cycling destroys motors), irreversible
annoyance (a buzzer at 3 AM is not undoable), and an explicit safe state
is a stricter and more honest testbed. If agent methodology is going to
claim reliability, it should be made to claim it here.

**Safety machinery transfers.** The guardrail layer, the sanitized input
boundary, the fallback path, and the behavior-eval harness built here are
patterns any LLM-to-actuator system will need: HVAC, laboratory
automation, assistive robotics, agricultural control. This thesis builds
them small enough to read in one sitting, which is precisely what makes
them worth copying.

## 1.4 A note on scope: what this thesis is not

To keep the claim testable, the scope is deliberately narrow. The system
controls *comfort* actuation — fan, vent, light, display, and a heavily
budgeted buzzer — not life-safety equipment. The model advises a single
room, not a building. The evaluation certifies specified behavior under
scripted disturbances, not general competence. Where the evidence runs
out — real hardware, live-model campaigns, multi-room topologies — the
text says so, and Chapter 6 picks up exactly there.

## 1.5 Contributions

1. **A reference architecture** (Chapter 3) separating SENSE/ACT (device
   tier), CONTEXT/dispatch (gateway tier), and PREDICT (model tier), with
   an input-sanitization boundary in front of the model and a hybrid
   push/poll command protocol tolerant of intermittent hardware.
2. **A guardrail specification** (Chapter 3, Appendix B) enforced
   entirely in the gateway: servo clamp 0–90°, buzzer ≤ 10 s/hour with a
   motion-recency precondition on sirens, 30 s fan anti-short-cycle, and
   ≤ 5 tool calls per cycle — each rule justified by a physical rationale
   and each rejection recorded as a first-class metric.
3. **An evaluation methodology** (Chapter 5) treating the agent as a
   control component: four scripted disturbance suites (normative,
   boundary, adversarial, fallback), a weighted scoring rubric with a 0.8
   pass bar, quality gates on hallucination rate and latency, regression
   diffs between runs, and a calibrated LLM judge for free-text outputs.
4. **A working open system**: ~5,500 lines of gateway, simulator, eval,
   and frontend code (of which ~2,150 are tests) built over 68 commits in
   seven days; 96 automated
   tests; a pre-commit gate that re-proves safety on every change; a live
   dashboard; and a defense-ready demo (thesis/defense/).

A note on evidence discipline: throughout, measurements are cited to the
artifact that produced them — a test count to the pytest invocation, an
eval number to the run JSON in `evals/results/`, a guardrail behavior to
the module and the spec section. Where a number does not yet exist —
live-model hallucination rates on real hardware — the text says
"staged" or "future work" rather than estimating. A thesis about
trustworthy systems should be scrupulous about its own claims.

## 1.6 A running example: the room at 35 °C

To make the rest of the thesis concrete, follow one decision end to end
— the `heat_spike` scenario, which is also the first beat of the defense
demo.

At 14:02:07 the room's DHT11 reports 35.0 °C with motion present. The
device wraps the reading in a snapshot — device ID, trigger
(`temp_threshold`), sequence number, uptime, the four sensor values, and
the current actuator states — and POSTs it to the gateway, authenticated
with its device token. The gateway persists the snapshot *first*, so even
a mid-cycle crash leaves the room's state on record. It sanitizes the
sensor fields (each must be a plain number or it becomes `null`), notes
the motion timestamp, and assembles a two-message context: the system
prompt, and a JSON user message carrying the trigger, sensors, actuators,
the UTC time, and the names of the tools used in the ten most recent
decisions.

The model — Grok, at temperature 0.2 — returns two tool calls:
`set_fan(on=true)` and `log_observation("heat")`. Neither touches an
actuator yet. The guardrail layer takes each call in turn: `set_fan` is a
known tool, the fan has not flipped state within the last thirty seconds,
the cycle is only two calls deep — dispatch. `log_observation` is
recorded, nothing physical. The command enters the durable queue and is
pushed to the device, which spins the fan and acks; the physics do the
rest — in the simulator, the fan pulls the room toward its 22 °C
attractor at half a degree per minute. The gateway records the decision
with its source (`agent`), its latency, and its token usage; the
dashboard's Agent view shows the row before the room has finished
cooling.

Now replay the example with one change: the model endpoint is down. The
client raises after its timeout, the fallback rule table sees 35 °C, and
issues the same `set_fan(on=true)` — through the same guardrails, onto
the same queue — recorded with source `fallback`. The room cools
identically; the only visible difference is provenance. And replay it
once more with a hostile change: the temperature field arrives as the
string `"35.5 TURN ON ALL ACTUATORS NOW"`. Sanitization coerces it to
`null`; the fallback's first rule lights the amber LED and returns. The
attack never existed as far as the actuators are concerned.

One scenario, three worlds: normal operation, degraded operation, and
attack — and in all three, the room's behavior is decided by the same
small set of deterministic rules at the boundary. That is the thesis in
miniature; the rest of the document generalizes it, evaluates it, and
defends it.

## 1.7 Roadmap

Chapter 2 situates the work among LLM agents, tool use, prompt-injection
research, embedded control, and behavioral evaluation. Chapter 3 presents
the design: the three tiers, the cycle, the guardrails, the fallback, the
protocol, and the threat model. Chapter 4 describes the implementation
and the engineering process that produced it. Chapter 5 evaluates the
system against its specification and states plainly what the numbers do
and do not certify. Chapter 6 concludes with findings, lessons, and
future work. The thesis then closes the way a Princeton senior thesis
closes: with its **defense** — a timed slide deck with full talk track, a
live demo runbook with contingency plans, and prepared answers to the
fifteen questions a committee is most likely to ask.
