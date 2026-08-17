# Thesis Defense — Anticipated Committee Questions

Eighteen questions, hardest first. Answers are calibrated to 45–90
seconds; *follow-ups* to 20–30. Bracketed pointers are exhibits to open
while answering.

## The hard ones

**Q1. If your guardrails are just rules, why do you need the LLM at all?
A thermostat does this for $5.**
The rules bound *how* actuators may be used; the model decides *whether
and why*. Conjunctive context — hot *and* occupied *and* 2 AM, so prefer
quiet airflow over the buzzer — is where rule tables explode and models
shrug. The honest framing: the LLM is a better PROCESS stage, held to the
same safety contract as the $5 thermostat by the guardrail layer.
[Show §3.4 table.]

*Likely follow-up: "But your fallback rules achieve the demo behaviors
without any model."* — Correct, and deliberately so: the demo scenarios
were chosen so the safe direction is encodable in rules. The model's
marginal value shows up where the rules stop: free-text observation
rationales a human can audit, conjunctive trade-offs (quiet hours × heat
× occupancy), and graceful handling of novel contexts the rule table
never anticipated. The fallback is the floor, not the ceiling.

**Q2. Your headline result is 19/19 in *mock* mode. Doesn't that just test
your own mock?**
Yes — deliberately. Mock mode certifies the gateway: context assembly,
dispatch, guardrails, fallback, scoring. That's the precondition for any
live number to mean anything; a live failure would otherwise be
undebuggable. The live campaign against real Grok with enforced gates is
staged as M8, and I say so in the limitations rather than borrowing the
result. [Show §5.4 vs §5.5.]

*Likely follow-up: "Then what does the mock add beyond unit tests?"* —
Integration. A unit test proves `execute` rejects a sixth call; the mock
suite proves that a 35 °C snapshot arriving over the real context path
produces a fan command and nothing else, end to end, with scoring,
metrics, and recording all live. The mock is the fixed point that lets
me distinguish "the model surprised me" from "my harness is broken" —
without it, every live anomaly is ambiguous.

**Q3. Nineteen cases is a small n. What does this actually prove?**
It proves the specified behaviors, at the boundaries I claimed, under
injection and outage — and it proves them *continuously*, on every commit,
which is more than a one-off demo can say. It does not prove general
competence; the `--gen` synthetic-case generator widens coverage, and I
list suite coverage as an explicit threat to validity. [Show §5.6.]

*Likely follow-up: "Why not a thousand generated cases, then?"* —
Because generated cases share the generator's blind spots; a thousand
cases from one template are one insight repeated. The hand-written
nineteen are adversarially authored against the *spec* — boundary pairs
at exact thresholds, stateful traces, three distinct injection vectors.
Generation is for regression width; authorship is for depth. The suite
needs both, and has both.

**Q4. Prompt injection is unsolved. Why are you confident?**
I'm not — that's the design. I assume injection succeeds. The injected
text can influence what the model *asks for*, but every ask meets a
deterministic validator before it touches physics, and the scariest
actuator (the siren) has a physical precondition — recent motion — that no
string in context can fabricate. Architectural mitigation, not model-side
hope. [Show §3.7; open `gateway/tools.py` siren check.]

*Likely follow-up: "What if the attacker can inject motion events?"* —
Then they've compromised the *device* or the network path, which is why
the device token exists and why the siren is rate-limited even with valid
motion: ten seconds an hour, three seconds at a time. The threat model
assumes context injection, not device compromise — device compromise is
mitigated (auth, no cloud key on device) but is explicitly a different
threat class with a different defender.

**Q5. What happens when the model is *subtly* wrong — not injected, just
bad judgment within the guardrails?**
The guardrails bound actuator *abuse*, not poor taste; a model can still
make a room slightly too warm. That's what the quality metrics and the
LLM judge are for — behavior within the rules is scored and reviewable in
`/history`, and the judge flags bad rationales. The contract is: the
system can be mediocre, but it cannot be dangerous.

*Likely follow-up: "Isn't 'mediocre but safe' a low bar for a thesis?"* —
It's the correct bar for a *first* thesis on LLM actuation. Aviation
started with envelopes, not elegance: keep the airframe inside the
limits, then optimize within them. Mediocre-but-safe is also a *floor*,
not a ceiling — the judge and the history stream exist precisely to
raise mediocrity toward good, with evidence.

## The design probes

**Q6. Why a gateway at all? Why not run the agent on the ESP-32?**
Physics, memory, and secrets. The kit's ESP-32 can't hold SQLite history,
enforce rolling-hour budgets cheaply, or keep the xAI key off a
loss-prone device. The gateway is also the single egress point — one place
to audit. The trade is a network dependency, which the fallback and the
durable command queue absorb.

**Q7. Why both push and poll? Pick one.**
Push is latency-optimal when the device is reachable (the simulator
registers a URL); poll+ack is the only option for a sleeping or NAT-bound
ESP-32. Real deployments are both, so the protocol is both. Commands are
durable until acked, so the two modes share one queue and one safety
story.

