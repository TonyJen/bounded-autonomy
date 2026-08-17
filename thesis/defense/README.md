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

## Rehearsal checklist

- [ ] Full run-through twice, timed, from a cold boot of all three terminals
- [ ] Screen-record a full backup demo during rehearsal (contingency)
- [ ] Verify `pytest … -q` → 88 passed on defense morning
- [ ] Verify `.env` key is valid with one `--mode live` case
- [ ] Tabs pre-opened: Device / Agent / Evals views, `/docs`, SPEC §5,
      latest JSON in `evals/results/`
