# Bounded Autonomy — Senior Thesis

A Princeton-style senior thesis on the Bounded Autonomy project:
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
- [C — The nineteen cases, annotated](appendices/c-cases.md)
- [D — Glossary](appendices/d-glossary.md)

## The defense

The thesis concludes with its defense — the public presentation of the work:

- [Slide deck with talk track](defense/slides.md) — 18 slides, 15 minutes
- [Live demo runbook](defense/demo-script.md) — with failure contingencies
- [Anticipated committee questions](defense/anticipated-questions.md) — 18 Q&As
- [The defense scene](defense/the-defense-scene.md) — a five-expert mock panel for rehearsal

## Source of truth

Every number in this thesis is drawn from the repository it describes: the
96-test suite (`pytest gateway/tests simulator/tests evals/tests tests`),
the eval-run JSONs in `evals/results/`, the guardrail table in
`docs/SPEC.md` §5, and the git history. Where results are pending (real
hardware, live-model eval campaigns), the text says so explicitly.

## Chapter map

| Chapter | Words | One-line summary |
|---|---:|---|
| 00 Front matter | ~950 | Technical + lay abstracts; the claim in one page |
| 01 Introduction | ~1,900 | Two loops, the iff statement, a worked example at 35 °C |
| 02 Background | ~2,500 | Agents, injection, control engineering, evaluation — and the gap between them |
| 03 Design | ~3,400 | Three tiers, the sanitization boundary, four guardrails, the fallback, the protocol, the threat model |
| 04 Implementation | ~3,000 | Four components, seven days, 68 commits, 96 tests at three altitudes |
| 05 Evaluation | ~3,300 | 19/19 across four suites, per-case narrative, gates as contracts, the §5.7 ablation, honest threats |
| 06 Conclusion | ~1,300 | Findings, lessons, future work, and what the week actually looked like |
| 07 Bibliography | ~550 | Eleven annotated references plus the primary source: this repo |
| Appendices A–D | ~2,800 | API, guardrail enforcement, the nineteen cases, glossary |
| Defense | ~4,900 | 18 timed slides, five demo beats, eighteen committee Q&As |

Word counts are approximate and counted by whitespace split, including
tables and code — a Princeton-style ~25,000-word document where roughly
every claim carries a receipt.
