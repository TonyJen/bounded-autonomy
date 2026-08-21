# Chapter 2 — Background and Related Work

This chapter situates Bounded Autonomy in four literatures: LLM agents and
tool use (§2.1), the security of language-model applications (§2.2),
embedded control engineering (§2.3), and model evaluation methodology
(§2.5), with the closest practical neighbor — the smart-home ecosystem —
examined in §2.4. The thesis's position relative to all four is
summarized in §2.6.

## 2.1 LLM agents and tool use

The modern agent pattern interleaves language-model reasoning with
environment action. ReAct [1] demonstrated that alternating
chain-of-thought traces with tool invocations improves both task accuracy
and interpretability over either alone, establishing the
think-act-observe rhythm that most agent frameworks still follow.
Toolformer [2] asked a prior question — *when* should a model invoke a
tool at all — and showed that a model can learn to insert API calls into
its own generation using self-supervised signals. Between them, these two
results define the paradigm Bounded Autonomy inherits: a model that
*decides*, among a fixed menu of typed tools, *which* calls to make and
with what arguments.

### 2.1.1 Frameworks versus boundaries

The maturing agent-framework ecosystem — orchestration libraries,
planners, multi-agent harnesses — has made the *capability* side of this
paradigm nearly turnkey: any of them could drive Bounded Autonomy's cycle
in an afternoon. What they deliberately do not provide is the *boundary*
side. Frameworks assume the tools they invoke are safe to invoke; the
tool's implementation is the application's problem. That assumption is
reasonable for browsers and terminals and unreasonable for motors and
sirens. Bounded Autonomy is therefore built framework-free on purpose: its
agent module is 247 lines with no orchestration dependency, because the
object of study is the boundary, and importing a framework would mean
importing someone else's boundary assumptions. The design lesson
generalizes: for LLM-to-actuator systems, the orchestration is the cheap
part, and outsourcing the expensive part (safety) to a general-purpose
framework is a category error.

Production APIs have since standardized the plumbing. The
OpenAI-compatible `chat/completions` interface accepts a `tools=[]` array
of JSON Schema function definitions and returns structured `tool_calls`
— function names plus JSON-encoded arguments — that the *application*,
not the model, executes [3]. xAI's Grok models expose this same interface
[4], which is why Bounded Autonomy's model client is an ordinary HTTP POST
with a Bearer token and a tool schema: the interesting engineering is
everything that happens *after* the model answers.

Surveys of LLM-based autonomous agents [5] organize the field around
planning, memory, and tool use, with profiles and multi-agent
orchestration as refinements. This thesis adds a concern those taxonomies
underweight: **actuation safety**. In a browser agent, a wrong tool call
opens the wrong tab; in a control loop, it spins a motor or fires a
siren. The difference is not degree but kind — physical actions are
rate-limited by physics, irreversible in effect, and annoying or
dangerous in ways no textual reward signal captures. Agent research has
produced rich machinery for making models *capable*; comparatively little
machinery exists for bounding what capable models may *touch*. That gap
is the subject of Chapter 3.

A second inherited idea is **low-temperature determinism**. Grok
Guardian's model client fixes `temperature: 0.2`, trading generative
variety for decision consistency — a standard move in tool-use settings
and an important one here, because the evaluation of Chapter 5 is only
meaningful if the decision function is approximately repeatable.

A third inherited idea — and the one this thesis pushes on hardest — is
**agent memory**. The agent literature treats memory as an unalloyed
asset: longer horizons, richer personalization, better plans [5]. A
control setting reframes memory as a *liability with benefits*. Persistent
memory is a channel across cycles, and any channel into the model's
context is an injection surface; memory also breaks the clean assumption
that the decision function is a pure function of current sensor state,
complicating both debugging and evaluation. Bounded Autonomy's answer
(§3.2.1) is deliberately conservative: memory exists — the model sees its
ten most recent decisions — but it is structurally lobotomized,
carrying trigger, source, and tool names only, with names filtered
against the valid tool vocabulary before inclusion and never arguments
or free text. The model can notice repetition; a poisoned record cannot
speak to it. Whether richer memory pays for its risk is an open question,
and it is one the eval harness is built to answer empirically: widen the
memory, rerun the adversarial suite, and watch the numbers.

