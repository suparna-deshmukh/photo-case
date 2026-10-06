# MVP user test — protocol (Part 6 / M8 evidence)

Three real users (friends; college students) run the Jog MVP in **Test mode** (`?test=1`).
15 minutes each. No coaching, no second chances beyond the app's own 2-wrong-confirm rule.

## Prerequisites
- App reachable at a public or LAN URL (record the final URL in research/links.md as LINK_mvp).
- Phone or laptop, Chrome/Edge, default zoom.
- Recorder: you (schedule via WhatsApp; 15-min slot).

## What each participant does (read this to them, 30 seconds)
1. Open `<URL>/?test=1`.
2. Type your code (P1 / P2 / P3) and press **Start session**.
3. Two **practice** tasks first (1 minute each, not counted) — one per mode.
4. Eight real tasks. Each task shows a short memory ("I'm trying to find…").
   - **Classic mode**: type a search, look through the grid, tap "This is it ✔" when you're sure.
   - **Jog mode**: read the questions, answer with buttons (or "I don't remember"),
     use "This is it ✔" / "Use as anchor" / "I'm stuck" as needed.
   - 3-minute limit per task. Up to 2 wrong "This is it" tries; 3rd wrong or timeout ends the task.
5. After each task: rate confidence (1–5) and ease (1–7).
6. At the end: answer the three free-text boxes (what was confusing / what helped / what you'd change).
7. Press **Download my session log** and send you the file (WhatsApp is fine).

## Rules for you (the researcher)
- Do not explain features, do not suggest queries. Silence is fine.
- If the app errors: screenshot, note the exact step, let them continue; log it below.
- After each session, click **Download all events** at `<URL>/?admin=1` and save to
  `research/test_logs/session_<P#>.jsonl` (the app also hands each participant their own file).

## Synthesis (fill in after all three)
| task | P1 mode/outcome (s) | P2 mode/outcome (s) | P3 mode/outcome (s) | notes |
|------|--------------------|--------------------|--------------------|-------|
| P1 practice | | | | |
| P2 practice | | | | |
| X1 | | | | |
| X2 | | | | |
| X3 | | | | |
| X4 | | | | |
| Y1 | | | | |
| Y2 | | | | |
| Y3 | | | | |
| Y4 | | | | |

Outcome = success / fail / give_up / timeout. (s) = seconds from task_start to task_end.

Compute from the JSONL (code, not by eye):
- success rate by mode (Classic vs Jog), overall and per task type
- median time-to-find by mode; median rounds (Jog) / queries (Classic)
- recovery-after-fail: tasks where the first "This is it ✔" was wrong but the task still succeeded
- question value: did answering "I don't remember" vs a real option change success?
- parse_source mix (cache/llm/rules) per session (from cues_parsed events)
- confidence/ease medians by mode; free-text themes (3 max, verbatim quotes)

Honesty rules: report Classic wins where they happen; label n=3 explicitly;
friends are not a random sample (selection bias → direction, not prevalence).

## Session log
- P1: date ______, errors ______, file research/test_logs/session_P1.jsonl
- P2: date ______, errors ______, file research/test_logs/session_P2.jsonl
- P3: date ______, errors ______, file research/test_logs/session_P3.jsonl

## Status
PENDING — needs a reachable URL + 3 friends (human gate: user schedules).
