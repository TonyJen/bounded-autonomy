# Grok Guardian: An LLM in the Embedded Control Loop

**Tony Jen**

A Senior Thesis submitted in partial fulfillment of the requirements
for the degree of Bachelor of Science in Engineering

Department of Computer Science
Princeton University

August 2026

*Adviser: [Adviser name]*
*Second reader: [Reader name]*

---

> *"The most dangerous phrase in engineering is 'the model will handle it.'"*

---

## Abstract

Large language models have been deployed as agents over digital tools —
browsers, terminals, code repositories, APIs — but only rarely inside
closed control loops that act on the physical world, where a wrong
decision is not a wrong sentence but a wrong actuator: a motor
short-cycled to death, a siren fired at three in the morning, a room left
hot while a model retries a malformed call. This thesis asks whether an
LLM can occupy the decision stage of a classical embedded control loop
**safely**, and answers the question by construction: Grok Guardian, a
room guardian built on the ELEGOO ESP-32 Super Starter Kit, in which a
Grok model decides — through OpenAI-compatible function calling — when to
spin a fan, move a vent servo, light an LED, display text, or sound a
buzzer, in response to real or simulated temperature, humidity, motion,
and light.

The central design claim is that an LLM can be embedded in a physical
control loop **if and only if prediction is separated from actuation by a
deterministic guardrail layer that the model cannot influence**, and if a
non-LLM fallback preserves safe behavior whenever the model is absent.
The system realizes this claim as a three-tier architecture. A device
tier — the ESP-32, or its software twin, a physics-driven simulator —
only senses and actuates; it cannot parse a prompt and therefore cannot
be prompt-injected. A gateway tier owns context assembly, tool dispatch,
persistent memory, and guardrail enforcement. A model tier — xAI's Grok —
only predicts tool calls against a typed schema.

Every safety property is implemented on the trusted side of the boundary.
The gateway sanitizes sensor input before the model ever sees it, clamps
every servo command to 0–90°, caps the buzzer at ten cumulative seconds
per hour with a motion-recency precondition on sirens, enforces a
thirty-second anti-short-cycle window on the fan, and bounds each agent
cycle to five tool calls — regardless of what the model asks for. When
the model call fails or times out, a deterministic rule table takes over;
it is deliberately *less* capable than the model, so that degradation
fails quiet rather than loud.

The system is evaluated the way a control component is evaluated: with
scripted disturbances, scored responses, and hard gates. A behavior suite
of nineteen scripted cases across four suites — normative, boundary,
adversarial prompt injection, and fallback — is replayed through the real
agent path and scored on required tools present, forbidden tools absent,
and argument validity. In deterministic mock mode the agent passes 19/19
cases with an average score of 1.000, zero hallucinated tool calls in 32
dispatched calls, zero guardrail violations, and a p95 cycle latency of
9.4 ms against a ten-second budget; 96 unit and integration tests guard
the plumbing, and a pre-commit gate re-proves both suites on every
commit. An ablation campaign then measures which layer carries the
safety case: against a deliberately compromised model that obeys any
injection it can see, the adversarial suite still passes with the
prompt's safety sentences deleted — and fails wholesale with the
sanitization boundary removed. A live-mode campaign against the
production model, with enforced
quality gates and an LLM judge calibrated against human labels, is staged
and reported as future work rather than borrowed as a result.

### Lay summary

Smart devices today follow fixed rules; AI agents today act only on
screens. This work connects them: an AI that runs a physical room. The
obvious worry — what stops the AI from blaring the alarm because a
website told it to? — is answered with an architectural trick rather
than a hope: the AI is never allowed to touch anything directly. Every
action it suggests passes through a small, rigid gatekeeper program that
enforces physical limits (the vent only opens so far), budgets (the alarm
can sound for ten seconds an hour, and only right after real motion), and
sanity (no more than five actions per decision). If the AI goes offline,
a simple thermostat-style rule set quietly takes over. The whole system
is tested the way bridges are tested — with scripted loads it must
survive — and every test runs again on every change to the code. The
conclusion: you can have an AI's judgment in a physical system, as long
as someone else holds the keys.

The work contributes four things: (1) a reference architecture for
LLM-in-the-loop embedded systems that makes the trust boundary explicit;
(2) a guardrail specification enforced entirely outside the model's
influence, small enough to audit in one sitting; (3) an evaluation
methodology — behavioral hardware-in-the-loop testing for an LLM — with
regression diffs and CI-grade gates; and (4) a working open system of
roughly five thousand lines across gateway, simulator, evaluation
harness, and a live dashboard, defended publicly at the end of this
document.

## Acknowledgments

Thanks to the open-source ecosystems behind FastAPI, Pydantic, SQLite,
Vite, and React — infrastructure boring enough to build a control loop
on, which is exactly the compliment control engineers pay their
dependencies. Thanks to ELEGOO for a starter kit generous enough to build
a room around, and to xAI for an API that stayed out of the way. Thanks
to everyone who reviewed early drafts of the guardrail table and asked
the only question that mattered: *and what happens when it lies to you?*
This thesis is the answer.

## Declaration

This thesis represents my own work in accordance with University
regulations. All third-party libraries are identified where used; all
results are reproducible from the repository this document ships with.
