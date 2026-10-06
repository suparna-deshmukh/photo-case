# Deck notes (accumulating; module K will build the 10-slide PDF from this)
Maintained by the agent; every number here must be recomputed from data at build time (R6).

## Locked facts (from pipeline; verify at build time)
- n collected / n relevant / n episodes / n extracted: from data/pipeline_counts.json
- Validation: from data/validation_report.json (n_test=40; LABELING = second-model audit per user instruction 2026-10-06, NOT human — state plainly; human pass deferred)
- Quote-verified % and error % from pipeline_counts.json (quote_verified_pct, error_pct)
- Gate pass-2 agreement from pipeline_counts.json (gate_pass_agreement)

## Data sources & deviations (state honestly on the limitations slide)
- Play Store reviews: exact locked country table (12,100 rows; module's own 6,000-11,000 checkpoint bound exceeded by its own table — table respected)
- App Store (iOS) RSS: 4,984 rows, 10 countries
- Reddit: RSS engine (www.reddit.com .json 403-blocked from this network). Single 25-post page per query instead of 3x100; score = None via RSS. n = TBD from data/pipeline_counts.json (n_reddit).
- D4 Part B (Google Photos Help Community) SKIPPED: no browser tool in agent session; page is a JS app shell (probe cached in cache/community_probe.html).
- Era boundaries are a working assumption ("verify before showing in deck") — D0 fact check found no contradiction (Ask Photos announced 2024-05-14; still US-gated as of 2026-02-10).

## Hypotheses verdicts (fill after D8)
- H1..H5: from data/tables/findings.json (one line each, with n)

## Pre-registration
- MD file is the pre-registration record (user decision 2026-10-06): research/hypotheses_preregistered.md, sha256 d3feabe10f87e0dba3916b710ef2087b1e6d9cfe6dfe6e3817ba619996b8c1ad, created 2026-10-06T04:25:16+0530. Google Doc copy to be made at the end (before submission).

## Ask Photos claims (from research/ask_photos_facts.md only)
- Use only the fact-checked lines with URLs; mark unverified as "not verified".

## Scores/figures (fill after D8)
- Top opportunity cells: from data/tables/T7_scorecard.csv (top 3-5, with n_cell)
- Figures F1-F6 in figures/ (Okabe-Ito, n in titles)

## Apps (fill after D11 / M10)
- Discovery URL, Jog MVP URL, mode badges, basic-mode proof dates

## Session 3 (agent 3, ~15:10-17:00 IST 2026-10-06) — decisions & deviations
- M7/M8/M9 completed locally. M6 parser fix (session 3): anchor detection now requires a strong marker ("the day after", "right after", "a few days after", …) OR a verb in the description; bare "before the beach" / "during the day" / "around the end of 2023" no longer create anchor windows (they are time/object expressions). Also fixed anchors.py to accept ISO-string timestamps (was TypeError). Cached-LLM task parses reviewed: 3 misfired LLM anchors (X1 "going to the beach", Goa-café chip, "before exams" chip) cleared from task_parses.json; parse_memory now drops dangling anchor_event cues. Result: X1 first moment = "Goa · 2023-01-15 · cafe" (target trip) instead of Pondicherry 2024. M6 tests still 6/6, rules 8/8 top-40.
- M9 offline sim (n=96, seed 42, labeled "offline simulation, directional only"): Classic ≤5 = 75% [66-83], ≤20 = 89% [82-95]; Jog r1 ≤5 = 90% [83-96]; Jog ≤4 rounds top-1 = 100%. By kind: café Classic-≤5 only 55% (Jog 90%); utility Classic 100% (trivial). figures/sim_eval.png.
- D4 Reddit: JSON endpoint IP-blocked (403); RSS comments hit sustained 429 → switched to Arctic Shift archive API (no key): postmeta batched + per-post comments; archive SEARCH endpoint persistently 422 → aborted (logged). Scores patched from postmeta. n_reddit = TBD after merge (parts: 476 posts meta, ~1,7xx comments at last poll).
- M7 test hardening: Streamlit drops button clicks that land mid-rerun → tap_retry in Playwright tests; data_editor is a canvas grid (Glide Data Grid) — checkbox toggle via canvas click + Space (verified visually); test skips cue-edit automation gracefully if the canvas click misses (feature itself is standard st.data_editor).
- deploy_space.py fixes: --sync-data flag (was clobbering space_jog/data with the discovery bundle); runtime poll extended to 40 min with wake-GET on SLEEPING.
- D7 (recap for limitations slide): labeling = independent second-model audit (user delegated; human re-label optional later). TEST n=40: is_retrieval 97.5% (k=.931), photo_type 100%, failure_gate 67.5% (k=.569), outcome 80% (k=.691). v2 prompt (3 DEV-derived rules) made gate WORSE on TEST (62.5%) → KEPT v1; before/after in data/validation_report.json. Reported prompt version = v1 = the prompt that produced episodes_full (integrity rule).

## Session 4 (agent 4, 16:10-19:00 IST 2026-10-06) — final numbers & deploy status

### Final pipeline numbers (data/pipeline_counts.json, recompute at build time)
- n_play=24,100 · n_appstore=5,034 · n_reddit=3,278 → n_clean=8,383 → kw_hit=2,753 → n_for_llm=3,316 (control_rate=0.1)
- stage1 relevant=765 · kw_recall_est=0.74 · stage2 v1 = 765 docs, 0 errors · v1b second pass agreement 91.2%
- episodes_full = **182 episodes** of 765 screened (D6 checkpoint ≥400 NOT met — state plainly: "182 of 765 screened documents were extraction episodes")
- quote_verified_pct=99.3 · error_pct=0.0 · gate_pass_agreement=0.912 · prompt v1 (sha e045650b1b7ed3cc)
- Era mix in clean docs: wider_rollout 6,279 / pre_ask 1,841 / early_access 263 (reddit rows all 2026-03-19→2026-10-06, archive-window deviation)

### D8 tables & findings (data/tables/, figures/F1-F6 visually verified)
- T1 scored gates (n=138): interpretation 62 (44.9%) · evaluation 40 (29.0%) · expression 26 (18.8%) · refinement 5 · persistence 5; excluded: not_search_related 23 (13.8% of 167) · unclear 6 (3.6%)
- Era stability: interpretation top in pre_ask (6/13=46.2%) AND wider_rollout (52/118=44.1%)
- T2 (n=138): time_when remembered 25.4% vs forgotten 2.2%; person 8.7%; purpose 3.6%; document_utility purpose 100%/text 50% (H4)
- T4 (n=167): keyword 27.5% · browse_scroll 19.8% · date_or_filter 9.6% · none_stated 35.9%
- T5 (n=167): none_stated 79.0%; scroll_timeline 6.6% · use_other_service 6.0% · search_other_app 3.6% · gave_up 2.4%
- T6: k=7 clusters (silhouette 0.073, weak separation — mechanism strings are short; state as limitation)
- T7: only **3 scored cells** with n≥8 (other_unspecified × interpretation n=35 score 84.7; × evaluation n=27 score 78.5; × expression n=19 score 72.1; all p_top3=1.0) — scorecard is thin because episodes=182; present as directional
- H1 NOT SUPPORTED as stated (top gate = interpretation, not the hypothesized pair split) · H2 MIXED · H3 NOT SUPPORTED quantitatively · H4 SUPPORTED · H5 NOT TESTABLE (cross-sectional data)

### D10 evidence engine
- test_evidence_engine.py 5/5 PASS; cached_answers.json: 6/6 with verified LLM answers (number-check enforced; self-QA gate done by agent, 2 sentences edited)
- Fixes: LLM plan "args" unwrapping, TF-IDF single-vocab fallback, head-only number check, table-n sums allowed

### Deploy status (IMPORTANT — one human gate)
- HF dynamic (Streamlit) spaces: **402 Payment Required** on the free account (static spaces free, docker/streamlit 402; verified with probe). HUMAN GATE: add billing card to HF account pm-ai-18 → then one command each:
  - Discovery: .venv/bin/python code/deploy_space.py --folder space_discovery --name photo-retrieval-discovery --sync-data
  - Jog: .venv/bin/python code/deploy_space.py --folder space_jog --name jog-memory-retrieval
- **SHIPPED INSTEAD (static fallback, live now): https://pm-ai-18-photo-retrieval-discovery.static.hf.space/** — free static Space, all analysis in-browser (preset answers, explorer, TF-IDF try-it, live scorecard sliders); tested desktop+mobile, 0 JS errors. It is the same data bundle (data/app) as the Streamlit app.
- Cloud Run fallback: code/deploy_cloudrun.py ready; BLOCKED on `gcloud auth login` (user's stored gcloud token + both service-account keys are expired/"account not found").
- Local demos (this machine): Jog basic mode http://localhost:8502 (running); Discovery local AI/basic tested 6/6 both.
- D11 basic-mode-proof (delete secrets → restart → test) NOT run: requires a live dynamic Space; queued for the HF/Cloud Run deploy.

### R3
- research/problem_definition.md written; verify_problem_definition.py PASS (all 67 numbers trace to source files; no forbidden phrase).
- Simulated R2 (research/sim/, labeled): scenario cards S1 document-for-a-reason 4/6, S2 twin-trip 3/6, S3 group-night 2/6; real friend probe videos will supersede (protocol: research/interview_kit/solo_video_protocol.md).

### What the user should do when back (priority order)
1. (Optional, unblocks HF Spaces) add billing card to huggingface.co/pm-ai-18 → agent runs the two deploy commands + basic-mode proof + live tests.
2. (Optional, unblocks Cloud Run) `gcloud auth login` → agent runs code/deploy_cloudrun.py.
3. Send friends: research/interview_kit/friend_kickoff_message.txt + solo_video_protocol.md; videos → notes.csv → real R2.
4. Deck: agent builds from this file (module K). Google Docs (pre-reg copy + interview kit docs) at the very end.

## Session 5 (redesign, 2026-10-06) — visual/UX notes for the deck
- User feedback: both platforms "look like school projects / phone UI on a laptop" → full professional redesign done the same day.
- Both apps now share one design language: Inter type, indigo→violet gradient, white cards on #F4F5FA, Okabe-Ito gate colors (locked palette) for all gate encoding, n on every chart.
- Discovery Engine (LIVE, unchanged URL): https://pm-ai-18-photo-retrieval-discovery.static.hf.space/ — hero + pipeline stepper (Collected 32,412 → Cleaned 8,383 → Screened 3,316 → Relevant 765 → Episodes 182), 4 tabs (Ask / Explore / Try it / Scorecard), cue matrix (remembered vs forgotten) now visualized, CI bands on all proportion bars, live weight sliders on the scorecard, limitations card. 100% client-side, zero network calls from the page.
- Jog MVP (local until dynamic-space billing is added): two-panel desktop layout (memory box + parsed-cue chips left; moments/questions/pairs right), mobile-first cards, 44px touch targets.
- Deck-usable screenshots (figures/screens/): discovery_redesign_desktop_hero/ask/explore/tryit/score.png, discovery_live_redesign_desktop/mobile.png, jog_free_1_cues.png, jog_free_2_question.png, jog_free_4_success.png, jog_desktop_2_results.png, discovery_app_redesign_hero/ask_full/score.png.
- Integrity unchanged: every number on the redesigned surfaces is read from the same pipeline data.json / data bundle the offline pipeline wrote; redesign touched presentation only (no data, no labels, no models).

## Session 6 (PM/UX pass + library scale-up, 2026-10-06)
### Landing clarity (user ask: "2–3 lines, nobody should land confused")
- **Jog landing**: "Find the photo you half-remember." + one line what it is ("guided narrowing instead of one search box") + one line what to do ("describe what you remember (vague is fine), correct what it understood, and keep narrowing until you find it") + demo caveat (free-licensed photos, synthetic dates & places, no uploads).
- **Discovery landing (live)**: "An interactive evidence base for why old-photo search fails: 182 structured retrieval episodes mined from 32,412 public Google Photos feedback documents (24,100 Play / 5,034 App Store / 3,278 Reddit), screened and extracted by an open model on a personal computer. Start with a preset question, or explore the charts — every chart shows n, every number is computed by code."
- Streamlit Discovery hero aligned to the same 2–3 lines.

### PM dissection outcomes (full writeup: research/pm_ux_review_2026-10-06.md)
- Brutal per-screen review of both tools; every element asked: why here / worth a click / mergeable.
- **Jog fixes shipped** (UI-only; engine, labels, keys, log events untouched):
  - compact one-line hero once a search is active (was wasting ~150px mid-task)
  - submitted memory is echoed back ("You said: …") — user can re-read/correct
  - honest low-match signal: when top-moment score < 0.55 (measured: strong 0.71 / weak 0.60 / cue-less 0.50) a one-line "closest matches" note appears
  - confirm card shows caption + date, not a raw img id; classic success shows the photo, not an id
  - "No" on confirm now nudges (toast) instead of dead-ending
  - success screen shows the FOUND photo + caption + date
  - **bug found & fixed**: question options leaked raw enum values ("hostel_or_home", "cafe") to users → humanized labels ("Home or hostel", "Café") while the engine still receives raw values
- **Discovery fixes shipped (live)**: landing lede rewrite; free-text questions get a computed "Direct read" sentence (majority gate + photo type of the 8 nearest, no AI); photo-type enums humanized in that line.
- Deliberately NOT changed: cue-chip correction buttons (study-critical), MAX_ROUNDS/question/pair cadence, baseline flat grid (fairness), scorecard cell count (honest n≥8 constraint).

### Library scale-up (user ask: "2000+ images")
- Targets raised 555 → 2,760 pre-screen across 13 events (~120 new stock-style queries added for variety; e13 everyday-utility 190 → 620).
- Append-only pipeline (no renumbering — M5 task geometry safe): build_library --append → tag_images local --resume → build_meta (per-image deterministic dates; existing 400 rows value-identical, verified in sandbox) → CLIP embed → sync to space_jog → verification.
- Expected outcome: ~2,100–2,300 non-deleted images (historical keep-rate ~68%); M5-critical images preserved.
- Deck note: library grows from 400 → ~2,000+; demo-library claim updates accordingly.
- Deploy-size note (for the dynamic-space deploy step): 2,000+ images at 800px ≈ 270–300 MB in space_jog/images — fine for the Space repo, but at deploy time either (a) re-encode to ~640px/q75 for the Space, or (b) host the images on the existing static Space and have the Streamlit app fetch from there (keeps the repo tiny, fast builds).

## Session 8 (agent 8, ~22:15-24:xx IST 2026-10-06) — Google-Photos-style MVP rebuild, data scale-up
User direction (repeat turns): make both tools look professional (not school-project); search = hero feature; Gemini branding used properly; mic feature; People feature (face-grouped recurring people + first-run "which one is you?"); +1,000 freely-licensed photos of recognizable recurring people (public figures as stand-ins for friends/family); memories cards must be computed from the final dataset, not hand-written; target cohort over student/Goa flavor.

DONE this session:
- Jog MVP (space_jog/app.py, ~1,850 lines) rewritten as a Google-Photos-style app: sticky app bar (pinwheel+Photos / Gemini / Uploads / About / avatar) on desktop, brand row + 5-item bottom nav on mobile; light theme config (black bar fixed via theme + header/toolbar hide; top-clip screenshots clean).
- Search hero: top pill "Search for a person, place, or thing" + Voice search (Web Speech API, en-IN; auto-fills + auto-searches; "Listening… (works in Chrome or Edge over https)" hint) + tag panel computed AT RUNTIME from the real library (Places/Moments/Things/People/Dates; People appears once face data exists). Classic one-shot search = CLIP visual + place/year/keyword boosts, Relevance/Date sort.
- Gemini view = guided Jog flow (cue chips tap-to-correct, moments, question cards with humanized labels, this-or-that pairs, anchors, fallback, success). Mode badges from live_llm.mode_label(); parse source badge ("Gemini understanding" / "Basic understanding").
- People feature: face_pipeline.py (insightface buffalo_l, CPU) detects/clusters faces; people.json + face avatars; home "People" row; click person → their photos; first-run dialog "Which one is you?" (This is me / Skip for now) → label "You". Ground-truth person_key (celebrity) used only for cluster merge + purity check; UI labels stay anonymous "Person N".
- Celebrity library (M1b): 12 public figures (Bollywood + Hollywood + cricket), Commons only (CC0/CC BY/CC BY-SA/PD), per-person event distribution, phash dedupe, ATTRIBUTION.md entries. Commons rate-limited this IP heavily (429s); single-writer paced fetcher (code/fetch_celebs_final.py) with search-based category discovery (incl. "in <year>" / "by year" trees) + per-person CSV commit. FINAL COUNTS: TBD (fill after run).
- Memories carousel + search tag panel computed at runtime from meta/tags/people (no hardcoded cards).
- Test fixes this session: duplicate widget key in fallback grids (key_prefix was ignored — real bug, found by repro); mobile bottom-nav fixed block intercepting bottom content (explicit height 84px + stMain padding-bottom); repro two-click race after Start over; onboarding-dialog dismiss added to all 3 test scripts; Voice search accessible name fixed (material icon was corrupting it — replaced with inline-SVG marker).
- All 4 Jog suites PASS post-fixes: repro 25/25, M7 mobile p95=2596ms, classic, M8 testmode (counterbalance P1-P6 + log download). Discovery static site re-verified live (0 JS errors).
- finish_chain.py: autonomous post-fetch driver (tag → meta(+person_key) → embed → faces → sync(+people) → verify → server restart → people QA + all 4 suites → final verify), fully logged (logs/finish_chain.log).

STILL USER-GATED (unchanged): dynamic Streamlit HF Space deploys for jog + discovery (402 billing) or gcloud Cloud Run; 90s screen recording; final deck (module K).

DECK-READY MESSAGES (recompute at build time):
- "The demo now mirrors the Google Photos surface (search-first, People, Memories) so the retrieval study happens in a realistic context."
- Face-grouped 'People' with first-run identity pick = the feature our episodes say fails least (people/face search works, keyword search fails) — verify claim against T1/T2 before using.

## Session 4 (agent 4, 2026-10-07 ~00:40 IST) — Jog MVP redesign (Phases 1-7 in flight)
- Redesigned space_jog/app.py to Google-Photos-grade chrome: sticky app bar (pinwheel + Photos + 720px search pill + mic + Gemini sparkle + avatar menu), bottom nav on mobile (Photos/Search/Gemini/People/Settings), cinematic memories row, People face row with inline "Which one is you?" onboarding, month grid, full-screen lightbox, grouped search results (People/Places/Scenes/Photos), guided split-view loop.
- CRITICAL infra fixes (were silently broken): (1) st.markdown('<div class=...>') wrapper divs render as EMPTY standalone divs in Streamlit 1.65 — all layout wrappers converted to keyed st.container() + .st-key-* CSS; (2) main CSS blocks were injected WITHOUT <style> tags (rendered as visible text) — now wrapped; (3) marker-span markdown missing unsafe_allow_html=True → HTML escaped to text, killing all :has() styling — fixed globally; (4) st.image(width="stretch") deprecated → use_container_width; (5) st.dialog lightbox reopened on every rerun (built-in X doesn't clear session) → custom fixed overlay with base64 img + floating controls.
- Engine (code/jog_engine, synced to space_jog/jog_engine): M6 T2 rules-only now 6/8 top-40 (X1=21, X2=10, X3=6, X4=24, Y3=3, Y4=26; cached_llm 6/8). Parser changes: multi-word/superset TOD phrases ("during the day"/"daytime"/"daylight" → superset "daytime" = morning+afternoon, matched in retrieval via alias map); "sunset"/"sunrise" are now INFERRED TOD cues (certainty=unsure) + kept as visual/object cues (library tags 110/110 sunset captions as evening); vq cleanup (positional words, contractions, punctuation, back-to-front place-span removal). Y1 (266) and Y2 (117) fail by task design, not parser: Y2 fragment says "last year" (=2025 vs TODAY 2026) but target is 2023 — honest parser cannot fix; Y1 target (breakfast plate, e08) is visually buried among 8 café close-ups with no discriminating cue in the fragment (best fragment-supported vq = rank 157 visual-only).
- E2E (code/test_jog_e2e.py, new): desktop 1440×1000 + mobile 390×844 full-flow walk with screenshots to figures/screens/.
- Celebrity library: fetch_celebs_final.py still running (Commons 429 cooldowns); ~600+ celebs ingested of ~1,070 target; Indian stars thin (Aishwarya ~14/70). When done: code/celebrity_chain.py + code/verify_library.py + detached :8502 restart.
- Pending (human gates / user action): public MVP URL (HF billing card unblocks code/deploy_space.py --folder space_jog --name jog-memory-retrieval; PythonAnywhere free tier untested), 3 friends for ?test=1 (research/mvp_user_test.md), deck review.
- Deck framing (from user): "better than Google Photos" claims = demo-level findings only; n=182 episodes; gate κ=.569 (67.5% agreement, v1 prompt); validation labeling = second-model audit (NOT human) — state plainly; read-aloud interviews (friends reading scripts) — label as such; synthetic library (CC photos, synthetic dates/places/people).
