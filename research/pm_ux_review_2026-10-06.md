# PM/UX dissection — Jog MVP + Discovery Engine (2026-10-06)

Method: read every screen/flow end-to-end; for each element ask: why is it here?
is it worth a click? can it be merged/removed? does it show the user anything they
cannot use? What is missing that a user would expect?
Constraints respected: test-contract labels/keys/log events unchanged; engine untouched.

## JOG MVP (space_jog/app.py)

### Verdict per screen
1. **Top bar** — keep. Brand + mode badge + "N photos · N events" (n visible = trust).
2. **Hero** — PROBLEM: full hero (36px h1 + lede + demo note, ~150px) renders on
   EVERY screen, including mid-search. PM: after the first search the hero is dead
   weight. FIX: compact one-line hero when a search session is active.
3. **Mode radio (Jog/Classic)** — keep; it is the study design (counterbalanced modes).
4. **Memory box + 3 chips + Find it** — core. Chips showed 20-char truncations that
   cut mid-word ("a café somewhere in G…"). FIX: word-boundary cut ≤28 chars.
   "Find it" primary button — keep, it is the only required step.
5. **Left panel: "What I understood" cue chips** — keep (transparency + correction is
   the product's core value and the study's data). 3 buttons per cue (not this /
   sure–unsure / ✕) are optional corrections, not required steps — main path stays
   type → Find it → moments. ADD: show the user's own submitted memory text above the
   cues (currently gone after submit — user cannot re-read what they said).
6. **Moments (right panel)** — keep top-3 thumbs + "This is it ✔" / "Use as anchor".
   Each button earns its place. PROBLEM: no honest signal when the match is weak —
   gibberish input gets the same confident presentation as a strong memory
   (measured: strong memory top-score 0.71, weak 0.60, cue-less 0.50).
   FIX: when top-moment score < 0.55 show one line: "These are your closest matches —
   the question below usually helps."
7. **Question card** — keep. Single question per round, always "I don't remember".
   Minimal and correct.
8. **This-or-that** — keep; best information-per-click interaction in the app.
9. **Anchor card** — keep; 4 options, no explanation needed (labels self-evident).
10. **Fallback** — keep; no dead ends ("I'd narrow it to …" + day grids + Start over).
11. **Confirm card** — PROBLEM: "Your pick: img_0234 · 2023-01-14" leaks a raw file id
    to a human. FIX: show caption + date, drop the id (photo already shown).
12. **"No" on confirm** — PROBLEM: card just disappears; user stares at moments with
    no next step. FIX: toast nudge "Not this one — keep browsing, or use another photo
    as an anchor."
13. **Jog success screen** — PROBLEM: "Found it." celebration with NO photo. The best
    moment in the product hides the artifact. FIX: show the found photo + caption +
    date on the success card.
14. **Classic mode** — keep flat 30-grid (it IS today's baseline; fairness is the
    point). PROBLEM: success card says "Noted — you picked img_0234" (raw id). FIX:
    show the photo + "Noted — thanks for trying…".
15. **Test mode** — task card, timer, give-up, post-task confidence/ease: all keep.
    "no feedback until the end" honored (correctness never revealed mid-task;
    outcome tag appears only in the post-task debrief, which is standard).
16. **Reset** — footer, keep. Test mode needs no reset (reload = fresh session).
17. **Loading copy** — "on-device vision model" is wrong for hosted deploys.
    FIX: "Loading the demo library and vision model (first load only)…"

### What I deliberately did NOT change
- Cue-chip buttons (3 per cue): study-critical (certainty/negation data), optional in the flow.
- MAX_ROUNDS, question cadence, pair cadence: engine behavior, validated by tests.
- Any button label / session key / log event name (test contract + analysis pipeline).

## DISCOVERY ENGINE (space_discovery_static — LIVE; + streamlit twin)

### Verdict per tab
1. **Lede + pipeline strip** — keep. Honest n's, no marketing. (Lede must keep the
   32,412 total — test asserts it.)
2. **Ask — presets** — keep: instant, method + n visible, tables behind the answer,
   evidence cards with source links. This is the strongest tab.
3. **Ask — free text** — PROBLEM: returns nearest-8 + votes but no direct sentence
   first. FIX: add a computed lead line, e.g. "The 8 closest episodes most often
   point to **interpretation** failures in **trip_event** photos." (pure vote
   computation, no AI, no new claims).
4. **Explore** — keep: gate bars with Wilson CIs + era stacks, cue matrix,
   query-style/workaround bars, 6 figures, full episode table with filters +
   pagination. Every chart shows n. No change.
5. **Try it** — keep: n=8 neighbours, majority votes, scorecard cell, 3 cards.
6. **Scorecard** — keep: live weights, p_top3 sensitivity, lev toggle, limits box.
   Only 3 cells (honest — n_cell ≥ 8 constraint on 182 episodes).
7. **Footer** — keep: validation numbers, pass-2 agreement, quote-verified %, sources.

### What I deliberately did NOT change
- Any chart structure/ids (test asserts exact counts: 5 gate bars, 3 era bars,
  25 episode rows, 3 score cells, 6 figures).
- Gate colors (Okabe-Ito standard), "n on every chart" rule.

## Implementation (this pass)
Jog: compact hero, chip word-cut, submitted-memory echo, low-match note,
confirm caption (no raw id), "No" toast, success photo (Jog + Classic), loading copy.
Discovery static: free-question lead line.
Then: re-run all 4 Jog suites + 25-check static test; redeploy static space (live).
