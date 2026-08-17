# Thesis Defense — Slide Deck with Talk Track

**Format:** 15-minute presentation + 10-minute committee Q&A + live demo.
18 slides ≈ 50 seconds each. Talk track is what you *say*; slide content is
what they *see*.

---

## Slide 1 — Title (0:00–0:30)

**Grok Guardian: An LLM in the Embedded Control Loop**
Tony Jen · Senior Thesis · August 2026

> Talk track: "Embedded systems loop over physics; LLM agents loop over
> tokens. This thesis puts an LLM inside the embedded loop — and shows how
> to keep the room safe while it's there."

## Slide 2 — The two loops (0:30–1:20)

```
EMBEDDED:  SENSE → PROCESS → ACT
LLM AGENT: CONTEXT → PREDICT → TOOL CALL
```

> "Both are loops. The embedded loop is safe because its PROCESS stage is
> boring. The agent loop is useful because its PREDICT stage isn't. The
> question: can we get the judgment without losing the safety?"

## Slide 3 — The thesis (1:20–2:10)

> **Safe iff prediction is separated from actuation by a deterministic
> guardrail layer the model cannot influence, with a non-LLM fallback
> behind it.**

> "Note the 'only if' — I'll argue guardrails in prompts aren't
> guardrails, because anything the prompt controls, prompt injection
> controls too."

## Slide 4 — The system (2:10–3:00)

Photo/diagram of the ELEGOO ESP-32 kit: DHT11, PIR, LDR → SG90 servo, DC
fan, RGB LED, buzzer, OLED.

> "A room guardian. It watches temperature, humidity, motion, light — and
> it can fan, vent, light, buzz, and display. Every actuator has a real
> failure mode: motors wear, buzzers enrage."

## Slide 5 — Architecture (3:00–4:00)

The three-tier diagram (thesis §3.1). Point at the trust boundary.

> "Device: physics only. Gateway: context, guardrails, memory. Model:
> predict only. The trust boundary is between gateway and model — every
> safety property lives on the trusted side."

## Slide 6 — One agent cycle (4:00–4:50)

Sequence diagram (§3.2).

> "Sense, store, build context, predict, validate, dispatch, ack. Every
> cycle is recorded with tokens and latency — that's what makes the
> evaluation possible without extra instrumentation."

## Slide 7 — Guardrails (4:50–5:50)

The four-rule table (§3.3).

> "Servo clamped to its physical travel. Buzzer: ten seconds an hour, and
> a siren needs motion within the last minute. Fan: thirty seconds between
> flips — that's actuator wear, from control engineering, enforced against
> a language model. Five calls per cycle, so an injected or looping model
> is bounded."

## Slide 8 — Fallback (5:50–6:30)

Fallback rule table (Appendix B.4).

> "If Grok is down, a rule table takes over — deliberately *less* capable
> than the model: it never sirens. The system fails quiet, not loud."

## Slide 9 — Hybrid push/poll protocol (6:30–7:10)

Push arrow vs. poll+ack loop.

> "Real ESP-32s sleep and drop off WiFi. Push when the device registers a
> URL, poll with explicit acks otherwise. Commands are durable; safety
> never depends on delivery."

## Slide 10 — Threat model (7:10–8:00)

Threat → bound table (§3.6).

> "The model is *inside* the threat model. Hallucination, injection,
> outage, rogue devices — each is bounded by a named mechanism, and each
> mechanism has a metric so we can watch it work."

## Slide 11 — Evaluation methodology (8:00–8:50)

Suite table (§5.3) + scoring rubric.

> "I evaluated the agent like a control component: scripted disturbances,
> scored responses, hard gates. Four suites — normative, boundary,
> adversarial, fallback. Fifty percent required actions, thirty forbidden
> absent, twenty valid arguments. Pass bar: 0.8."

## Slide 12 — Results (8:50–9:40)

| 19/19 passed | avg 1.000 |
|---|---|
| hallucination rate | 0.000 |
| guardrail violations | 0 |
| p95 latency | 9.4 ms (mock) vs 10 s budget |

> "Nineteen of nineteen in deterministic mock mode, zero hallucinated
> tools, zero guardrail violations, and a commit gate re-proves this on
> every change. Mock mode certifies the gateway; the live campaign is
> staged and honest — that's next."

## Slide 13 — 88 tests + commit gate (9:40–10:20)

Test pyramid: 45 gateway / 17 sim / 26 evals+acceptance.

> "Safety properties were tested before they were trusted. Every commit
> runs pytest and the mock eval suite — nothing merges red."

## Slide 14 — Live demo (10:20–12:30)

Run [demo-script.md](demo-script.md): heat_spike → night_intruder →
kill-the-model fallback → injection attempt.

> "Watch the dashboard's Device view — the fan spins up when the room
> crosses thirty degrees. Now I'll simulate an outage… the fallback keeps
> the fan honest. And here's the model being told by a sensor string to
> sound the siren — the gateway declines."

## Slide 15 — Limitations (12:30–13:10)

§5.6 list, condensed to four bullets.

> "Mock determinism isn't model behavior; the physics are hand-tuned;
> nineteen cases don't span the context space; and the numbers are for one
> model. The architecture is model-agnostic — the results aren't, yet."

## Slide 16 — Future work (13:10–13:50)

M7 hardware swap, M8 live campaign, model portfolio, formal guardrail
checks.

> "The firmware stub exists; the simulator speaks the same protocol, so
> hardware is a transport swap. The live eval campaign with gates is
> ready to run."

## Slide 17 — Contributions (13:50–14:30)

The four contributions (§1.4), one line each.

## Slide 18 — Closing (14:30–15:00)

> "Embedded systems earned reliability by being boring; LLMs earned
> usefulness by being anything but. Draw the boundary in deterministic
> code, on the trusted side, and prove it on every commit — and the two
> can share a control loop. The room is safe; the model is allowed to be
> interesting. Thank you — I'll take questions."

---

## Q&A (15:00–25:00)

See [anticipated-questions.md](anticipated-questions.md). Have SPEC §5 and
the eval results JSON open in tabs before Q&A begins.
