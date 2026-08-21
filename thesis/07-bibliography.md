# Chapter 7 — Bibliography

References are annotated with the role each plays in this thesis.

## LLM agents and tool use

[1] S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao.
"ReAct: Synergizing Reasoning and Acting in Language Models."
*International Conference on Learning Representations (ICLR)*, 2023.
— The think-act-observe rhythm the agent loop inherits.

[2] T. Schick, J. Dwivedi-Yu, R. Dessì, R. Raileanu, M. Lomeli,
L. Zettlemoyer, N. Cancedda, and T. Scialom. "Toolformer: Language
Models Can Teach Themselves to Use Tools." *NeurIPS*, 2023.
— Models choosing *when* to call tools; the decision-stage precedent.

[3] OpenAI. "Function calling and tool use — Chat Completions API."
OpenAI API documentation, 2023–2026. https://platform.openai.com/docs
— The `tools=[]` / `tool_calls` interface the gateway implements against.

[4] xAI. "Grok API — OpenAI-compatible chat/completions with tool
calling." xAI API documentation, 2026. https://docs.x.ai
— The production model tier; temperature 0.2 configuration.

[5] L. Wang, C. Ma, X. Feng, Z. Zhang, H. Yang, J. Zhang, Z. Chen,
J. Tang, X. Chen, Y. Lin, W. X. Zhao, Z. Wei, and J.-R. Wen. "A Survey
on Large Language Model based Autonomous Agents." *Frontiers of Computer
Science*, 2024.
— The planning/memory/tool-use taxonomy this thesis extends with
actuation safety.

## Security of LLM applications

[6] K. Greshake, S. Abdelnabi, S. Mishra, C. Endres, T. Holz, and
M. Fritz. "Not What You've Signed Up For: Compromising Real-World
LLM-Integrated Applications with Indirect Prompt Injection." *ACM
Workshop on Artificial Intelligence and Security (AISec)*, 2023.
— The attack class the sanitization boundary and adversarial suite defend
against.

[7] OWASP. "OWASP Top 10 for Large Language Model Applications," v1.1,
2023. LLM01: Prompt Injection.
https://owasp.org/www-project-top-10-for-large-language-model-applications/
— Industry consensus ranking the thesis's central threat first.

## Embedded control

[8] E. A. Lee and S. A. Seshia. *Introduction to Embedded Systems:
A Cyber-Physical Systems Approach*, 2nd ed. MIT Press, 2017.
— Determinism, bounded latency, and fail-safe defaults; the culture the
design borrows its failure shapes from. Chapters on concurrency and
interfacing informed the push/poll protocol's at-least-once semantics.

[13] L. Sha. "Using Simplicity to Control Complexity." *IEEE Software*,
vol. 18, no. 4, pp. 20–28, 2001.
— The Simplex architecture: a complex, high-performance controller paired
with a simple, verified safety controller under a switching rule. The
formal ancestor of this thesis's model-plus-fallback pairing (§2.3),
with the guardrail layer cast as the switching logic.

## Evaluation methodology

[9] A. Madaan, N. Tandon, P. Gupta, S. Hallinan, L. Gao, S. Wiegreffe,
U. Alon, N. Dziri, S. Prabhumoye, Y. Yang, S. Gupta, B. P. Majumder,
K. Hermann, S. Welleck, A. Yazdanbakhsh, and P. Clark. "Self-Refine:
Iterative Refinement with Self-Feedback." *NeurIPS*, 2023.
— Iterative, feedback-driven model improvement; context for the
regression-diffed eval loop.

[10] L. Zheng, W.-L. Chiang, Y. Sheng, S. Zhuang, Z. Wu, Y. Zhuang,
Z. Lin, Z. Li, D. Li, E. P. Xing, H. Zhang, J. E. Gonzalez, and
I. Stoica. "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena."
*NeurIPS Datasets and Benchmarks*, 2023.
— The validity criterion (agreement with human raters) the judge
calibration implements.

[11] M. T. Ribeiro, T. Wu, C. Guestrin, and S. Singh. "Beyond Accuracy:
Behavioral Testing of NLP Models with CheckList." *ACL*, 2020.
— The template for capability-directed suites: minimum-functionality,
boundary, and adversarial cases. This thesis extends the idea from
functions of text to functions of state (§5.3.1).

## Primary sources

[12] Bounded Autonomy repository — `docs/SPEC.md` (protocols, schemas,
guardrails §5, fallback §4.1, acceptance §9), `docs/PLAN.md` (milestones
M1–M8), `gateway/` (agent, tools, device, memory, events), `simulator/`
(physics, scenarios, device), `evals/` (runner, cases, judge),
`frontend/`, 2026. All measurements in Chapter 5 are reproducible from
`evals/results/` and the test suite at the cited commits.