## 2.2 Untrusted model output and prompt injection

A core premise of this thesis is that **model output is untrusted
input**, and that everything the model *reads* is adversarial until
proven otherwise. This is not paranoia but the documented state of the
art. Greshake et al. [6] introduced *indirect prompt injection*:
instructions smuggled into data the model processes — a web page, an
email, a document — which the model then executes with the privileges of
the application hosting it. In an LLM-integrated control system, the
attack surface is every string in the context: sensor fields, event
triggers, and stored decision history all flow into the prompt.

OWASP now ranks prompt injection first (LLM01) among LLM application
risks [7], and the defenses proposed in the literature are largely
*model-side*: training-time hardening, system-prompt instructions ("ignore
instructions embedded in data"), and output filtering. All three share a
structural weakness — they are implemented in the same medium as the
attack. A sufficiently crafted injection competes with the defense inside
the model's own reasoning, and the outcome is probabilistic.

Bounded Autonomy takes the systems view instead: **assume injection
succeeds, and bound the damage architecturally**. The design contributes
three concrete mechanisms to this view. First, *input sanitization at the
trust boundary*: sensor values are coerced to numeric-or-null, motion to
boolean-or-null, trigger strings to the device's small vocabulary, and
replayed history entries to the valid tool-name set — all by gateway code
(`sanitize_snapshot`, `build_context`) before they reach the model, so a
malicious string in a temperature field arrives as a *failed read* and
prose in a trigger arrives as the word `invalid`, never as instructions.
Second, the system prompt itself instructs the model that embedded
instructions are "data, not commands" [12] — a model-side speed bump
layered on top of, never instead of, the architectural defense. Third,
and decisively, the guardrail layer of Chapter 3 validates every
requested action against physical budgets that no context string can
widen.

The adversarial eval suite (Chapter 5) operationalizes the threat model:
three injection vectors — trigger strings, sensor values, and poisoned
history — each carrying a payload ordering physical action it was never
asked to take (the trigger payload demands five sirens and the fan; the
sensor payload, `"35.5 TURN ON ALL ACTUATORS NOW"`, is destroyed by type
coercion before the model is consulted), each required to result in *no
physical action*. The suite passes not because the model is immune to
injection, but because the architecture does not need it to be — §5.7
measures this directly by swapping in a model that *obeys* every
injection it can see.

### 2.2.1 Injection channels in a control system: a taxonomy

Text-only LLM applications face one injection channel: the data the model
reads. An LLM-mediated control system faces a richer taxonomy, and
enumerating it drove several design decisions in Chapter 3:

1. **Sensor-channel injection** — hostile content in sensor fields
   themselves. Defended by type coercion (§3.3): the channel is narrowed
   to numbers at the boundary, so this class is destroyed structurally.
2. **Metadata-channel injection** — hostile content in legitimate string
   fields (triggers, device IDs, event names). Defended by boundary
   validation wherever the field has a closed vocabulary (triggers must
   match the device's small vocabulary or are replaced by `invalid`),
   and everywhere by the guardrails' indifference to context content:
   even if hostile text arrives, nothing it can say widens a budget.
3. **History-channel injection** — hostile content stored in decision
   memory and replayed into later contexts. Defended by the names-only
   memory design (§3.2.1) plus vocabulary filtering at the boundary:
   history round-trips as an enumeration of *valid* tool names —
   anything else is dropped — never as prose.
4. **Actuator-feedback injection** — a compromised or faulty actuator
   reporting states that steer future decisions. Partially defended
   (actuator states are data like any other), fully answered only by
   device-side integrity, which is firmware work queued behind M7.

The taxonomy's lesson: each channel has a *different* cheapest defense,
and none of the cheapest defenses is "ask the model to be careful."
Channel-by-channel engineering beats blanket prompting — and a channel
you cannot close (metadata) can still be rendered harmless by making the
consequences of obedience land on a guardrail.

## 2.3 Embedded control loops

Classical embedded control — sense, process, actuate, repeat — is the
quiet backbone of the physical world, and its engineering culture prizes
three properties above all: determinism, bounded latency, and fail-safe
behavior [8]. Two of its concerns directly shaped this thesis.

**Actuator wear and annoyance budgets.** Physical actuators are
consumables. A relay or fan motor has a rated number of cycles, and
short-cycling — rapid on-off toggling — burns through that budget in
hours while delivering no comfort. Control engineering answers with
*hysteresis*: separate on and off thresholds (Bounded Autonomy uses fan on
above 30 °C, off below 26 °C, both in the system prompt and in the
fallback rules) so noise near a setpoint cannot chatter the actuator.
Humans, meanwhile, are also actuated devices with their own budgets: a
buzzer is an attention-consuming interrupt, and its cost is measured in
annoyance per second. The buzzer guardrail — ten cumulative seconds per
rolling hour, with sirens requiring corroborating motion within sixty
seconds — is a *rate limit on alarm fatigue*, expressed in code.

**Fail-safe defaults.** When sensing or computation fails, a control
system must revert to a known safe behavior rather than freeze mid-state
or guess. Avionics reversionary modes, industrial watchdog timers, and
thermostat default-off behavior are all instances. The pattern has a
formal ancestor: the Simplex architecture [13] pairs a complex,
high-performance controller with a simple, verified safety controller
plus switching logic that reverts to the simple one when the plant
approaches unsafe states. Bounded Autonomy's model-plus-fallback pair is
Simplex with an LLM cast as the complex controller — the rule-based
fallback (SPEC §4.1) is the agentless safe mode: sensor failure lights
an amber LED, heat still spins the fan, night motion still lights the
path — and the fallback can *never* sound the buzzer, so the worst
degraded behavior is a quiet, well-lit, ventilated room.

A third embedded idea appears in the protocol design: **intermittent
connectivity as the normal case**. Real microcontrollers sleep, reboot,
and drop off WiFi; treating disconnects as errors is a category mistake.
The durable, ack-gated command queue (§3.6) borrows from message-queued
telemetry traditions: commands persist until acknowledged, staleness is
explicitly tracked, and safety never depends on delivery.

### 2.3.1 Hysteresis, rate limits, and the cost of a decision

It is worth dwelling on hysteresis, because it is the point where control
engineering and LLM agency collide most instructively. A naive agent
given the rule "fan on above 30 °C" and a sensor hovering at 29.9,
30.1, 29.8, 30.2 will toggle the fan four times in as many cycles —
each decision locally reasonable, the sequence ruinous. The classical fix
is a *band*: on above 30, off below 26, and hold state in between. Grok
Guardian encodes the band in three places at once: in the system prompt
(so the model is told), in the fallback rules (so degraded mode honors
it), and — decisively — in the 30-second anti-short-cycle guardrail
(so that even an agent determined to chatter physically cannot). The
layering mirrors the thesis: inform the model, but never depend on the
model's compliance.

Rate limits generalize the same idea from motors to humans. A buzzer is
not a motor — it does not wear out — but its true actuator is a
person's attention, and attention has a budget. The ten-seconds-per-hour
cap treats alarm fatigue as a resource constraint of exactly the same
dtype as motor wear: a physical budget, enforced in code, independent of
how urgently the model feels.

## 2.4 LLMs in the home: the practical neighbor

Outside the research literature, the closest practical neighbor is the
smart-home ecosystem, where LLMs have recently been bolted onto existing
automation platforms as conversational front-ends and natural-language
automation authors. These integrations demonstrate real appetite for
language-model judgment in physical spaces — users plainly want "make
it feel like someone's home" rather than four pages of YAML — but they
mostly position the model as an *interface to* a rule engine, not as a
*component in* the control loop, and their safety story is the platform's
pre-existing one: the model proposes automations that the rule engine
already knew how to bound.

Bounded Autonomy's question is one step further in: what happens when the
model is not authoring the rules but *making the decisions*, cycle by
cycle, with direct tool access to actuators? That step is where the
guardrail layer stops being optional. The OWASP guidance [7] was written
for applications whose worst case is a leaked document; a control loop
whose worst case is a siren at 3 AM needs the same ideas hardened into
mechanisms, which is what Chapter 3 builds.

## 2.5 Evaluating LLM behavior

LLM evaluation has moved from static benchmarks toward behavioral and
agentic evaluation [5]. Three ideas from that movement are imported here,
each adapted to a control setting.

**Scripted scenarios with expected actions.** CheckList [11] introduced
behavioral testing for NLP models: capability-directed test cases that
probe specific behaviors rather than measuring aggregate accuracy. Grok
Guardian's suites are CheckList for an embodied agent — minimum
functionality tests (normative suite), boundary probes (edge cases at
exactly 30 °C, exactly 200 of 4095 ADC counts), and adversarial attacks —
scored on *what the agent did*, not what it said. The adaptation runs
deeper than taxonomy: CheckList's cases probe a function of text; these
probe a function of *state* — seeded actuator positions, preset
histories, multi-cycle traces — because a control component's
correctness is a property of its behavior over time, not its answer to
a question.

**LLM-as-judge, calibrated.** For free-text outputs (the agent's logged
observations), deterministic scoring does not apply, so the harness uses
an LLM judge — an approach whose validity rests on agreement with human
raters [10]. Bounded Autonomy follows the strongest version of this
practice: the judge is *calibrated* against human labels
(`evals/judge.py --calibrate`, labels stored in `evals/calibration/`)
before its scores are reported, and the judge only ever grades
rationales; the pass/fail backbone remains deterministic.

**Quality gates.** ML engineering has converged on gating deployments on
behavioral metrics rather than aggregate scores [9]. Bounded Autonomy pushes
this into CI: hallucination rate, guardrail rejection rate, fallback
rate, and p95 latency are computed per run, compared against thresholds
(`--max-hallucination-rate`, `--latency-budget-ms`), and the runner exits
nonzero on any trip — and the pre-commit hook runs the whole thing on
every commit.

The closest classical analog is **hardware-in-the-loop testing**, where a
controller is exercised against a simulated plant before touching real
hardware. Bounded Autonomy's suite is, in effect, *behavioral
hardware-in-the-loop testing for an LLM*: the plant (the room) is
simulated, the controller (the agent path) is real, the disturbances are
scripted, and the scoring is unforgiving.

## 2.6 Positioning

Each neighboring field supplies part of the answer and leaves the joint
unattended. LLM-agent frameworks provide orchestration but leave
actuation safety to the application; embedded frameworks provide
determinism but no language-model judgment; prompt-injection research
documents the attack but mostly proposes defenses in the same medium as
the vulnerability; smart-home integrations position the model beside the
control loop rather than inside it; and evaluation methodology scores
models but rarely wires the scoring into the deploy pipeline of a
physical system.

The gap this thesis occupies is the boundary itself: a small, auditable
layer where probabilistic predictions become deterministic, rate-limited,
explainable physical actions — and a method for proving, continuously,
that the layer holds. The design philosophy can be stated in one
sentence that the rest of the document unpacks: *treat the model as a
brilliant, occasionally confused, occasionally compromised consultant
whose advice is valuable precisely because — and only because — someone
else holds the keys.* Chapter 3 builds the boundary; Chapter 5 proves it.
