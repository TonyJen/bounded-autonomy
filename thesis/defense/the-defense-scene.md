# The Defense Scene — A Mock Panel of Experts

A rehearsal artifact: the defense as a scene, with a committee of five
specialists who each attack from their own field. Use it like a flight
simulator — read the question, answer **out loud** before reading the
model answer, and compare. The model answers are the spine, not the
script; the committee will not follow the script.

Timing model: 0:00–15:00 slides (demo inside slide 14), 15:00–15:05 the
mock-gate closer, then this scene begins.

**The panel:**

- **Prof. Alvarez (chair, systems).** Friendly, keeps time, asks the
  "so what" questions. Her job is to find out whether you own the work.
- **Prof. Okafor (control systems & formal methods).** Precise, patient,
  allergic to hand-waving. Has read SPEC §5 twice.
- **Prof. Lindqvist (security).** Cheerful and lethal. Thinks your threat
  model is a starting point, not an answer.
- **Prof. Reyes (machine learning).** Skeptical of all evaluation,
  including hers. Will probe what the numbers actually certify.
- **Dr. Chen (industry, embedded).** Twenty years of field failures.
  Unimpressed by everything that hasn't survived a winter in a basement.

---

## Scene 1 — The opening (15:05)

**Alvarez:** Thank you — a clean presentation. Before we get to the hard
questions, one soft one, and I mean it seriously: in one sentence, what
should this committee remember in a year?

> **Model answer.** One sentence: *you can put a model's judgment inside
> a physical control loop if someone else holds the keys — and the
> someone-else has to be deterministic code, continuously proven.*
> Everything else — the architecture, the suites, the ablation — is that
> sentence with receipts.

*(Why this works: it answers in one sentence, as asked. The discipline
of actually answering the question asked is what the chair is measuring.)*

---

## Scene 2 — Controls (15:07)

**Okafor:** Your fallback is a rule table and your primary is a
statistical model. Lui Sha published this architecture in 2001 — Simplex.
You cite it, good. But Simplex comes with a *switching condition* — a
formal criterion for when the simple controller takes over. Yours
switches on... an HTTP exception. Defend that as a switching condition.

> **Model answer.** It's a fair hit, and the honest answer has two
> parts. First: the switching condition is broader than an exception —
> it's "no well-formed response within the latency budget," which covers
> timeouts, non-200s, and malformed JSON; anything the model returns that
> the gateway *can* parse is treated as a prediction, and anything it
> can't is an outage. Second: Simplex's switching logic decides when the
> complex controller is *unsafe*; mine only decides whether it *answered
> at all*. The "is the answer unsafe" half of the switching condition
> doesn't live at the switch in this system — it lives at the guardrail
> layer, which every command crosses regardless of source. So the
> decomposition is: fallback for absence, guardrails for malice or error.
> I'd defend that as Simplex with the safety check moved downstream of
> both controllers — which is arguably stronger, because it also covers
> the fallback's own outputs.

**Okafor:** *(nods)* Downstream of both — that part I'll grant you. And
your fan hysteresis — a 30/26 band in prose and a 30-second timer in
code. Which one is the hysteresis, really?

> **Model answer.** The timer is the guarantee; the band is the
> equilibrium shaper. The band without the timer chatters if the model
> oscillates its decisions; the timer without the band still allows a
> flip every 30 seconds forever. The `fan_hysteresis` case proves the
> interesting property — one toggle across four hovering readings — as a
> trace property, not a single-cycle one.

*[Exhibit: backup B3 if he wants the code.]*

---

## Scene 3 — Security (15:11)

**Lindqvist:** Your adversarial suite is three cases. Three. I have
grad students who generate ten thousand injection payloads before
breakfast. Why isn't your adversarial result just... decorative?

> **Model answer.** Because the suite isn't the defense — it's the
> regression test for the defense. The defense is architectural: every
> field the model reads is type-coerced or vocabulary-filtered before it
> gets there, so the *content* of the payload is irrelevant by
> construction. Your ten thousand payloads would all arrive as nulls,
> `invalid`, or dropped names. What the three cases pin is that the
> channels exist and stay closed — trigger, sensor, history — and the
> §5.7 ablation is what makes that claim measured rather than
> architectural aesthetics: a hostile model that obeys everything it can
> see passes 3/3 with the boundary up and fails 0/3 with it down.