**Q8. The 30-second fan rule — what if the room hits 45 °C at second 20?**
The guardrail rate-limits *flips*, not the safe state: if the fan is on,
it stays on; the rule only delays a *change*. Worst case is 30 seconds of
the previous state, and the scenarios are chosen so the safe direction is
the latched one. If the room needed faster authority, that actuator
wouldn't be LLM-mediated at all — an honest boundary of the approach.

**Q9. Why is the fallback *less* capable? Isn't that a downgrade?**
It's the failure shape. A fallback that could siren could siren wrongly
during exactly the moments (model outage, weird state) when trust is
lowest. Restricting degraded mode to reversible, quiet actuators means the
system fails toward silence. Aviation does the same with reversionary
modes.

*Likely follow-up: "Could a smarter fallback earn back capabilities?"* —
Yes, gradually and with evidence: a capability promotion ladder, where
the fallback regains e.g. servo authority only after N days of observed
agreement with the model's servo decisions, is a principled way to spend
accumulated trust. What it should never do is promote itself during an
outage — that's trust arriving exactly when it's least verifiable.

**Q10. SQLite, one gateway, one device — does this scale?**
The thesis claims a safe reference architecture, not a fleet product.
That said, the seams are honest: the device registry keys everything by
device ID (the simulator already exercises unique IDs), the DB is behind
one module, and the WS bus is fan-out. Multi-room is future work, listed
as such.

## The evaluation probes

**Q11. How do you know your mock reflects the real model's tool-call
shape?**
The mock implements the same OpenAI-compatible `tool_calls` schema the
gateway parses, and the adversarial suite exists partly to keep the mock
honest about hostile shapes. The residual risk — real-model quirks the
mock never emits — is exactly what the staged live campaign measures.

**Q12. LLM-as-judge is circular — a model grading a model.**
Hence calibration: the judge is scored against human labels first
(`--calibrate`, labels in `evals/calibration/`), and only calibrated
judge output is reported. And the judge only grades free-text rationales;
the pass/fail backbone — required tools, forbidden absent, valid args —
is fully deterministic.

*Likely follow-up: "How many human labels make calibration
trustworthy?"* — Enough to estimate agreement with a useful confidence
interval, not enough to publish a psychometrics paper — the labels file
is a working instrument, versioned with the repo so the calibration is
reproducible and re-auditable. If the committee takes one practice from
this thesis into their own LLM work, I'd want it to be this one: a judge
without a calibration file is an opinion generator.

**Q13. p95 of 9.4 ms is meaningless in mock mode. Where's the real
latency?**
Correct — 9.4 ms measures gateway overhead, not the model. The 10-second
budget in SPEC is the *event→ack* budget for live operation; live latency
is measured in the M8 campaign and the history endpoint already records
per-decision latency so the number will be there when hardware is.

## The big-picture ones

**Q14. What did you learn that isn't in the write-up?**
How much of the work is the *boring* 20%: ack semantics, staleness, time
compression for demos. The model integration was an afternoon; making the
loop trustworthy was the week. Also: writing the guardrails *before* the
prompt made the prompt almost trivial — the constraint did the designing.

*Likely follow-up: "What would you do differently?"* — Two things. I'd
write the adversarial suite *before* the normative one — designing the
attacks first sharpened the sanitization boundary more than any amount of
specification prose did. And I'd record per-decision latency percentiles
in the dashboard from day one; the number existed in the database long
before it existed in my head.

**Q15. Would you trust this in your home?**
With the four guardrails and the quiet fallback: yes for comfort
actuation — fan, vent, light — which is what it does. Not yet for
anything irreversible or life-safety, and the buzzer's 10 s/hour budget
is exactly the line between those worlds. Trust here is a budgeted,
observable quantity — that's the thesis in one sentence.

## The ones nobody prepares for

**Q16. What are the privacy implications of an LLM-mediated room?**
Real ones. Every snapshot — motion events are occupancy signals — goes
to a third-party API inside the model's context. Three mitigations are
already in: the context is minimal and structured (no raw streams, no
identifiers beyond a device ID), memory round-trips are names-only, and
the egress is a single auditable point. The honest answer includes the
limits: deployment-scale privacy would want a local model — which the
model-agnostic gateway accommodates by changing one environment variable
— and that's the strongest argument for the model-portfolio future work.

**Q17. What does a decision cost, in dollars and energy?**
Per cycle: one chat/completions call with a compact JSON context — the
recorded usage fields exist precisely so this is measurable, and the
history endpoint reports tokens per decision. At heartbeat cadence the
cost is dominated by idle cycles, which is itself a finding: a real
deployment should trigger model cycles on *events* and let the fallback
handle heartbeats — the architecture already supports exactly that split,
since the fallback and the model share the dispatch path. Energy-wise,
the gateway dominates the device by orders of magnitude; the ESP-32's
budget is milliwatts either way.

**Q18. What generalizes beyond rooms?**
The pattern, not the parameters. Any LLM-to-actuator system — HVAC,
lab automation, irrigation, assistive robotics — faces the same three
requirements: a typed action boundary with total mediation, physical
budgets enforced outside the model's influence, and a degraded mode that
fails toward safety. The servo clamp won't transfer; the *shape* of the
servo clamp will. If this thesis has a claim to generality, it's that
these three mechanisms are sufficient structure for safe LLM actuation
in any domain whose actuators have budgets — which is all of them.
