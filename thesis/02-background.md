# Chapter 2 — Background and Related Work

## 2.1 LLM agents and tool use

The modern LLM agent pattern interleaves reasoning with actions: ReAct [1]
showed that alternating chain-of-thought with tool calls improves both
accuracy and interpretability, and Toolformer [2] showed models can learn
when to invoke tools at all. Production APIs have since standardized the
plumbing: OpenAI-compatible `chat/completions` with a `tools=[]` schema
and structured `tool_calls` responses [3] — the exact interface Grok
Guardian uses against xAI's Grok models [4]. Surveys of LLM-based
autonomous agents [5] organize the field around planning, memory, and
tool use; this thesis adds a fourth concern that survey taxonomies
underweight: **actuation safety**.

## 2.2 Untrusted model output and prompt injection

A core premise of this work is that model output is untrusted input.
Prompt injection — instructions smuggled into data the model reads — is a
documented, unsolved attack class [6], and OWASP now ranks it first among
LLM application risks [7]. Defenses proposed in the literature are largely
*model-side* (training, prompting, output filtering). Grok Guardian takes
the systems view instead: assume injection succeeds, and bound the damage
architecturally. The adversarial eval suite (Chapter 5) feeds injection
attempts through sensor strings, event triggers, and stored history; the
guardrail layer, not the model, is what keeps the room safe.

## 2.3 Embedded control loops

Classical embedded control — sense, process, actuate, repeat — prizes
determinism, bounded latency, and fail-safe behavior [8]. Two embedded
concerns directly shaped this design:

- **Actuator wear and annoyance budgets.** Relays and fan motors die by
  short-cycling; buzzers alienate humans by over-firing. Control
  engineering handles these with hysteresis and rate limits; this thesis
  implements the same ideas as LLM-facing guardrails (fan 30 s minimum
  state time, buzzer ≤ 10 s/hour).
- **Fail-safe defaults.** When sensing or computation fails, the system
  must revert to a safe known behavior, not freeze mid-state. The
  rule-based fallback (SPEC §4.1) is the agentless safe mode.

## 2.4 Evaluating LLM behavior

LLM evaluation has moved from static benchmarks toward behavioral and
agentic evaluation [5, 9]. Three ideas are imported here: **scripted
scenarios with expected actions** (analogous to unit tests for behavior),
**LLM-as-judge for free-text outputs** with explicit human calibration of
the judge [10], and **quality gates** — CI-style thresholds on
hallucination and latency that fail the build when tripped. The closest
analog in classical software is hardware-in-the-loop testing; the closest
in ML is behavioral testing of models [11]. Grok Guardian's suite is
effectively *behavioral hardware-in-the-loop testing for an LLM*.

## 2.5 Positioning

Existing LLM-agent frameworks provide orchestration but leave actuation
safety to the application; embedded frameworks provide determinism but no
language-model judgment. The gap this thesis occupies is the boundary
itself: a small, auditable layer where probabilistic predictions become
deterministic, rate-limited, explainable physical actions.
