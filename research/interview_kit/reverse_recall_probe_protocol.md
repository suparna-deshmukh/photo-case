# R1 Item 5 — Reverse-recall probe (exact protocol)

Purpose: measure how much of a photo's "identity" survives in memory, and what happens when the
person tries to retrieve it. This is the core 10-minute block.

## Step 1 — select (no phone)
READ: "Choose a photo or video from at least two years ago that you remember reasonably well but not
perfectly. Don't open Google Photos yet."
*(They may keep it private and describe it without showing it. Wait ~10 s.)*

## Step 2 — describe
READ: "Describe it to me as if you were explaining it to a friend. Say everything you remember, and
tell me for each thing whether you are sure or just think so."
Interviewer writes every cue as one row:
| cue type (see codebook) | value (their words) | sure / think so | time spoken |

## Step 3 — search (screen shared)
READ: "Now please share your screen and find it in Google Photos. Think aloud."
- Start the stopwatch at the **first tap**. **Hard stop at 5 minutes** ("Okay, let's stop here.").
- Log in order: every typed query (exact text), every filter/tab used, scrolling vs typing,
  number of reformulations, whether they opened the Ask tab, and the moment of success or giving up.
- **Do NOT help.** No suggestions, no "have you tried…", no hints. Silence + "Take your time."

## Step 4 — reveal check
READ (after success or stop): "Looking at it now, what did you forget or remember wrongly?"
Log each cue from Step 2 as: correct / wrong / forgotten / unverifiable.

## Step 5 — scores
READ: "How confident were you at the start that you would find it (1–5)? And now, how easy was it (1–7)?"
Log: expectation_confidence_1to5, ease_1to7. Stop stopwatch; record probe_time_to_find_s
(only if success; else blank + probe_success = N or partial).