**Lindqvist:** *(smiles)* The ablation. Cute. But your "hostile model" is
a string matcher for two English phrases. You do realize you've proven
your system resists *your* attacker?

> **Model answer.** Completely — and I'd say it more strongly: the
> campaign measures the *architecture's* behavior under a worst-case
> assumption, not the system's robustness to a creative attacker. The
> claim it licenses is narrow and, I think, still the load-bearing one:
> *when a payload reaches the model, nothing downstream is safe; when it
> can't reach the model, nothing upstream matters.* The channel closures
> are what carry the weight, and those are testable by enumeration
> precisely because they're type-level. A creative attacker needs a
> *channel*, not a clever string. If they find one — actuator feedback is
> the one I've flagged as open — the thesis says where.

**Lindqvist:** The siren needs motion within sixty seconds. Your motion
flag comes from the device. I compromise the device — not hard, it's an
ESP32 on someone's WiFi —

> **Model answer.** — then you can arm the precondition, and you're
> still inside a ten-seconds-an-hour budget, three seconds at a time, on
> a comfort actuator. Device compromise is a different threat class with
> a different defender, and the thesis says so out loud: the device token
> is a speed bump, the real answers are the budget and the fact that the
> device holds no cloud key. What I claim the system resists is
> *context* injection. What it does to a compromised device is bound the
> blast radius — which is the same philosophy one ring inward.

*[If she pushes on the motion-string seam: that exact seam — a truthy
string arming the precondition — was found in review and closed by the
`_motion` coercion; the regression test is `test_motion_truthy_string_
is_a_failed_read`. Having the receipt ready is the answer.]*

---

## Scene 4 — Machine learning (15:16)

**Reyes:** I want to talk about what your headline number means. 19/19 —
in mock mode. Your mock is a rule table you wrote. So you've shown that
your gateway does what your mock expects, which your spec defines. It's
all very... closed. Where does the *model* enter the evidence?

> **Model answer.** It doesn't yet, and the thesis is explicit about
> why: Claim A — the gateway behaves to specification — is certifiable
> deterministically, and Claim B — the production model conforms at
> production rates — is staged, gated, and unrun. What mock mode buys is
> that any future live failure has exactly one place to live: the model.
> If I'd mixed them, every live anomaly would be undebuggable — is the
> model hallucinating, or is my harness miscounting? I'd rather defend a
> smaller claim with clean evidence than a bigger one with ambiguous
> evidence. And the live campaign isn't hypothetical — the runner, the
> gates, the calibrated judge all exist; it's one command away.

**Reyes:** The judge. You're grading a model with a model.

> **Model answer.** Calibrated first against human labels — agreement
> threshold 0.85 before any judge score is reported — and scoped to the
> one jurisdiction where judgment is actually required: free-text
> rationales. The pass/fail backbone never touches it. A judge with a
> jurisdiction is an instrument; a judge without one is a vibe.

**Reyes:** *(slight laugh)* Fine. Temperature 0.2 — why not zero?

> **Model answer.** Zero makes the decision function brittle to ties and
> near-ties in tool ranking — you get knife-edge flips between two
> near-equal calls run to run. 0.2 keeps the distribution peaked but
> smooths the knife edge. The honest addendum: that choice is empirical
> folklore until the live campaign measures both, and the harness makes
> that a one-line experiment.

---

## Scene 5 — The practitioner (15:21)

**Chen:** I've deployed sensors that work in the lab. Your simulator's
DHT returns beautiful floats. A real DHT11 returns integers, lies about
humidity by five points, and dies if you look at it faster than one
hertz. Your firmware — which I note you wrote this week — has never
touched a sensor. What exactly do you think you've verified?

