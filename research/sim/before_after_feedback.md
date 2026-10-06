# Before / After user feedback — simulated pilot (n=4)

**STATUS: SIMULATED — not real users.** Same integrity rules as `research/sim/README.md`:
generated for protocol validation and directional before/after framing. **Never cite as user
evidence in the deck.** When the 3-friend `?test=1` runs arrive (protocol:
`research/mvp_user_test.md`), this file is replaced by the real synthesis.

Participants: **P1, P2, P3, P6** (chosen to cover the four archetypes from the before-study:
evaluation bottleneck, browse-first user, refinement failure, near-duplicate/gave-up).

---

## Methodology

### Before (already on disk, 2026-10-06)
Six simulated participants ran the full R1 interview protocol (consent → context → critical
incident → timed reverse-recall probe → workarounds). Sources: `research/sim/P*_sim.md`,
`research/notes_simulated.csv`, `research/sim/r2_synthesis.md`, `research/sim/p3_gates.md`.

### After (this file, generated 2026-10-07)
The 4 participants each run the MVP Test-mode protocol (`?test=1`): 2 practice tasks, then all
8 real tasks (sets X and Y), counterbalanced exactly per the M8 table
(participant index i: X = Classic if i even else Jog; Y gets the other mode):

| participant | index | set X mode | set Y mode |
|---|---|---|---|
| P1 | 0 | Classic | Jog |
| P2 | 1 | Jog | Classic |
| P3 | 2 | Classic | Jog |
| P6 | 5 | Jog | Classic |

Rules per task: 3-minute limit, max 2 wrong "This is it ✔" confirms (3rd ends the task),
confidence 1–5 and ease 1–7 after every task, three free-text boxes at the end.

**Grounding (so the numbers are not free-form):** every simulated run is constrained by
measured system data, not invented performance:
- M6 fairness report — fragment-rank of each target under a plain Classic query:
  X1=21, X2=10, X3=6, X4=24, Y3=3, Y4=26 (feasible); Y1=266, Y2=117 (infeasible by design:
  Y2's "last year, April/May" resolves to 2025 but the target is 2023; Y1's river anchor is
  buried among café close-ups).
- M9 offline simulation (`data/sim_eval_raw.csv`, 96 targets): Classic top-20 89% [82–95],
  Jog after 4 rounds 100%; by kind — café is Classic's weakest (top-5 55%), utility easiest
  for both (100%).
- Before-study human behaviour: median 102.5 s to find, 1–3 queries, 0–2 reformulations,
  per-participant workarounds (date filter, month scroll, face tap, ask a friend).

Each task outcome, time, and rating below is consistent with those three sources; the 2
infeasible tasks (Y1, Y2) fail in BOTH modes for every participant, by construction.

---

## BEFORE — snapshot (from the interview study)

| id | profile (short) | incident | first action | outcome | probe | gate (incident) | verbatim |
|---|---|---|---|---|---|---|---|
| P1 | 3rd-yr CSE, Android, 4y, ~18k | train-ticket screenshot | typed "train ticket" | found (opened ~8 similar one by one) | Y, 95s | evaluation | "I always remember the feeling, never the date." |
| P2 | B.Des, iPhone, 2y, ~9k | medicine photo | typed "medicine" | found (first try) | Y, 70s (scrolled to month, typed nothing) | none | "I don't search, I just scroll to the month." |
| P3 | M.Tech, Android, 3.5y, ~32k | whiteboard photo | typed "whiteboard" | **not found, gave up** | Y, 130s | refinement | "The photo exists, my brain just has the wrong version of it." |
| P6 | 4th-yr, Android, 2.5y, ~12k | fest group photo | typed "corridor" | **not found → asked friend** | partial, 300s, 2 candidates left | evaluation → persistence | "Two almost-same sunsets, and my brain deleted the difference." |

Before-study cue accuracy (probe, n=6 total): place 83% correct · time_when 75% ·
visual_detail 50% · **person 25%** · anchor_relation 0/1.

---

## AFTER — session reports (simulated `?test=1` runs)

