# Chapter 1 — Introduction

## 1.1 Two loops

Embedded systems and LLM agents are both loops, but they loop over
different worlds:

```
EMBEDDED:  SENSE → PROCESS → ACT          (in a world of physics)
LLM AGENT: CONTEXT → PREDICT → TOOL CALL  (in a world of tokens)
```

The embedded loop is old, well understood, and boring by design: read a
sensor, apply a rule, move an actuator, repeat forever. Its PROCESS stage
is deliberately simple — a thermostat does not need to be interesting —
because its outputs are physical and its failures are too.

The LLM agent loop is new, expressive, and untrusted by default. Its
PREDICT stage can reason over rich context, weigh trade-offs no rule table
anticipates, and explain itself — and it can also hallucinate, be prompt-
injected, time out, or cost money per thought.

This thesis joins the loops. Grok Guardian is a room guardian: an ESP-32
microcontroller (or its software twin, a physics simulator) senses
temperature, humidity, motion, and light; a Grok LLM decides what the room
should do about it; actuators — fan, vent servo, RGB LED, buzzer, OLED —
carry the decision out. The research question is not whether the model is
*clever*; it is whether the model can be *safe inside the loop*.

## 1.2 Thesis statement

> **An LLM can occupy the decision stage of a physical control loop safely
> if and only if prediction is separated from actuation by a deterministic
> guardrail layer that the model cannot influence, and if a non-LLM
> fallback preserves safe behavior when the model is absent.**

The "only if" direction matters as much as the "if": the thesis argues —
by construction and by evaluation — that guardrails expressed in prompts
are not guardrails at all, because prompt-influenced safety is itself
influenceable by the prompt's attacker.

## 1.3 Why this is worth doing

Three motivations:

1. **Embedded rules don't scale with context.** A thermostat threshold
   cannot express "the room is hot *and* someone just walked in *and* it's
   2 AM, so prefer quiet airflow over the buzzer." LLMs excel at exactly
   this conjunctive, contextual judgment.
2. **LLM agents need physical grounding to mature.** Most agent benchmarks
   live in browsers and terminals. A control loop with latency budgets,
   actuator wear (fan short-cycling destroys motors), and irreversible
   annoyance (a buzzer at 3 AM) is a stricter and more honest testbed.
3. **Safety machinery transfers.** The guardrail layer, fallback path, and
   behavior-eval harness built here are patterns any LLM-to-actuator
   system — HVAC, lab automation, assistive robotics — will need.

## 1.4 Contributions

1. **A reference architecture** (Chapter 3) separating SENSE/ACT (device),
   CONTEXT/dispatch (gateway), and PREDICT (model), with a hybrid
   push/poll command protocol tolerant of intermittent hardware.
2. **A guardrail specification** (Chapter 3, Appendix B) enforced entirely
   in the gateway: servo clamp 0–90°, buzzer ≤ 10 s/hour with a
   motion-recency precondition on sirens, 30 s fan anti-short-cycle, and
   ≤ 5 tool calls per cycle.
3. **An evaluation methodology** (Chapter 5) treating the agent as a
   control component: four scripted disturbance suites (normative,
   boundary, adversarial, fallback), a weighted scoring rubric with a
   0.8 pass bar, quality gates (hallucination rate, rejection rate,
   fallback rate, p95 latency), and regression diffs between runs.
4. **A working open system**: ~5,200 lines of gateway, simulator, eval,
   and frontend code; 88 automated tests; a live dashboard; and a
   defense-ready demo (thesis/defense/).

## 1.5 Roadmap

Chapter 2 situates the work among LLM agents, tool use, and embedded
control. Chapter 3 presents the design and its threat model. Chapter 4
describes the implementation and engineering process. Chapter 5 evaluates
the system against its specification. Chapter 6 concludes with findings
and future work. The thesis closes with its **defense**: slides, a live
demo runbook, and prepared answers to committee questions.