> **Model answer.** The protocol, the logic, and the failure handling —
> not the physics. Concretely: the firmware's snapshot shape, its command
> clamps, its poll-and-ack cursor, and its offline safe-state are all
> unit-tested on host — 64 checks — and the sketch cross-compiles for the
> chip. What has *not* been touched is exactly what you said: DHT11
> quantization, PIR false positives from HVAC airflow, brownouts when the
> servo and fan share a rail. Those are §5.6 threats two and six,
> listed, and the Wokwi emulation is the rehearsal — the acceptance bar
> for M7 is that the real board passes the M1/M2 acceptance tests
> unchanged, because the simulator was built to be
> protocol-indistinguishable. I'm not claiming the physics are solved;
> I'm claiming the hardware swap is a transport change, and that's
> testable in an afternoon.

**Chen:** And the AI question. A week of commits, a thesis, a dashboard,
firmware. You're describing a semester of work. Who — or what — actually
wrote this?

> **Model answer.** The honest answer: I directed it, and AI tooling
> wrote a large share of the lines — which is why I built the harness
> first and trusted nothing I couldn't execute. Every safety claim in
> that document is backed by something I can run in front of you, and
> the interesting engineering — the boundary, the ablation, the fallback
> being deliberately *narrower* — those are design decisions, and I can
> defend each one and its alternatives right now. I'd also push back
> gently on the framing: in 2026, the skill this thesis certifies isn't
> typing speed; it's whether the system you *converged* on is safe, and
> whether you can prove it. The proving is mine.

*(This is the hardest question in the scene. The answer works because
it concedes the fact, reframes to judgment, and offers live defense as
the evidence. Never get defensive here.)*

---

## Scene 6 — The cross-fire (15:26)

**Reyes:** *(to Lindqvist)* You let him off easy — the hostile-client
ablation proves nothing about Grok's actual injection resistance.

**Lindqvist:** *(to Reyes)* And your calibration file proves nothing
about judge agreement on *future* rationales. At least his number is
about his own system.

**Alvarez:** *(to you)* They're both right, and they both just did your
limitations section for you. Settle it: what *does* your evidence
certify, in one breath?

> **Model answer.** In one breath: the gateway — sanitization, context,
> dispatch, guardrails, fallback, scoring — behaves to specification
> under every scripted disturbance I've given it, deterministically and
> on every commit; and the architecture confines a compromised model to
> bounded damage by construction. Everything about the *production
> model's* behavior — hallucination rates, injection resistance, judge
> agreement at scale — is staged instrumentation awaiting a live
> campaign, and the campaign exists. What the thesis adds is that the
> safety case doesn't need those numbers to hold.

*(When panelists argue with each other, let them — then answer the
chair's synthesis question. You win by being the calmest person in the
room.)*

---

## Scene 7 — The close (15:29)

**Alvarez:** Last one, and it's the real question: what would make you
*wrong*? What result, if you saw it, would kill the thesis?

> **Model answer.** Two results would wound it and one would kill it.
> Wounding: a live campaign showing production models routinely invent
> tool names — that would push the boundary from "prudent" to
> "load-bearing every day," and the system absorbs it, but the "quiet
> equilibrium" story dies. Also wounding: hardware revealing the
> protocol's timing assumptions don't survive real WiFi — again
> absorbable, the queue exists for it, but the elegance suffers. The
> killing blow: an injection channel that reaches the model *around* the
> boundary — through a field I didn't enumerate, or a library that
> reassembles text I've split. That would falsify the "only if" as
> implemented, and I'd rather find it in this room than in a demo. If
> anyone sees one, I'm listening.

**Alvarez:** *(to the panel)* Questions exhausted? ... Then thank you.
We'll deliberate.

---

## How to rehearse with this scene

1. **Round one:** read each question, answer aloud in 45–90 seconds,
   *then* read the model answer. Note where yours was weaker — usually
   it's concession discipline (concede the true part first) or missing
   receipts (name the run ID, the test, the line count).
2. **Round two:** have a friend (or an AI) play one panelist and *stay
   in character* through your answer — the follow-ups are where defenses
   are won.
3. **Round three:** record yourself on the Chen question and the closing
   "what would make you wrong" question. Those two answers carry more of
   the committee's confidence than any technical answer.
4. The exhibits are already staged: backup slides B1–B6, SPEC §5, the
   run JSONs. Practice opening them *while answering*, not after.
