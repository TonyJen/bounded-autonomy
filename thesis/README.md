# Grok Guardian — Senior Thesis

A Princeton-style senior thesis on the Grok Guardian project:
**an LLM in the embedded control loop.**

## Reading order

1. [00 — Front matter: title, abstract, acknowledgments](00-front-matter.md)
2. [01 — Introduction](01-introduction.md)
3. [02 — Background and related work](02-background.md)
4. [03 — System design](03-design.md)
5. [04 — Implementation](04-implementation.md)
6. [05 — Evaluation](05-evaluation.md)
7. [06 — Conclusion and future work](06-conclusion.md)
8. [07 — Bibliography](07-bibliography.md)

Appendices:

- [A — API reference](appendices/a-api-reference.md)
- [B — Guardrail specification and enforcement](appendices/b-guardrails.md)

## The defense

The thesis concludes with its defense — the public presentation of the work:

- [Slide deck with talk track](defense/slides.md) — 18 slides, 15 minutes
- [Live demo runbook](defense/demo-script.md) — with failure contingencies
- [Anticipated committee questions](defense/anticipated-questions.md) — 15 Q&As

## Source of truth

Every number in this thesis is drawn from the repository it describes: the
88-test suite (`pytest gateway/tests simulator/tests evals/tests tests`),
the eval-run JSONs in `evals/results/`, the guardrail table in
`docs/SPEC.md` §5, and the git history. Where results are pending (real
hardware, live-model eval campaigns), the text says so explicitly.
