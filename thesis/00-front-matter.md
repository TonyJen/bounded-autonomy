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

## Abstract

Large language models have been deployed as agents over digital tools —
browsers, terminals, APIs — but rarely inside closed control loops that
act on the physical world, where a wrong decision is not a wrong sentence
but a wrong actuator. This thesis asks whether an LLM can occupy the
decision stage of a classical embedded control loop **safely**, and answers
with a working system: Grok Guardian, a room guardian built on the ELEGOO
ESP-32 Super Starter Kit, in which a Grok model decides — via function
calling — when to spin a fan, move a vent servo, light an LED, or sound a
buzzer, in response to real or simulated temperature, humidity, motion, and
light.

The central design claim is that an LLM can be embedded in a physical
control loop **if and only if prediction is separated from actuation by a
deterministic guardrail layer that the model cannot influence**. The
system realizes this as a three-tier architecture: a device tier that only
senses and actuates, a gateway tier that owns context assembly, guardrail
enforcement, and memory, and a model tier that only predicts tool calls.
The gateway clamps every servo command to 0–90°, caps the buzzer at 10
cumulative seconds per hour, enforces a 30-second anti-short-cycle on the
fan, and limits each agent cycle to five tool calls — regardless of what
the model asks for. A rule-based fallback preserves safe behavior when the
model is unreachable.

The system is evaluated with a behavior suite of 19 scripted cases across
four suites — normative, boundary, adversarial (prompt injection), and
fallback — scored on required tools, forbidden tools, and argument
validity. In deterministic mock mode the agent passes 19/19 cases with
average score 1.0, zero hallucinated tool calls, and zero guardrail
violations; 88 unit and integration tests guard the plumbing. The work
contributes (1) a reference architecture for LLM-in-the-loop embedded
systems, (2) a guardrail specification enforced outside the model's trust
boundary, and (3) an evaluation methodology that treats an LLM agent like
a control component: scripted disturbances, scored responses, and
hard gates.

## Acknowledgments

Thanks to the open-source ecosystems behind FastAPI, Pydantic, Vite, and
React; to ELEGOO for a starter kit generous enough to build a room around;
and to the xAI team for an API boring enough to build a control loop on —
which is exactly the compliment control engineers pay infrastructure.