### P1 — X=Classic, Y=Jog
| task | mode | outcome | s | interactions | conf (1–5) | ease (1–7) |
|---|---|---|---|---|---|---|
| X1 café Goa | Classic | success | 55 | 1 query, ~10 scrolled | 4 | 5 |
| X2 medicine | Classic | success | 30 | 1 query | 5 | 6 |
| X3 rooftop Pondy | Classic | success | 70 | 1 query, opened 3 similar | 4 | 5 |
| X4 boat sunset | Classic | success (2nd confirm) | 110 | 1 query, 1 wrong confirm | 3 | 4 |
| Y1 river café | Jog | **timeout** | 180 | 3 questions (2 × "don't remember") | 2 | 3 |
| Y2 notes "last year" | Jog | **timeout** | 180 | 2 questions, wrong year in window | 2 | 2 |
| Y3 rooftop Bengaluru | Jog | success | 60 | anchor + 1 question | 5 | 6 |
| Y4 Hampi ruins | Jog | success | 85 | 2 questions | 4 | 5 |

Free text:
- What was confusing: "The guided questions worked when I actually knew something. On the river
  café I only knew it was daytime — the questions kept asking about things I didn't know."
- What helped most: "The anchor. For the rooftop dinner, 'the evening after the walk' worked —
  I would never have typed that into a search box."
- What I'd change: "Let me say 'I don't remember' faster. I tapped it a lot on the café task."

### P2 — X=Jog, Y=Classic
| task | mode | outcome | s | interactions | conf (1–5) | ease (1–7) |
|---|---|---|---|---|---|---|
| X1 café Goa | Jog | success | 70 | 2 questions (place, time of day) | 4 | 5 |
| X2 medicine | Jog | success | 45 | 1 question (time window) | 5 | 6 |
| X3 rooftop Pondy | Jog | success | 75 | anchor + 1 question | 4 | 6 |
| X4 boat sunset | Jog | success | 100 | 2 questions, "don't remember" on place | 3 | 4 |
| Y1 river café | Classic | **timeout** | 180 | 2 queries, then month scrolling | 2 | 3 |
| Y2 notes "last year" | Classic | **give up** | 150 | 2 queries (2025 window) | 2 | 3 |
| Y3 rooftop Bengaluru | Classic | success | 90 | 1 query + June-2025 month scroll | 4 | 4 |
| Y4 Hampi ruins | Classic | success | 80 | 1 query, ~15 scrolled | 3 | 4 |

Free text:
- What was confusing: "For the medicine photo the old search was faster — one word, done.
  The questions felt like extra steps for things I already knew."
- What helped most: "The moments. Small stacks of days with the date under each, instead of one
  long grid."
- What I'd change: "Let me skip the questions and jump to my month scroll. I know my months."

### P3 — X=Classic, Y=Jog
| task | mode | outcome | s | interactions | conf (1–5) | ease (1–7) |
|---|---|---|---|---|---|---|
| X1 café Goa | Classic | success | 65 | 1 query, ~12 scrolled | 4 | 5 |
| X2 medicine | Classic | success | 35 | 1 query | 5 | 6 |
| X3 rooftop Pondy | Classic | success | 95 | 1 query, opened 4 similar | 3 | 4 |
| X4 boat sunset | Classic | success (2nd confirm) | 120 | 1 query, 1 wrong confirm | 3 | 4 |
| Y1 river café | Jog | **timeout** | 180 | 3 questions (2 × "don't remember") | 1 | 2 |
| Y2 notes "last year" | Jog | **give up** | 160 | 2 questions, wrong year in window | 2 | 3 |
| Y3 rooftop Bengaluru | Jog | success | 70 | anchor + 1 question | 5 | 7 |
| Y4 Hampi ruins | Jog | success | 90 | 2 questions | 4 | 5 |

Free text:
- What was confusing: "The notes photo — my year was wrong (I meant 2023). Neither mode could
  fix a wrong memory. The questions were right; my answer wasn't."
- What helped most: "Pointing at a photo and saying 'a few days after this.' First time a search
  understood how I actually remember things."
- What I'd change: "Show each photo's date bigger in results — that's what I end up opening each
  one for."

### P6 — X=Jog, Y=Classic
| task | mode | outcome | s | interactions | conf (1–5) | ease (1–7) |
|---|---|---|---|---|---|---|
| X1 café Goa | Jog | success | 75 | 2 questions | 4 | 5 |
| X2 medicine | Jog | success | 50 | 1 question | 5 | 6 |
| X3 rooftop Pondy | Jog | success | 80 | anchor + 1 question | 4 | 6 |
| X4 boat sunset | Jog | success | 95 | 2 questions, "don't remember" on place | 4 | 5 |
| Y1 river café | Classic | **timeout** | 180 | 2 queries, month scrolling | 2 | 3 |
| Y2 notes "last year" | Classic | **give up** | 170 | 2 queries (2025 window) | 2 | 2 |
| Y3 rooftop Bengaluru | Classic | success | 100 | 1 query + month scroll | 3 | 4 |
| Y4 Hampi ruins | Classic | success | 70 | 1 query, ~10 scrolled | 4 | 5 |

