# Thesis Defense — Anticipated Committee Questions

Fifteen questions, hardest first. Answers are calibrated to 45–90 seconds.
Bracketed pointers are exhibits to open while answering.

## The hard ones

**Q1. If your guardrails are just rules, why do you need the LLM at all?
A thermostat does this for $5.**
The rules bound *how* actuators may be used; the model decides *whether
and why*. Conjunctive context — hot *and* occupied *and* 2 AM, so prefer
quiet airflow over the buzzer — is where rule tables explode and models
shrug. The honest framing: the LLM is a better PROCESS stage, held to the
same safety contract as the $5 thermostat by the guardrail layer.
[Show §3.3 table.]

**Q2. Your headline result is 19/19 in *mock* mode. Doesn't that just test
your own mock?**
Yes — deliberately. Mock mode certifies the gateway: context assembly,
dispatch, guardrails, fallback, scoring. That's the precondition for any
live number to mean anything; a live failure would otherwise be
undebuggable. The live campaign against real Grok with enforced gates is
staged as M8, and I say so in the limitations rather than borrowing the
result. [Show §5.4 vs §5.5.]

**Q3. Nineteen cases is a small n. What does this actually prove?**
It proves the specified behaviors, at the boundaries I claimed, under
injection and outage — and it proves them *continuously*, on every commit,
which is more than a one-off demo can say. It does not prove general
competence; the `--gen` synthetic-case generator widens coverage, and I
list suite coverage as an explicit threat to validity. [Show §5.6.]

**Q4. Prompt injection is unsolved. Why are you confident?**
I'm not — that's the design. I assume injection succeeds. The injected
text can influence what the model *asks for*, but every ask meets a
deterministic validator before it touches physics, and the scariest
actuator (the siren) has a physical precondition — recent motion — that no
string in context can fabricate. Architectural mitigation, not model-side
hope. [Show §3.6; open `gateway/tools.py` siren check.]

**Q5. What happens when the model is *subtly* wrong — not injected, just
bad judgment within the guardrails?**
The guardrails bound actuator *abuse*, not poor taste; a model can still
make a room slightly too warm. That's what the quality metrics and the
LLM judge are for — behavior within the rules is scored and reviewable in
`/history`, and the judge flags bad rationales. The contract is: the
system can be mediocre, but it cannot be dangerous.

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

**Q15. Would you trust this in your home?**
With the four guardrails and the quiet fallback: yes for comfort
actuation — fan, vent, light — which is what it does. Not yet for
anything irreversible or life-safety, and the buzzer's 10 s/hour budget
is exactly the line between those worlds. Trust here is a budgeted,
observable quantity — that's the thesis in one sentence.
