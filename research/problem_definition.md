# Problem Definition (R3)

Inputs used (no other numbers): data/tables/T1–T7 + findings.json, data/validation_report.json,
data/pipeline_counts.json, research/sim/ (SIMULATED participant study, clearly labeled — protocol
validation only, not real user evidence), research/ask_photos_facts.md.

## Target segment
Android-first Google Photos users who have backed up for 3+ years and hold libraries from a few
thousand to tens of thousands of photos. They have the deep libraries where a missed photo is
costly. Interview segment (simulated): 5 of 6 target users with 2–4 years of use and ~2,500–32,000
photos. Discovery data: 3,278 Reddit rows skew to Android subreddits; app-store/play reviews add
cross-platform breadth (n=8,383 clean docs total).

## Retrieval scenario
Two or more years ago the user photographed something for a reason: a medicine strip to remember a
dosage, a ticket, a trip day, a group night. They remember the context, the feeling, the rough
time — but the one cue that discriminates the photo (exact date, exact text in it, which of two
similar trips) is missing or wrong. Now they need that one photo, and the library is big enough
that scrolling is not an option.

## Product outcome to influence
Recovery after a failed first query. The gates that decide it: interpretation (62 of 138 scored
episodes, 44.9%) and evaluation (40 of 138, 29.0%). Measurable behavior: share of failed searches
recovered on the next interaction; time-to-find; reformulations that ADD a cue vs swap keywords.

## Root cause
Because search expects exact keywords, dates, or faces while people hold partial memory — a time,
a context, a feeling — with the discriminating cue missing or wrong, the system cannot map a
half-memory to a small candidate set, so users scroll, try other apps, or stop searching.

Supporting evidence (exact numbers):
- interpretation is the top scored gate: 62/138 = 44.9%; evaluation 40/138 = 29.0%; expression 26/138 = 18.8% (T1).
- time_when is remembered in 25.4% of scored episodes but explicitly forgotten in only 2.2% (T2): memory holds time; search treats it as weak.
- keyword is the most common stated query style at 27.5%; browse_scroll 19.8%; none stated 35.9% (T4, n=167).
- 132/167 = 79.0% state no workaround at all (T5): there is no recovery path in today's flow.
- H4 (supported): document_utility episodes remember purpose_or_reason in 100.0% and text_in_image in 50.0%, while trip_event episodes remember event_context in 0.0% and anchor_relation in 0.0% (findings.json). The cues people hold do not match the signals search ranks.
- Era stability: interpretation is top in pre_ask (6/13 = 46.2%) and still top in wider_rollout (52/118 = 44.1%) (T1).

## Existing workarounds (ranked, T5, n=167)
1. scroll_timeline — 11 (6.6%)
2. use_other_service — 10 (6.0%)
3. search_other_app — 6 (3.6%)
4. gave_up — 4 (2.4%)
5. manual_albums_or_favorites — 3 (1.8%)
6. switch_to_classic_search — 1 (0.6%)
(no workaround stated: 132, 79.0%)

## User value
Get the half-remembered photo found without re-telling the story as keywords; stop asking friends
to resend it; keep trusting that the library holds what happened.

## Business value for Google Photos (mechanisms; hypotheses unless supported)
- Library stays the memory store: persistence gate = 5/138 = 3.6% (T1) is the disengagement signal after failed retrieval (supported as a signal; mechanism is a hypothesis).
- Confidence to keep backing up → storage-plan retention (hypothesis; no direct measure in this data).
- Engagement with AI features: ask_photos_chat appears in 1/167 stated query styles (T4) — headroom exists (hypothesis).
- Sharing: people re-request photos from friends after search fails (simulated R2, S3) (hypothesis).

## Evolution chain
Storage-plan retention (business metric) → recover after a failed first query (product outcome) →
interpretation gate = 44.9% of 138 scored episodes (discovery signal) → keyword-first query, then
scrolling or stopping (observed behavior) → search expects exact cues while memory is partial
(problem).

## What we chose NOT to solve (and why)
1. Storage pricing and plan complaints — screened out in D6 as not retrieval.
2. Deletion, sync and "library missing" reports — not_search_related = 23/167 = 13.8% (T1); different product surface.
3. Memories/highlights quality — out of scope per the D6 relevance rule.

## How Jog differs from Ask Photos
Verified from research/ask_photos_facts.md (support page, accessed 2026-10-06): "You can switch
between the classic search and Ask Photos results at any time" — Ask Photos is a parallel
natural-language results mode on top of classic search. Everything else about Ask Photos' internal
behavior (including why it still fails interpretation) is not verified. Jog is not a second results
mode; it is an interactive narrowing loop (moments → one question → this-or-that) that converts
partial memory into a convergent search.

## Slide-ready text

### Slide 5
Title: "Interpretation is where retrieval breaks: search hears keywords, people hold memory."
Body:
- 62 of 138 scored episodes (44.9%) fail at interpretation; evaluation adds another 29.0% (T1, n=138).
- People do hold cues: time_when in 25.4% of episodes, person in 8.7%, purpose in 3.6% (T2) — but the one discriminating cue is often missing or wrong.
- They respond with keywords (27.5%) and scrolling (19.8%) — the two least discriminating signals (T4, n=167).
- Interpretation stayed the #1 gate across eras: pre_ask 46.2% (6/13) → wider_rollout 44.1% (52/118) (T1).

### Slide 6
Title: "After the first miss there is no recovery path — 79% state no workaround at all."
Body:
- Workarounds that exist are few: scroll 6.6%, other service 6.0%, other app 3.6%, give up 2.4% (T5, n=167).
- Top scorecard cells (n_cell >= 8): other_unspecified x interpretation (n=35, score 84.7), x evaluation (n=27, 78.5), x expression (n=19, 72.1); all p_top3 = 1.0 (T7).
- Document/utility photos remember purpose in 100.0% of episodes — the cue search ignores (findings.json, H4 supported).
- Engine accuracy on the held-out test set: is_retrieval 97.5%, photo_type 100%, failure_gate 67.5%, outcome 80.0% (validation_report.json, n_test=40, prompt v1).
