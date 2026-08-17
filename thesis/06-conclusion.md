# Chapter 6 — Conclusion

## 6.1 Findings

This thesis set out to test one claim: an LLM can occupy the decision
stage of a physical control loop safely **if and only if** prediction is
separated from actuation by a deterministic guardrail layer the model
cannot influence, with a non-LLM fallback behind it.

Grok Guardian demonstrates the claim constructively. The three-tier
architecture keeps the model stateless and untrusted; the gateway enforces
servo, buzzer, fan, and cycle-width guardrails regardless of what the
model requests; the fallback keeps the room safe with the model entirely
absent; and the evaluation harness proves all of it on every commit. The
system passed 19/19 behavior cases across normative, boundary,
adversarial, and fallback suites with zero hallucinated tool calls,
guarded by 88 tests and a commit gate that re-proves safety on every
change.

## 6.2 Lessons

1. **Guardrails belong in code, not prompts.** The adversarial suite
   passes precisely because injected instructions meet a validator, not a
   vibe.
2. **Build the simulator first.** The software twin let the entire
   protocol, dashboard, and eval suite mature before any hardware
   arrived, and turned the M7 hardware swap into a transport change.
3. **Make safety observable.** Rejection rate, fallback rate, and
   hallucination rate as first-class metrics turned "is it safe?" from an
   argument into a dashboard.
4. **Fall down, not apart.** A fallback that is deliberately *less*
   capable than the model (it never sirens) makes degradation quiet —
   the right failure shape for physical systems.

## 6.3 Future work

- **M7 — hardware swap-in.** Flash the real ESP-32 (firmware stub exists:
  `firmware/grok_guardian/config.h.example`), replace the simulator on
  the same protocol, and bench-verify latency and staleness behavior.
- **M8 — demo polish.** Scripted scenario playback from the Room view and
  the live-mode eval campaign of §5.5 with enforced quality gates.
- **Model portfolio.** The gateway is model-agnostic; comparing Grok
  against local small models on the same suites would quantify the
  capability/safety trade-off at the edge.
- **Richer physics and rooms.** Multi-room topologies, actuator coupling
  (fan → LDR), and learned physics from logged snapshots.
- **Formal guardrail verification.** The guardrail layer is small enough
  (one module, four rules) to be a realistic target for property-based
  testing or lightweight formal checks.

## 6.4 Closing

Embedded systems earned their reliability by being boring. LLM agents
earned their usefulness by being anything but. This thesis shows the two
can share a control loop — provided the boundary between them is drawn in
deterministic code, on the trusted side, and proven continuously. The
room is safe; the model is allowed to be interesting.

*The thesis concludes with its defense: [slides](../thesis/defense/slides.md),
[demo runbook](../thesis/defense/demo-script.md), and
[prepared Q&A](../thesis/defense/anticipated-questions.md).*