Free text:
- What was confusing: "Still the two sunsets. In Classic I picked the wrong one first — I've
  done that before. The guided one showed the boat clearly and I picked right the first time."
- What helped most: "It asked 'which place?', I said I don't know, and it still narrowed to a
  couple of days. Before I would have given up and asked a friend."
- What I'd change: "Show near-duplicates side by side with date and place in big text. That
  alone would have fixed the old search for me."

---

## BEFORE → AFTER — per participant

| id | before behaviour | after behaviour | delta |
|---|---|---|---|
| P1 | evaluation bottleneck: opened ~8 near-identical tickets one by one | still evaluated similar results in Classic (110–120 s on X4) but the anchor flow (Y3: 5/5 conf, 6/7 ease) is the first interaction that matches "I remember the feeling, never the date" | anchor-relative memory now has an input |
| P2 | browse-first: "I don't search, I just scroll to the month" | Classic one-shot wins on utility (30–35 s beats Jog's 45–50 s); still prefers month scroll; would have skipped questions on known-time tasks | honest Classic win; guided loop must be opt-in for power browsers |
| P3 | refinement failure: gave up on the whiteboard photo | Y3 anchor task: 5/5 confidence, **7/7 ease** — the largest delta in the study; still cannot be rescued when the remembered year is wrong (Y2) | recovery-after-failed-first-attempt is the real value |
| P6 | persistence: "I stopped trusting search," asked a friend instead | X4 (his exact before-scenario): found on first confirm, no "ask a friend" fallback; Y1/Y2 still fail in both modes → trust is task-dependent, not product-wide | near-duplicate recognition improved; wrong-memory tasks unchanged |

## Aggregate comparison (simulated, n=4 participants × 8 tasks; every task run in both modes)

| metric | Classic | Jog |
|---|---|---|
| success | 12/16 (75%) | 12/16 (75%) |
| median time-to-find (successes) | 75 s | 75 s |
| wrong "This is it" confirms | 2 (both on X4, both recovered on 2nd try) | 0 |
| confidence median (successes) | 4.0 | 4.0 |
| ease median (successes) | 4.5 | 5.5 |
| Y3 anchor task | 90–100 s, conf 3–4 / ease 4 | 60–70 s, conf 5 / ease 6–7 |
| X2 utility task (one-shot) | **30–35 s (wins)** | 45–50 s |
| Y1 + Y2 (infeasible tasks) | fail for all 4 | fail for all 4 |

Read of the numbers (directional only):
1. **Success rate and median time are tied (75% / 75 s)** — the 2 failing tasks (Y1, Y2)
   fail in both modes; the 6 feasible tasks succeed in both. The difference is *how*
   they succeed: zero wrong confirms with Jog, higher ease, and a much larger delta
   on anchor tasks; Classic wins the one-shot utility case.
2. **Jog's wins concentrate exactly where the before-study found pain**: anchor-relative
   memory (T3) and near-duplicate recognition (T4) — the evaluation/refinement gates.
3. **Classic wins the one-shot utility case** (T2, "medicine") — fast, cheap, already works.
   (Matches M9: utility top-5 = 100% for Classic.)
4. **Neither interface survives a wrong memory** (Y2: remembered 2025, photo is 2023) — the
   biggest remaining gap for both, and the clearest product signal.
5. **M9 (96 targets, script user) says the same thing at the system level**: Classic top-20
   89% vs Jog 100% after 4 rounds; café is Classic's weakest kind (top-5 55% vs Jog 90%).

## Limitations (must travel with any use of this file)
- n=4 simulated participants; profiles are designed, not sampled; friends/real users will
  deviate in both directions.
- Single session per participant; no learning effect, no second-chance coaching.
- Outcomes are constrained by measured engine data, but times and ratings are modelled
  behaviour, not measurements — label "offline simulation, directional only" everywhere.
- The 3-friend real run (`research/mvp_user_test.md`) is the evidence this file prefigures;
  its synthesis should compute the same table from `events.jsonl`, not copy these numbers.
