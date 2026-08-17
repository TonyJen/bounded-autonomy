# Thesis Defense

The defense is the final chapter of the thesis — the public presentation
of Grok Guardian, ending the work the way a Princeton senior thesis ends:
in a room, with questions.

## Contents

1. **[slides.md](slides.md)** — 18-slide deck with full talk track and
   minute-by-minute timing (15 min presentation, 10 min Q&A).
2. **[demo-script.md](demo-script.md)** — live demo runbook: pre-flight
   checklist, five narrated beats (heat spike → night intruder → fallback
   → injection → the commit gate), and a contingency table for when the
   demo gods object.
3. **[anticipated-questions.md](anticipated-questions.md)** — 15 committee
   questions with prepared 45–90 second answers, hardest first.

## Run of show

| Time | Segment |
|---|---|
| 0:00–15:00 | Slides 1–18 (demo is slide 14, beats 1–4) |
| 15:00–15:15 | Demo beat 5: mock eval gate, live in the terminal |
| 15:15–25:00 | Committee Q&A — Agent view left running behind you |

## The argument of the defense, in one paragraph

If the committee remembers nothing else, they should remember this:
the thesis claims safety comes from a deterministic boundary, and the
defense *demonstrates the boundary doing its job in real time* — a fan
commanded across a threshold (beat 1), a siren refused for lack of a
physical precondition (beat 2), a room kept safe with the model dead
(beat 3), and an injection attempt destroyed by type coercion (beat 4).
Every beat is chosen so the safety mechanism, not the model's cleverness,
is the protagonist. The slides argue; the demo exhibits; the Q&A
[answers](anticipated-questions.md) defend. Three legs, one stool.

## Rehearsal checklist

- [ ] Full run-through twice, timed, from a cold boot of all three terminals
- [ ] Screen-record a full backup demo during rehearsal (contingency)
- [ ] Verify `pytest … -q` → 88 passed on defense morning
- [ ] Verify `.env` key is valid with one `--mode live` case
- [ ] Tabs pre-opened: Device / Agent / Evals views, `/docs`, SPEC §5,
      latest JSON in `evals/results/`
- [ ] Backup slides B1–B5 accessible (system prompt, sanitizer, guardrail
      code, run JSON, commit log)
- [ ] Printed copy of [anticipated-questions.md](anticipated-questions.md)
      in the bag — paper doesn't need Wi-Fi
