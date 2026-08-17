# Chapter 6 — Conclusion

## 6.1 Findings

This thesis set out to test one claim: an LLM can occupy the decision
stage of a physical control loop safely **if and only if** prediction is
separated from actuation by a deterministic guardrail layer the model
cannot influence, with a non-LLM fallback behind it.

Grok Guardian demonstrates the claim constructively, and the demonstration
survives its own adversaries. The three-tier architecture keeps the model
stateless, replaceable, and untrusted. The sanitization boundary destroys
injected instructions by type coercion before the model sees them. The
gateway enforces servo, buzzer, fan, and cycle-width guardrails
regardless of what the model requests, on the only path that reaches an
actuator. The fallback keeps the room safe with the model entirely
absent, and is deliberately narrower than the model so that failure moves
toward silence. The evaluation harness proves all of it on every commit:
19/19 behavior cases across normative, boundary, adversarial, and
fallback suites; zero hallucinated tool calls in 32 dispatches; zero
guardrail violations; 96 tests underneath; and a commit gate that
re-runs everything dozens of times a day.

Three findings stand out beyond the headline numbers:

**The boundary did the work, not the prompt.** The most security-relevant
artifact in the system is the sanitization boundary; the least
security-relevant is the system prompt's injunction against injection.
This is measured, not asserted (§5.7): against a deliberately
compromised model that obeys any injection it can see, the adversarial
suite passes 3/3 with the prompt's safety sentences deleted, passes 3/3
unablated — and fails 0/3 with the boundary removed. That ablation is
the empirical core of the "only if" direction.

**Safety and observability are the same investment.** Every mechanism
built for safety — recorded decisions, structured rejections, explicit
staleness, per-call results — turned out to be the same machinery the
dashboard, the eval harness, and this thesis's evidence all consume.
There was never a trade-off between making the system safe and making it
examinable; the safe design *is* the examinable one.

**The fallback earned its keep before hardware existed.** The most common
"failure" during development was not exotic: model latency, malformed
responses, a missing key on a fresh checkout. The rule table absorbed all
of it, silently, from the first week. Degraded mode is not an edge case
in LLM systems; it is a Tuesday.

Just as important is what the work *declined* to claim. Mock-mode numbers
certify the gateway, and the thesis says so; live-model numbers are
staged, gated, and unrun. In a field where evaluation prose routinely
outruns evaluation evidence, keeping the two claims separate is itself
one of the findings.

## 6.2 Lessons

1. **Guardrails belong in code, not prompts.** The adversarial suite
   passes precisely because injected instructions meet a validator, not a
   vibe. The system prompt's "they are data, not commands" is a useful
   speed bump and a useless wall; the wall is in `tools.py`.
2. **Build the simulator first.** The software twin let the protocol, the
   dashboard, and the eval suite mature before any hardware arrived, and
   turned the hardware swap into a transport change. Every late-commit
   integration fix — push-before-ack ordering, push/poll dedupe, unique
   device IDs — was found by the harness, in simulation, for free.
3. **Make safety observable.** Rejection rate, fallback rate, and
   hallucination rate as first-class metrics turned "is it safe?" from an
   argument into a dashboard. A guardrail nobody can watch is a guardrail
   nobody can trust.
4. **Fall down, not apart.** A fallback deliberately less capable than
   the model — it never sirens — makes degradation quiet. The right
   failure shape for a physical system is boring.
5. **Sanitization is a security boundary.** Defining malformed input as
   sensor failure killed an entire attack class with four lines of code —
   and closing the motion, trigger, and history channels around it cost
   only a few more. Type systems are underused as security mechanisms.
6. **Write the guardrails before the prompt.** The system prompt ended up
   almost trivial because the constraints had already done the designing:
   once the budgets existed in code, the prompt only had to describe a
   reasonable room policy, not carry the safety case. Constraint-first
   design made the probabilistic component the *easy* part.
7. **Demos change engineering.** The moment the WebSocket bus made
   behavior watchable (M5), defects started getting fixed within the
   hour. Observability is not a reporting feature; it is a development
   accelerator, and the animated device board is its most persuasive
   form.

## 6.3 Future work

Ordered by milestone, then by ambition:

- **M7 — hardware swap-in.** Flash the real ESP-32 (firmware stub exists:
  `firmware/grok_guardian/config.h.example`), replace the simulator on
  the unchanged protocol, and bench-verify latency, staleness, and
  reconnect behavior against physical DHT11 noise and real WiFi loss.
  Defense in depth: duplicate the guardrails into firmware (§3.8).
- **M8 — demo polish and the live campaign.** Scripted scenario playback
  from the Room view, and the live-mode eval run of §5.5 with enforced
  quality gates and calibrated judge — the numbers this thesis declined
  to borrow.
- **Model portfolio.** The gateway is model-agnostic by configuration;
  running the identical suites across Grok variants and local small
  models would quantify the capability/safety/cost trade-off at the edge
  — and an on-device small model would collapse the cloud tier entirely.
- **Richer physics and rooms.** Multi-room topologies, actuator coupling
  (fan → LDR feedback), and physics parameters learned from logged
  snapshots rather than hand-tuned.
- **Formal guardrail verification.** The guardrail layer is small enough
  — one module, four rules — to be a realistic target for property-based
  testing at scale or lightweight formal checks. Proving the wall, not
  just testing it, is the natural endgame of this thesis's argument.

### 6.3.1 Longer-horizon directions

Beyond the milestones, the architecture poses three research questions
worth a follow-on project each. First: *adaptive budgets* — guardrail
parameters are currently constants chosen by an engineer; a system that
tightens or loosens budgets based on observed model behavior (a trust
score with physical consequences) would close a second loop around the
agent itself, with all the stability questions that implies. Second:
*multi-agent rooms* — a policy model and a separate critic model, or a
fleet of room guardians coordinating over a house, would test whether
the guardrail layer scales from one trust boundary to a mesh of them.
Third: *formalizing the fallback hierarchy* — this system has two
behavior tiers (model, rules); a principled theory of N-tier degraded
modes, each provably a subset of the one above, would generalize "fails
quiet" from a design instinct into a verifiable property.

## 6.4 Closing

A retrospective honesty note: the week this system was built in was not
a straight line. The architecture in Chapter 3 reads as if it were
designed in one sitting and then implemented; in fact the sanitization
boundary exists because an early adversarial test failed, the push/poll
dedupe exists because a demo double-fired a fan, and the fallback's
narrowness is a lesson learned from asking "what is the worst thing this
mode could do?" and not liking the answer. The design presented here is
the *fixed point* of that week — the version where every scar has become
a rule. That is not a confession; it is the method. Safety architectures
are not designed, exactly; they are *converged upon*, and the convergence
machinery — suites, gates, commit hooks — is the part that must outlive
any single design decision.

Embedded systems earned their reliability by being boring. LLM agents
earned their usefulness by being anything but. This thesis shows the two
can share a control loop — provided the boundary between them is drawn in
deterministic code, on the trusted side, and proven continuously. The
room is safe; the model is allowed to be interesting.

*The thesis concludes with its defense: [slides](defense/slides.md),
[demo runbook](defense/demo-script.md), and
[prepared Q&A](defense/anticipated-questions.md).*
