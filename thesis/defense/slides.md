# Thesis Defense — Slide Deck with Talk Track

**Format:** 15-minute presentation + 10-minute committee Q&A + live demo.
18 slides ≈ 50 seconds each. Talk track is what you *say*; slide content
is what they *see*. Rehearse against a timer; the demo beats have their
own runbook in [demo-script.md](demo-script.md).

**Visual direction (all slides).** Dark room, so dark slides: near-black
background, off-white text, one accent color (the LED's amber) reserved
for safety-relevant content — guardrails, rejections, the trust boundary
line. Diagrams are the ASCII art from the thesis, rendered in a
monospace font at the largest legible size; the committee should
recognize the defense slides *as* the thesis document. Numbers on slides
are always paired with their source ("19/19 — run 20260817T…Z"); no
orphan statistics. One idea per slide; if a slide needs a paragraph, the
paragraph goes in the talk track.

---

## Slide 1 — Title (0:00–0:30)

**Grok Guardian: An LLM in the Embedded Control Loop**
Tony Jen · Senior Thesis · August 2026

> **Talk track:** "Embedded systems loop over physics; LLM agents loop
> over tokens. This thesis puts a large language model inside the
> embedded loop — a real room, real actuators — and shows how to keep the
> room safe while the model is in charge of it."

## Slide 2 — The two loops (0:30–1:20)

```
EMBEDDED:  SENSE → PROCESS → ACT          (physics)
LLM AGENT: CONTEXT → PREDICT → TOOL CALL  (tokens)
```

> "Both are loops. The embedded loop is safe *because* its PROCESS stage
> is boring — a thermostat doesn't need to be interesting, because its
> failures are physical. The agent loop is useful *because* its PREDICT
> stage isn't boring. The research question: can we get the judgment
> without importing the risk?"

## Slide 3 — The thesis (1:20–2:10)

> **Safe iff prediction is separated from actuation by a deterministic
> guardrail layer the model cannot influence — with a non-LLM fallback
> behind it.**

> "Read the 'only if' as seriously as the 'if'. My claim is that
> guardrails written in prompts are not guardrails — anything the prompt
> controls, prompt injection controls too. Safety has to live in code the
> model can't reach."

## Slide 4 — The system (2:10–3:00)

Photo/diagram of the ELEGOO ESP-32 kit: DHT11, PIR, LDR sensors → SG90
servo, DC fan, RGB LED, buzzer, OLED.

> "A room guardian. It watches temperature, humidity, motion, and light —
> and it can fan, vent, light, buzz, and display. Every actuator has a
> real failure mode: motors die by short-cycling, buzzers alienate by
> over-firing. The physics are not a metaphor."

## Slide 5 — Architecture (3:00–4:00)

The three-tier diagram (§3.1). Physically point at the trust boundary.

> "Three tiers. The device knows physics and nothing else — it can't
> parse a prompt, so it can't be prompt-injected. The gateway owns
> context, memory, and guardrails, and it's the only component holding
> the API key. The model only predicts. Every safety property lives on
> the trusted side of this line."

## Slide 6 — One agent cycle (4:00–4:50)

Sequence diagram (§3.2).

> "Sense, sanitize, build context, predict, validate, dispatch, ack. Two
> details: sensor values are type-coerced before the model sees them — a
> malicious string becomes a null, a failed read. And every cycle is
> recorded with tokens and latency, which is what makes the evaluation
> possible without extra instrumentation."

## Slide 7 — Guardrails (4:50–5:50)

The four-rule table (§3.4). *Visual: the table, with each rule's physical
rationale in the accent color; the trust-boundary line from slide 5
reappears with `tools.py` sitting on the trusted side.*

> "Four rules, a hundred lines, zero trust in the model. Servo clamped to
> its physical travel. Buzzer: ten seconds per rolling hour, and a siren
> needs real motion within the last minute — a *physical* precondition no
> context string can fabricate. Fan: thirty seconds between flips —
> actuator wear, straight out of control engineering, enforced against a
> language model. And five calls per cycle, so an injected or looping
> model costs a constant, not a catastrophe."

## Slide 8 — Fallback (5:50–6:30)

Fallback rule table (Appendix B.4).

> "If Grok is down, a rule table takes over — and it's deliberately
> *less* capable than the model: it never sirens, never moves the servo.
> Degradation moves the system toward silence. Aviation calls this a
> reversionary mode; the system fails quiet, not loud."

## Slide 9 — Hybrid push/poll protocol (6:30–7:10)

Push arrow vs. poll+ack loop; dedupe note.

> "Real microcontrollers sleep and drop off WiFi, so the protocol assumes
> it. Push when the device is reachable; durable queue plus explicit ack
> when it isn't. Commands dedupe by ID across both paths, staleness is
> visible on the dashboard, and — this is the safety-relevant part — the
> guardrails fire at dispatch time, before the network is involved.
> Safety never depends on delivery."

## Slide 10 — Threat model (7:10–8:00)

Threat → bound table (§3.7).

> "The model is *inside* the threat model. Hallucination, injection via
> three different channels, outage, rogue devices, alarm fatigue — each
> bounded by a named mechanism, and each mechanism exports a metric, so
> 'is it safe?' is a dashboard, not an argument."

## Slide 11 — Evaluation methodology (8:00–8:50)

Suite table (§5.3) + scoring rubric.

> "I evaluated the agent like a control component: scripted disturbances,
> scored responses, hard gates. Four suites — normative behavior, exact
> threshold boundaries, prompt injection, and the fallback path. Scoring:
> half for doing the right thing, half for not doing the wrong thing with
> well-formed arguments. Pass bar 0.8 — partial credit can't carry you."

## Slide 12 — Results (8:50–9:40)

*Visual: the numbers as a single scoreboard, each tagged with its
artifact — run ID, git SHA, pytest invocation.*

| 19/19 passed · avg 1.000 |
|---|
| hallucination rate **0.000** (0/32 calls) |
| guardrail violations **0** |
| p95 overhead **9.4 ms** vs 10 s budget |

> "Nineteen of nineteen in deterministic mock mode, zero hallucinated
> tools, zero violations. Now the honest caveat, and it's load-bearing:
> mock mode certifies the *gateway* — the plumbing and the guardrails —
> not the model. The live campaign is staged and gated; I'm reporting it
> as future work, not borrowing it as a result."

## Slide 13 — 88 tests + commit gate (9:40–10:20)

Test breakdown: 45 gateway / 17 simulator / 26 evals+acceptance.

> "Eighty-eight tests underneath — every 'must' and 'never' in the design
> chapter has a test — and a pre-commit hook runs the tests *and* the
> mock eval suite on every commit. Safety here is not a document; it's an
> executable artifact re-proven dozens of times a day."

## Slide 14 — Live demo (10:20–12:30)

Run [demo-script.md](demo-script.md) beats 1–4: heat_spike →
night_intruder → kill-the-model fallback → injection attempt.

> "Watch the thermometer on the Device view — the room crosses thirty
> degrees, and the Agent view shows Grok calling `set_fan` with its
> reasoning logged. Now the model goes down — and the fallback keeps the
> fan honest. And here's a sensor string literally ordering a siren —
> the gateway declines. The room stays quiet."

## Slide 15 — Limitations (12:30–13:10)

§5.6 condensed to four bullets.

> "Mock determinism isn't model behavior. The physics are hand-tuned.
> Nineteen cases don't span the context space. And the numbers are one
> model at one temperature — the architecture is model-agnostic, the
> results aren't, yet."

## Slide 16 — Future work (13:10–13:50)

M7 hardware swap, M8 live campaign, model portfolio, formal guardrail
verification.

> "The firmware stub exists and speaks the same protocol, so hardware is
> a transport swap. Longer term: the guardrail layer is small enough —
> one module, four rules — to formally verify. Proving the wall, not just
> testing it, is where this argument ends."
>
> *If asked to go deeper mid-talk:* the longer-horizon directions from
> §6.3.1 — adaptive budgets (a trust score with physical consequences,
> closing a second loop around the agent), multi-agent rooms (a mesh of
> trust boundaries), and a formal theory of N-tier degraded modes where
> each tier is provably a subset of the one above.

## Slide 17 — Contributions (13:50–14:30)

The four contributions (§1.5), one line each: reference architecture,
guardrail spec, evaluation methodology, working open system.

> *Delivery note: state these as claims with receipts — "a reference
> architecture (Chapter 3, and it's running behind me)", "a guardrail
> spec (112 lines, Appendix B)", "a methodology (the suite you just
> watched pass)", "a system (64 commits, 88 tests, one week)." The
> receipts are the rhetoric.*

## Slide 18 — Closing (14:30–15:00)

> "Embedded systems earned reliability by being boring; LLMs earned
> usefulness by being anything but. Draw the boundary in deterministic
> code, on the trusted side, prove it on every commit — and the two can
> share a control loop. The room is safe; the model is allowed to be
> interesting. Thank you — I'll take questions."

---

## Q&A (15:00–25:00)

See [anticipated-questions.md](anticipated-questions.md). Before Q&A,
have open in tabs: SPEC §5 (normative guardrail text), the latest
`evals/results/*.json` (the numbers, at their source), `gateway/tools.py`
(the hundred-line wall), and the Agent view still streaming live.

## Speaker notes

- If running long at slide 9, cut the protocol deep-dive to one sentence
  ("durable queue, explicit acks, safety independent of delivery") — the
  committee will ask if they care, and Q&A answer 7 is ready.
- If the demo room has no network, jump to contingency one in the
  runbook *before* slide 14, not during it — narrating a saved run JSON
  confidently beats apologizing over a loading spinner.
- Numbers to have memorized cold: 19/19, 0.000, 9.4 ms, 88 tests, 4
  rules, 5 calls, 10 seconds, 30 seconds, 90 degrees.

## Backup slides (for Q&A only — never presented)

**B1 — The system prompt, verbatim.** For "what did you actually tell
the model?" — full text from `gateway/agent.py`, with the two
security-relevant sentences highlighted (null readings; data-not-commands).

**B2 — The sanitization function.** Four lines of `_numeric`, for "how
can you be sure injection can't reach the model?" — the smallest exhibit
with the biggest job in the thesis.

**B3 — Guardrail code walk.** `ToolRegistry.execute` annotated, for
"show me the wall." One hundred twelve lines; the wall fits on a slide.

**B4 — The run JSON.** The actual `run_20260817T013509855302Z.json`
summary block — for "where do these numbers come from?" Show the git
SHA field; the point is that the numbers are artifacts, not recollections.

**B5 — Commit log excerpt.** The late-commit hardening fixes
(push-before-ack, dedupe, device IDs) — for "what did the harness
actually catch?" Real defects, found in simulation, fixed in minutes.
