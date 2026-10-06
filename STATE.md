# STATE BLOCK (living - overwrite with the latest block from each thread)

Last updated: 2026-10-07 ~01:10 IST (session 4)
BASE: /Users/apple/photo_case (locked default ~/photo_case; moved here from photos-retrieval-fellowship/photo_case)

## Session 4 snapshot (Jog MVP redesign — Phases 1-6 largely done, Phase 7 in flight)
- Engine: code/jog_engine T2 rules-only 6/8 top-40 (X1 21, X2 10, X3 6, X4 24, Y3 3, Y4 26; cached_llm 6/8). Y1/Y2 fail by task design (see deck notes session 4). All 6 engine tests PASS. space_jog/jog_engine synced.
- App: space_jog/app.py rewritten to GP-grade chrome. CRITICAL: Streamlit 1.65 silently breaks (a) wrapper <div> markdown (renders empty) -> keyed st.container + .st-key-* CSS; (b) st.markdown CSS without <style> (renders as text) -> wrapped; (c) marker spans without unsafe_allow_html=True (escaped to text) -> fixed globally; (d) st.image(width="stretch") -> use_container_width; (e) st.dialog lightbox (reopens on rerun) -> custom fixed overlay + base64 img + floating controls. Bottom nav hidden on desktop (.st-key-mnav).
- Tests: code/test_jog_e2e.py (NEW, desktop+mobile full flow + screenshots); repro_jog_widget.py stale (old UI) - superseded by e2e; test_jog_app/testmode/people need re-run after E2E green.
- Docs: research/mvp_user_test.md (3-friend protocol), code/record_demo.py (90s video), deck/notes_for_deck.md session-4 section, links.md LINK_mvp local.
- Running: fetch_celebs_final.py (PID 92570) - Commons 429 cooldowns, ~600/1070 celebs, Indian stars thin (Aishwarya 14/70). On finish: code/celebrity_chain.py + code/verify_library.py + detached :8502 restart.
- BLOCKED (needs user): public MVP URL (HF billing card -> code/deploy_space.py --folder space_jog --name jog-memory-retrieval; or PythonAnywhere), 3 friends for ?test=1, deck review.

## Decisions
- Locked context v3 adopted (supersedes v2): .venv at BASE (Python 3.13.14 via /opt/homebrew/bin/python3.13); scripts in BASE/code; no notebooks unless asked; no Colab.
- Local LLM = Qwen via LiteLLM proxy; LLM_BASE_URL/LLM_API_KEY/LLM_MODEL discovered + filled in D0 (LiteLLM may alias names, drop params; D0 verifies).
- Local LLM usage unlimited; llm_helper.autotune_workers() 1-8 by measured throughput.
- Human gates confirmed: one keys-and-logins session in D0 (Google AI Studio key OPTIONAL, Pexels key, HF WRITE token; 2FA/CAPTCHA/terms by user); approvals "pilot ok" (D6), "tags ok" (M2), "answers approved" (D10), "approve" (M5) + final deck look (K1); human-only: interviews R1/R2, tests T1, hand-label D7, hand-edit M5/D10; user sends messages; user types forbidden.txt; user submits.

## Files and paths
- BASE/{.venv(py3.13.14),cache,code,code/jog_engine,code/prompts,data,data/tables,data/app,figures,figures/screens,research,research/test_logs,library,library/images,library/contact_sheets,space_discovery,space_jog,deck,deck/pages,qa,logs}
- BASE/{.env MISSING - D0 keys session, .gitignore, STATE.md, forbidden.txt EMPTY - user types}
- docs/{role-and-rules.md v3, locked-context.md v3 verbatim}
- Registry v3 incl. research/{tools_inventory.md,llm_probe.json,ask_photos_facts.md,links.md}, qa/QA_REPORT.md

## Schema versions
- v3: enums, gates, palette, figure standard, LLM profiles, live-layer constants, folder layout, file registry

## Constants
- LIVE layer: PER_SESSION_CAP=10, DAILY_CAP=300, TIMEOUT_S=8, PROBE_TIMEOUT_S=3, breaker 2 fails -> 120 s
- .env keys: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL, LIVE_LLM_BASE_URL, LIVE_LLM_API_KEY, LIVE_LLM_MODEL, LIVE_DAILY_CAP, PEXELS_API_KEY, HF_TOKEN
- Spaces: photo-retrieval-discovery, jog-memory-retrieval; deploy via huggingface_hub scripts; HF username neutral
- Deck: python-pptx -> LibreOffice PDF -> automated checks; Slides fallback
- Era dates = working assumption (D0 may refine); flag "verify before showing in deck" until approved

## Done
- BASE layout complete per v3; .venv (3.13.14) created; rules v3 + locked context v3 archived; .gitignore written; stray /Users/apple/.venv (accidental, py3.9) removed

## Not done
- All 4 deliverables; .env; forbidden.txt content; every registry file; module D0 not started

# STATE BLOCK — D0 (appended 2026-10-06 by agent)
BASE: /Users/apple/photo_case
Decisions:
- Local LLM = Qwen via REMOTE LiteLLM proxy (Cloud Run), discovered read-only from ~/.codex/litellm.config.toml + env LITELLM_API_KEY; base https://litellm-cw-tnc7knp4ba-uc.a.run.app/v1; alias qwen38-27b (alt alias gemma-4-26b-a4b-it).
- Alias routing note: x-litellm-model-api-base header shows qwen38-27b routes to a "risa-gemma4" backend - aliasing confirmed, flagged for later modules.
- No browser/Workspace tools in this session: keys gate + pre-reg Google Doc = HUMAN GATE; ai.google.dev pricing is sign-in-walled -> LIVE_LLM_MODEL stays empty until verified in keys gate.
- Ask Photos fact check: era boundaries NOT contradicted (announced 2024-05-14; "rolling out over the coming months"; still US-eligibility-gated 2026-02-10) -> no new boundaries proposed; all era dates stay "verify before showing in deck".
Files: .env (mode 600; LLM_* set, LIVE_LLM_BASE_URL prefilled, LIVE_LLM_API_KEY/LIVE_LLM_MODEL/PEXELS_API_KEY/HF_TOKEN empty), .gitignore, forbidden.txt (empty), code/d0_install.sh, code/d0_probe_llm.py, research/{tools_inventory.md, llm_probe.json, ask_photos_facts.md, links.md, hypotheses_preregistered.md}, logs/{actions.log, install.log, libreoffice.log}, cache/{ap_*.html, ddg2.html, web_*.html}
Probe: JSON mode OK; vision OK (red PNG -> "Red"); no think-block leak; both thinking switches accepted by proxy (effect unverified); context >=6526 tokens (needle returned); latency median 2.36 s (5 calls: 2.36/2.53/1.40/1.49/2.60); 4-parallel burst all 200, no 429, no rate-limit headers.
Installed (venv py3.13.14): pandas 3.0.6, pyarrow 25.0.1, numpy 2.5.3, pydantic 2.13.5, openai 3.24.0, requests 2.34.2, tqdm 4.70.1, scikit-learn 1.9.1, sentence-transformers 6.1.0, transformers 5.18.0, torch 2.14.1, altair 6.3.0, matplotlib 3.11.2, google-play-scraper 1.2.7, rapidfuzz 3.14.6, langdetect 1.0.9, statsmodels 0.15.0, Pillow 12.3.0, imagehash 4.3.2, streamlit 1.65.0, python-pptx 1.0.2, pypdf 6.19.0, pymupdf 1.28.2, python-dotenv 1.2.4, huggingface_hub 1.33.0, playwright 1.63.0 + chromium 153.0.8010.12; LibreOffice 26.8.0.3 (brew cask).
Pre-registration: fallback file only sha256 d3feabe10f87e0dba3916b710ef2087b1e6d9cfe6dfe6e3817ba619996b8c1ad, created 2026-10-06T04:25:16+0530; Google Doc = HUMAN GATE before D6.
Done: D0 steps 1,2,3,4,5,8 PASS; steps 6,7 = HUMAN GATE pending.
Not done: .env hosted/pexels/HF keys; pre-reg Google Doc; forbidden.txt content; every registry file; D1+.

# STATE BLOCK — D0 follow-up: keys (appended 2026-10-06 by agent)
Decisions:
- Keys session done by user: LIVE_LLM_API_KEY set (AI Studio), LIVE_LLM_MODEL=gemini-3.8-flash, HF_TOKEN set (token name nextleap, HF username pm-ai-18 - neutral, no name/ID).
- Pexels SKIPPED per user: key issuance paused; PEXELS_API_KEY stays empty; M1 image source = Openverse + Wikimedia Commons (no key). Locked-context Pexels line superseded for M1 by this explicit instruction.
- Hosted config verified live: /models 200 (models/gemini-3.8-flash present); chat 200 "pong" 5.45 s after 2 transient 503 "high demand" errors (free-tier load; retry works; circuit breaker + retry logic required in live_llm.py).
- Pricing page free-tier marking: verified by user (page sign-in-walled for anonymous fetch); recorded as user-verified in research/links.md.
Done: .env complete except PEXELS_API_KEY (intentionally empty). D0 checkpoint fully PASS.
Open HUMAN GATES: HG2 pre-reg Google Doc (before D6); HG3 forbidden.txt content.
Not done: all registry data/code; D1+.

# STATE BLOCK — D1 + D1B (appended 2026-10-06 by agent)
Done:
- code/pipeline_counts.py: thread-safe merge writer -> data/pipeline_counts.json (now {d0_bootstrap: true, llm_workers: 8}).
- code/llm_helper.py: get_client(local|hosted); llm_json (JSON mode ON + fallback on 400; qwen thinking-off via extra_body enable_thinking=False + "/no_think" + fallback on 400; think/fence strip; first-{..last-} extract; pydantic; invalid-JSON retry x3 with appended instruction; 429/5xx backoff 2/4/8/16; never raises -> {"_error": ...}); llm_json_image (PIL downsize <=640px JPEG); disk cache cache/llm_cache.jsonl (sha256 key, append-only, loaded at import); llm_json_batch (ThreadPoolExecutor + tqdm + optional max_per_minute pacer); autotune_workers(1/2/4/8, 12 calls/tier); check_context(limit 5526 = D0 6526 - 1000); speed_test.
- D1 valid run (logs/d1_run.log run 2): smoke ok=true, second identical call cache hit (0.9 ms); tiers 1/2/4/8 = 15.7/8.3/8.3/3.0 s, 0 errors -> workers=8 saved; speed 1.27 s/call sequential; projections 1000/3000/6000 = 21.2/63.5/126.9 min; secret scan clean.
- Integrity note (R18): run 1's autotune used prompts shared across tiers -> cache collisions invalidated tiers 2-8 and mis-saved workers=4; fixed with per-tier nonces; run 2 is the valid measurement (the collision itself demonstrated the disk cache works).
- code/live_llm.py: requests-only, guarded imports, never raises; 5-min /models probe; PER_SESSION_CAP=10; DAILY_CAP=300 (env LIVE_DAILY_CAP); breaker 2 fails -> 120 s; LRU-500 input cache (hits free); no inputs/outputs to disk or logs; no key/URL printed.
- code/test_live_llm.py: 5/5 PASS (logs/d1b_test.log): (1) not_configured, None in 0.0 ms; (2) dead base -> breaker open after 2 failures in 0.00 s, no exception; (3) real hosted round 1: {'ok': True} + second identical call cache hit; (4) PER_SESSION_CAP=2 -> third distinct call None (session {'live_calls': 2}); (5) LIVE_DAILY_CAP=2 -> third call None + daily_cap_reached.
Constants: CONTEXT_LIMIT_TOKENS=5526; live-layer constants per locked context.
Files: code/{pipeline_counts.py, llm_helper.py, live_llm.py, d1_run_checks.py, test_live_llm.py}; data/pipeline_counts.json; cache/llm_cache.jsonl; logs/{d1_run.log, d1b_test.log}.
Open: HG2 pre-reg Google Doc (before D6); HG3 forbidden.txt. SKIPPED-path of D1B test 3 not exercised (hosted layer present).
Not done: D2+ (data pipeline, apps, library, deck).

# STATE BLOCK — D2 + D3 (appended 2026-10-06 by agent)
Done:
- code/collect_play.py (resume via data/play_parts/, --limit N, 1 s sleep, 5-error stop, userName/userImage dropped immediately) and code/collect_appstore.py (app id 962194608 verified via itunes lookup, UA student-research/0.1, pages 1..10, resume via data/appstore_parts/).
- data/play_raw.parquet: 12,100 rows, per-combo EXACT locked table (in 2500/1500, us 2000/1500, gb 800/500, au 600/300, ca 600/300, sg 300/200, za 300/200, ph 300/200); span 2024-08-19 -> 2026-10-05 (25.5 months); 0 empty dates; no zero-row country; n_play=12100.
- D2 checkpoint note: the module's country table sums to 12,100, above its own 6,000-11,000 range; table respected exactly, nothing trimmed beyond combo targets. Strict <=11,000 would need an approved table change (e.g. in/newest 2500->1400).
- Scraper behavior: google-play-scraper 1.2.7 returns full ~200-row batches (ignores final count); part files may overshoot, merge truncates to table targets (parts keep full raw).
- data/appstore_raw.parquet: 4,984 rows (us 486, in/gb/au/ca/sg/za/ie/ph 500, nz 498); span 2019-06-05 -> 2026-10-04; author names NOT stored; n_appstore=4984; >=800 PASS.
- Part dirs kept for resume; both scripts re-runnable (skip complete combos).
Not done: D4+ (further sources, cleaning, episodes), apps, library, deck.

# STATE BLOCK — D4 resume + delegation decisions (appended 2026-10-06 by agent)
Decisions (user, 2026-10-06, "you decide how / do everything yourself"):
- Pilot gate ("pilot ok"): pre-delegated to agent — proceed with full stage 2 if automatic checks + agent review of 10 sample outputs are good; decision logged at time of run. User may veto on check-in; stage-2 re-run cost ~15-30 min.
- D7 labeling: delegated to agent (second-model audit). NOT human validation. validation_report.json and deck must state: labels written by a second AI model (frontier LLM), independent blind pass, per user instruction 2026-10-06; human validation deferred. Blind CSV kept valid for a later human pass.
- D10 "answers approved": self-QA (agent verifies every number/sentence against tables; edits unsupported sentences); user final review later.
- Pre-registration: per user, the MD file IS the pre-registration record for now: research/hypotheses_preregistered.md (sha256 d3feabe10f87e0dba3916b710ef2087b1e6d9cfe6dfe6e3817ba619996b8c1ad, created 2026-10-06T04:25:16+0530). Google Doc copy will be made at the end (before submission); until then, no public claim of pre-registration.
- Deck (module K) explicitly deferred by user; agent maintains deck/notes_for_deck.md with all findings/decisions/flags as they occur.
D4 status: json engine 403-blocked (IP-level); RSS engine works (25 newest posts per query; per-post comment feeds). Full run launched 05:45 +0530 as session 29572 -> logs/d4_reddit_rss.log; observed sustainable rate ~1 request / 55-60 s; ETA ~2.5-3 h. Deviations (to state on deck): RSS = single 25-post page per query (module: 3x100 JSON pages); score column = None via RSS.
Done: code/clean_merge.py (D5, regex unit-tested), code/schemas.py (D6), code/run_stage1.py (D6, patched), code/d4_checkpoint.py (D4).
Not done: D4 full run, D5 run, run_stage2.py, D7 scripts, D8-D11.

# STATE BLOCK — D4 run + D5-D11 pre-build (appended 2026-10-06 by agent)
D4: full RSS run in progress (session 29572, logs/d4_reddit_rss.log). All 60 (sub,query) search pairs saved to data/reddit_parts/ (25 posts each). Comment phase running: 120 per-post .rss feeds, ~55-60 s each (Reddit rate budget), ETA ~12:00-12:30 +0530. 429s handled by 45 s backoff, 0 pairs skipped so far.
D5: code/clean_merge.py written + unit-verified on play/appstore (play 12,100 -> 6,293 >=8 words, 8,836 exact dups, 2,689 kw_hit; appstore 4,984 -> 3,381, 75 dups, 1,248 kw_hit; all dates parse; era dist sane). Regex unit-tested (14 cases).
D6: code/schemas.py (locked Episode model), code/run_stage1.py (batch 12/450 chars, resume, recall est), code/run_stage2.py (v1+v1b passes, step-0 120-min cap logic, pilot mode, 900-char trunc, partials/25, ETA log), code/finalize_stage2.py (quote verify, pass-2 agreement, episodes_full join). Prompts: code/prompts/stage2_v1.txt (module-verbatim), stage2_v1b.txt (reworded equivalent).
D7: code/prepare_validation.py (55 docs: 15 DEV + 30 TEST-episode + 10 TEST-notrelevant(stage1), seed 42, blind CSV + key parquet), code/validation_report.py (TEST-only accuracy+kappa 4 fields, gate confusion matrix, disagreement rows, before/after hook). Labeling = agent second-model audit per user decision.
D8: code/analyze.py (T1-T7 incl. T6 KMeans 6..14 silhouette + 1 LLM naming call/cluster + T7 scorecard with Dirichlet-1000 sensitivity + no-lev ranking; F1-F6 per locked figure standard; findings + H1-H5 verdicts -> data/tables/findings.json; T6_cluster_map.csv for D9).
D9: code/build_app_data.py (episodes_public w/ snippet 280 char, MiniLM normalized emb, enums.json, copies T/F/validation/counts, <50 MB check).
D10: code/evidence_engine.py (load_data, query_stats w/ cue pseudo-cols, semantic_search minilm/tfidf-fallback w/ emb_ids alignment, route_keywords, plan_with_llm w/ step validation, run_plan, answer_with_llm w/ citation+number checks, templated_summary, nearest_estimate, build_cached_answers 6 presets), code/test_evidence_engine.py (5 tests), code/run_d10.py (local-profile live_call adapter).
D11: space_discovery/ written (README exact YAML, pinned requirements + CPU torch index, live_llm/schemas/evidence_engine/stage2_v1 copies, app.py full 4-tab app). code/deploy_space.py (create/upload/secrets/poll, -lab fallback), code/test_discovery_app.py (Playwright fresh-context harness, 6 checks).
APP SMOKE TEST (synthetic bundle /tmp/disc_smoke, NOT real data): 6/6 PASS basic mode AND AI mode (LIVE_LLM_* set); free-text LLM plan -> query_stats -> answer verified-or-fallback demonstrated; badge "AI mode"/"Basic mode" both render. Bugs found+fixed: st.cache_resource usage, altair-6 (no add_layer, encode kwargs, no Parameter bind), text_area/text_input commit-on-blur -> buttons always-enabled with in-handler guard.
HF: user pm-ai-18; both space names AVAILABLE (404 verified): photo-retrieval-discovery, jog-memory-retrieval.
Done-delegated: D6 pilot pre-approved; D7 self-labeling; D10 self-QA; pre-reg = MD file (Doc at the end).
Not done: D4 completion + checkpoints D5-D11 execution (awaiting reddit job), D7 labels, real-data app test, deploy, basic-mode-proof, deck (deferred).

# RESUME PLAN (agent, 2026-10-06) — execute in this order after reddit job finishes
1. Confirm `DONE collect_reddit` in logs/collect_reddit.log (job session 29572). If it crashed: re-run `.venv/bin/python code/collect_reddit.py --engine rss` (resume-safe; parts + comment resume now in place).
2. If comment coverage low (skips): run `.venv/bin/python code/collect_reddit.py --engine rss --rss-sleep 60` (comment resume skips posts already captured).
3. D4 checkpoint: `.venv/bin/python code/d4_checkpoint.py` (expect >=300 rows; record RSS deviations).
4. D5: `.venv/bin/python code/clean_merge.py` then `code/d5_checkpoint.py`.
5. D6 stage1: `.venv/bin/python code/run_stage1.py` (~10-15 min, 8 workers).
6. D6 pilot: `.venv/bin/python code/run_stage2.py --pass v1 --pilot 30`; run automatic checks (schema validity, quote verify, enums) + print 10 full outputs next to source text; agent reviews; if good, PROCEED (delegated) and log decision.
7. D6 full: `.venv/bin/python code/run_stage2.py --pass v1` (120-min cap auto) then `--pass v1b`, then `code/finalize_stage2.py` (quote verify, agreement, episodes_full.parquet).
8. D7: `code/prepare_validation.py` -> agent labels research/validation_blind.csv BLIND (writes research/validation_filled.csv; criteria documented in the report) -> `code/validation_report.py`. If gate agreement <70%: write stage2_v2 from DEV disagreements only; if <60% add <=6 DEV few-shots; re-run 40 TEST docs with v2; before/after in report; decide full re-run vs keep v1 per module rule (log decision).
9. D8: `code/analyze.py` (dry-run validated on synthetic data 2026-10-06; figures verified visually).
10. D9: `code/build_app_data.py` (folder must be <50 MB).
11. D10: `code/test_evidence_engine.py` (5 tests) then `code/run_d10.py`; agent QA of 6 answers vs tables (self-approve per user decision; edit unsupported sentences).
12. D11: sync data (deploy_space.py does it), local streamlit test w/ real data in BOTH modes (code/test_discovery_app.py; AI mode via LIVE_LLM_* from .env), screenshots to figures/screens/, then `.venv/bin/python code/deploy_space.py --folder space_discovery --name photo-retrieval-discovery`; poll RUNNING; live-URL test desktop+mobile; `.venv/bin/python code/basic_mode_proof.py` (delete secrets -> restart -> test -> restore -> test); record LINK_discovery in research/links.md; secret-scan space_discovery files.
13. Update deck/notes_for_deck.md with final numbers; append final STATE BLOCK; report to user with checkpoint tables.
Pitfalls: pandas 3.0.6 (no pd.np); altair 6 (no add_layer, encode kwargs only, no Parameter bind); streamlit text widgets commit on blur (buttons must be always-enabled); LLM alias qwen38-27b routes to gemma4 backend (noted in D0); reddit RSS ~1 req/55-60s.

# STATE BLOCK — session 2026-10-06 ~14:00-16:00 IST (agent 2; handoff from agent 1)
Running persistent exec sessions (poll with write_stdin):
- 32296: build_library.py TOP-UP run (e02/e06/e12 new queries + deep top-up; screen cached for old imgs). M1 first pass done: 475 dl, screen flagged 173 -> 302 kept (<380 checkpoint) -> top-up launched to reach >=380.
- 45949: collect_reddit_arctic.py (NEW SOLUTION for rate-limited Reddit): phase C (archive search) aborted (endpoint 422s persistently); phase A postmeta ~done; phase B comments for ~360 posts at ~3s pace (~30-40 min). Then merge + score patch.
- 38083: (done) M1 first pass.
Key decisions this session:
- Reddit JSON 403 + RSS comments sustained 429 => Arctic Shift archive API (no key): posts/ids + comments/search. RSS loop killed (0 progress, parts safe). Deviation to state on deck.
- D7 COMPLETE: 55-doc second-model audit by agent 2 (agent 1's labels unrecoverable; re-audit is independent). TEST n=40: is_retrieval 97.5% (k=.931), photo_type 100%, failure_gate 67.5% (k=.569), outcome 80% (k=.691). Gate<70% -> wrote stage2_v2.txt (3 disambiguation rules from DEV disagreements) -> v2 on 40 TEST docs: gate 62.5%, is_retrieval 90% = WORSE -> KEEP v1 (integrity: reported prompt = v1 = prompt producing episodes_full). v2 = next step, recorded in validation_report.json before_after.
- run_stage2.py: added --pass v2 + --docfile (eval runs).
- M1: fixed screen_one tuple-unpack crash (llm_json_batch returns fn's tuple); EVENTS extended for e02/e06/e12 (top-up queries).
- nohup children DIE when parent exec session ends (twice). Launch long jobs as persistent exec sessions.
NOT YET WRITTEN->WRITTEN: code/synthesis_r2.py (R2, runs when research/notes.csv exists; P1/P2 mechanical + P3 scaffold), code/keepalive.py (M10).
D track remaining: reddit merge -> d4_checkpoint -> clean_merge(D5) -> d5_checkpoint -> filter stage2 orphans -> run_stage1 -> run_stage2 v1 (increment) + v1b (increment) -> finalize_stage2 -> D8 analyze -> D9 build_app_data -> D10 tests+cached answers -> D11 local tests + deploy + basic-mode proof.
M track: M1 top-up -> M2 tag_images (local, 8w) -> M3 build_meta -> M4 embed_images -> M9 sim eval (bg) -> M5 build_tasks -> M6 test_engine (fill rules half of task_parses) -> M7/M8 streamlit + Playwright tests -> M10 deploy.
R track: R1 kit DONE (11 files, friend-ready script). R2/R3 pending notes.csv from user's friends.

# STATE BLOCK — session 2026-10-06 ~16:10-19:00 IST (agent 4; handoff from agent 3)
Running persistent exec sessions:
- 27616: Streamlit Jog basic mode (LIVE_LLM_* unset), port 8502 (local demo for user; keep alive).
- 55180/45318: Discovery streamlit local servers (8501) — may be dead; relaunch if needed:
  basic: cd space_discovery && env -u LIVE_LLM_BASE_URL -u LIVE_LLM_API_KEY -u LIVE_LLM_MODEL ../.venv/bin/python -m streamlit run app.py --server.headless true --server.port 8501
  AI: same with LIVE_LLM_* from .env (never print values)
- 73697: python http.server 8610 serving space_discovery_static (local preview; kill: lsof -ti tcp:8610 | xargs kill)
Decisions:
- HF dynamic spaces 402 (free plan; static only). SHIPPED static Discovery Engine: https://pm-ai-18-photo-retrieval-discovery.static.hf.space/ (live, tested desktop+mobile 5/5, 0 JS errors). Dynamic deploys one-command ready (deploy_space.py fixed for huggingface_hub 1.x: create_repo repo_type=space space_sdk=docker, runtime.stage poll, real host from API; --sync-data).
- Cloud Run fallback: code/deploy_cloudrun.py + Dockerfiles in both spaces; BLOCKED on user `gcloud auth login` (stored token + both SA keys expired).
- All remaining human gates delegated & logged: D7 labeling (second-model audit), D10 answers approved (self-QA, 2 edits), M5/M2/M1 gates (prior sessions), D11 basic-mode-proof (queued until a dynamic space exists).
Done (this session):
- D-chain finalize PASS: episodes_full.parquet=182 (of 765); quote_verified 99.3%; gate pass-2 agreement 91.2%; errors 0. D6 checkpoint >=400 NOT met (report shortfall honestly).
- validation_report.py re-run (fresh gate_pass_agreement into report).
- D8: analyze.py 2 numpy bugs fixed (T7 column_stack.to_numpy, rank order[:,j]); T1-T7 + F1-F6 + findings.json + T1 robustness; figures visually verified (F3 sparse = data reality). n_scored_cells=3 (update_counts).
- D9: build_app_data.py (cluster_label->mechanism_cluster_label rename); data/app 1.6MB; username scan 0 hits; snippets <=280.
- D10: test_evidence_engine 5/5 PASS (fixes: TF-IDF force path doc-side + single vocab + token_pattern; semantic_search membership-mask alignment; _step_equivalent; args-unwrap in validate/run). run_d10: 6/6 verified LLM answers (plan merge llm+keywords; head-only number check; year strip; table-n sums; thin-evidence note). 2 sentences self-edited (Q3 phrasing, Q6 none_stated majority).
- D11 local: test_discovery_app 6/6 PASS basic + 6/6 PASS AI + 6/6 PASS mobile; screenshots figures/screens/discovery_*.png.
- Static space built: code/build_static_space.py (NaN->null fix!) + space_discovery_static (index/app.js/style/data.json 0.26MB + F1-F6); local smoke 11/11; deployed via upload_file (upload_folder 401 pipelined bug — use upload_file per file); live URL tested desktop+mobile.
- M10: space_jog ready; deploy blocked as above. keepalive.py deferred (no dynamic spaces live; static space does not sleep).
- R3: research/problem_definition.md + code/verify_problem_definition.py PASS (67/67 numbers in sources; no forbidden phrase).
- deck/notes_for_deck.md session-4 final block appended (all final numbers).
Not done (user-side or queued):
- HF billing card OR gcloud login (one of the two unblocks dynamic deploys). Then: deploy both, live tests desktop+mobile, basic-mode-proof (delete secrets -> restart -> test -> restore), 90s video, keepalive, links.md LINK_mvp.
- Real R2 from friend videos (protocol + kickoff message ready).
- Deck (module K) from notes_for_deck.md; Google Docs copies at the very end.

# STATE BLOCK — session 2026-10-06 ~17:20-18:20 IST (agent 5; handoff from agent 4 — REDISIGN)
Mission (user): "both platforms look very raw / school-project / phone UI on a laptop — make them extremely impressive, professional, clean; use Gemini keys for AI."
DONE this session:
- Static Discovery Engine (the LIVE one) fully redesigned: space_discovery_static/{index.html,app.js,style.css} rewritten. Design system: Inter, indigo→violet gradient accents, white cards, Okabe-Ito gate palette (locked), CI whisker bands, pipeline stepper with real counts (Collected 32,412 → Cleaned 8,383 → Screened 3,316 → Relevant 765 → Episodes 182), cue-matrix T2 (remembered vs forgotten) now SHOWN (was in data.json but never rendered), evidence cards with gate-colored accents, [ep:id] refs flash-highlight evidence, prev/next pagination, live weight sliders, lev-off toggle. data.json schema UNCHANGED (no rebuild needed).
- code/test_static_site.py (NEW, replaces ad-hoc 11/11): 25/25 PASS desktop 1440×900 + mobile 390×844, 0 JS errors. Bugs found & fixed: #epsearch had no input handler; esc() lost HTML entities in heredoc.
- Uploaded per-file (index.html, app.js, style.css) to pm-ai-18/photo-retrieval-discovery; LIVE verified https://pm-ai-18-photo-retrieval-discovery.static.hf.space/ desktop+mobile, new content confirmed, 0 JS errors. Screenshots: figures/screens/discovery_redesign_*.png + discovery_live_redesign_*.png.
- Jog MVP: classic-mode test PASS and M8 test-mode test PASS on the (already rewritten) app; counterbalancing P1-P6 verified; desktop-viewport screenshots (jog_desktop_1_home/2_results/3_progress.png) confirm the two-panel desktop layout looks professional on a laptop.
- Streamlit Discovery (space_discovery/app.py) restyled to match: .streamlit/config.toml (theme indigo), CSS injection (Inter, pill tabs, metric cards, rounded expanders), hero (gradient headline "Where does photo retrieval actually break?", mode badge pill, 5 metric cards), sidebar pipeline counts corrected (collected=32,412, cleaned 8,383, screened 3,316, relevant 765, episodes 182/765). test_discovery_app.py 6/6 desktop + 6/6 mobile, 0 JS errors. .dockerignore does NOT exclude .streamlit → theme ships in Docker builds.
RUNNING persistent sessions:
- 26649: Streamlit Discovery AI mode, port 8501 (LIVE_LLM_* from .env, values never printed).
- (8502) Jog AI mode server from prior session still up (pid 62457).
STILL BLOCKED (user-gated, unchanged):
- Dynamic (Streamlit) HF spaces: 402 on free plan → user adds billing card → `deploy_space.py` ready (fixed for huggingface_hub 1.x). Then: deploy space_jog + space_discovery, live desktop+mobile tests, basic-mode-proof (delete secrets→restart→test→restore), 90s screen recording, keepalive.py, links.md LINK_mvp.
- Cloud Run fallback ready (code/deploy_cloudrun.py) but blocked on user gcloud auth.
- Real R2 interviews: user will have friends do the scripted interviews (R1 kit done in research/kit/). When videos/notes arrive → code/synthesis_r2.py.
- Deck (module K): build from deck/notes_for_deck.md at the end (user defers it).

# STATE BLOCK — session 2026-10-06 ~17:50-18:30 IST (agent 5b — JOG BUGFIX)
User reported: "Jog is not working ... StreamlitWidgetAlreadyInstantiatedError". Root causes (all in space_jog/app.py, engine untouched):
1. EXAMPLE CHIPS (the user's exact error): chip handler did st.session_state["jog_membox"] = ex AFTER the text_area(key="jog_membox") was instantiated in the same run -> StreamlitWidgetAlreadyInstantiatedError. Fix: on_click=_fill_membox callback (runs before widget instantiation).
2. st.columns([4,1], align="end") — `align` not a valid kwarg in streamlit 1.65 (it's vertical_alignment). Broke EVERY free-mode render with TypeError. Fix: vertical_alignment="bottom". (This line appeared in a late edit after the last verified test pass of the previous session.)
3. Confirm card needed TWO clicks in free jog play (confirm_img set mid-run after _confirm_flow's check). Fix: st.rerun() in setattr_confirm and in the fallback "✔ This one" handler -> single click shows the card.
4. Error card now prints str(e)[:220] (was class name only) — faster future diagnosis.
VERIFIED: code/repro_jog_widget.py 25/25 steps (all free-play branches incl. chip path, both modes, reset); test_jog_app.py M7 PASS (success on first confirm click, p95=3431ms); --classic PASS; test_jog_testmode.py M8 PASS (counterbalance P1-P6 + events log). 0 JS errors.
RUNNING: 8502 Jog AI mode (persistent session 38904, log logs/streamlit_jog_8502.log); 8501 Discovery AI mode (session 26649).

# STATE BLOCK — session 2026-10-06 ~18:30-19:00 IST (agent 5c — JOG UI REDESIGN)
User: "redesign Jog to match the Discovery Engine UI I like; text way too much; simplest product-like UI; no random <> characters."
DONE:
- space_jog/app.py UI layer fully rewritten (954 lines). Engine, jog_engine/, logger.py, live_llm.py, tasks/data untouched. All log events + payload keys identical (analysis pipeline safe).
- Design: Discovery-Engine language — sticky top bar (logo tile 🧭, brand, mode badge pill, "302 photos · 13 events"), gradient-word hero ("Find the photo you half-remember."), white cards 16px radius on #f4f5fa, indigo→violet primary buttons, pill tabs/radios, cue chips as pills, moment cards with why-matched line, gradient success card.
- Copy cut ~60%: hero 2 lines; deleted "How Jog works" card; card subs ≤ 8 words; footer 1 line; task card 1 line ("3:00 · no feedback until the end").
- BUG FIXES: (1) 3× st.markdown with <div> lacking unsafe_allow_html=True → raw tags visible in UI (the 'random <>'): 'Top 30 matches', 'Most likely moments', 'Study session'. (2) All dynamic values (cue values, moment labels, why-line, question text/options, captions, fragments, ids, dates) now html-escaped. (3) kept earlier fixes: on_click chip (widget error), vertical_alignment, single-click confirm reruns.
- Mobile: CSS stacks the top-level 2-panel columns below 980px.
VERIFIED: repro 25/25; M7 PASS (success on first confirm click, p95=2567ms); classic PASS; M8 testmode PASS (counterbalance + logs); 0 JS errors; screenshots jog2_desktop_home/results/question.png + jog2_mobile_home/results.png visually verified.
RUNNING: 8502 Jog (session 72781, AI mode, log logs/streamlit_jog_8502.log); 8501 Discovery (session 26649).

# STATE BLOCK — session 2026-10-06 ~18:55-20:00+ IST (agent 6 — LIBRARY SCALE-UP + PM/UX PASS)
Mission (user): "we need 2000+ images. continue" + brutal PM/UX dissection of both tools + clear 2-3 line landing intros.
DONE this session:
- code/build_library.py: EVENTS scaled (targets sum 2760; e13 620) + ~120 new diverse queries; --append mode (keeps existing 584 rows/ids, re-phashes 400 non-deleted, continues from img_0585, per-event non-deleted shortfall fetch at depth 0→1→2, resume-safe via m1_api.jsonl).
- code/build_meta.py: append-safe — keeps existing meta rows byte-identical (M5 geometry safe), new rows use per-image crc32-seeded rng, day sampled from existing per-event day distribution, e13 place via stable rng (no salted hash()).
- code/sync_space_jog.py (new): idempotent sync of data files + non-deleted images into space_jog, orphan removal.
- code/library_scale_up.py (new): driver chaining build_library --append → tag_images local --resume --workers 8 → build_meta → embed_images → sync_space_jog → verification (row-count consistency, per-event 60%, M5-critical images).
- LAUNCHED as persistent session 4814, log logs/library_scale_up.log. At 19:32: e08 (8/13), 1660 image files.
- PM/UX dissection: research/pm_ux_review_2026-10-06.md (per-screen verdicts for both tools).
- JOG UX fixes (space_jog/app.py only; engine untouched): compact hero when session active; 2-3 line landing hero (what/what-to-do/demo caveats); example chips word-boundary cut ≤28; submitted-memory echo ("You said"); low-match honest note when top-moment score < 0.55 (measured: strong 0.71 / weak 0.60 / cue-less 0.50); confirm card shows caption+date instead of raw img_id; "No" → toast nudge; success screen shows the FOUND photo+caption+date; classic success shows photo instead of raw id; loading copy fixed; QUESTION OPTION LABELS HUMANIZED (raw enums like hostel_or_home leaked to users — real bug; raw values still passed to engine; repro test's expected labels now match).
- DISCOVERY static (LIVE): landing lede rewritten (what it is / what to do / keep 32,412); free-text ask gets computed "Direct read:" lead line (votes, no AI). REDEPLOYED to static space (app.js upload; verified live serving after 15s). Streamlit Discovery hero aligned (same 2-3 line intro).
- TESTS: repro 25/25 PASS (twice), M7 PASS p95=2577ms 0 JS errors, classic PASS, M8 PASS (counterbalance + logs), static 25/25 PASS. Screenshots: figures/screens/jog3_*.png (home/searching/lowmatch/success/question_labels) + /tmp zooms.
- Mysterious stale question card in one screenshot (humanized "Café/Office" options): does NOT reproduce in fresh contexts; current code verified correct via live DOM + engine repro; no code explanation found (no stale pyc, server cwd correct). Flagged, not a regression.
RUNNING: session 4814 (scale-up chain); 72781 Jog server :8502 (AI mode); 26649 Discovery :8501.
NEXT (after scale-up finishes, driver does it): verify (2000+ non-deleted target; M5-critical present) → re-run 4 Jog suites + static test → sync done by driver → update notes_for_deck.md with final library numbers.
STILL BLOCKED (user-gated, unchanged): dynamic Space deploys (billing card OR gcloud), friend interview videos → real R2, deck (module K).

# STATE BLOCK — 2026-10-06 ~22:45 IST (side conversation — NEW USER-AUTHORIZED WORK QUEUE)
User (side conversation, then main-thread directive): "everything mentioned in the last 3 responses — do everything, queue it after the current task."
ACTION: full ordered spec written to **WORK_QUEUE.md** (repo root). It is the next unit of work for the main thread, to be executed ONLY after Gate 0 (the currently running celebrity download → tag → meta → embed → face pipeline → sync → test-suite task) completes.
Queue summary: P1 design system + chrome (Roboto Flex, tokens, one icon set, GP app bar / bottom nav tonal-pill active state, search pill in app bar) → P2 home (cinematic memories, inline onboarding card, month grid, NEW lightbox) → P3 search (suggestions, grouped results People/Places/Scenes/Photos, zero-result router) → P4 guided loop (desktop split view + progressive results, chat styling, confidence strip, "not this but close") → P5 intelligence features (face-based questions, candidate-completion cards, festival date inference, ask-less auto-cues, simulated "still searching" card, share-on-success) → P6 motion/skeletons/polish (delete Uploads tab) → P7 ship (public URL via free path first, 90s recording, Part 6 with 3 users, deck, validation polish).
Invariants restated in WORK_QUEUE.md: log events + test-mode label contract unchanged; tests updated in lockstep; no stack traces/secrets; screenshot QA matrix per phase.
NOT touched this side conversation: no app code, no servers, no running jobs — only WORK_QUEUE.md (new) + this block.

# STATE BLOCK — session 2026-10-06 ~22:15-24:xx IST (agent 8 — GP-clone data finish + autonomy chain)
Mission: user delegated everything (returns in a few hours). Finish the Google-Photos-style MVP with the People feature: +1,000 recognizable-person photos (Commons celebrities as stand-ins), face-grouping data, full test+QA pass, leave everything runnable.
DONE:
- Bugs fixed in space_jog/app.py: (1) _photo_grid_confirm ignored key_prefix → StreamlitDuplicateElementKey in multi-day fallback (repro-caught); (2) mobile bottom nav fixed block 385px tall intercepting bottom content (explicit height:84px + [data-testid="stMain"] padding-bottom 100px); (3) Voice search accessible name corrupted by :material icon (inline-SVG .micmark instead); (4) repro race on two-click nav (wait_for visible).
- code/fetch_celebs_final.py (NEW, replaces resume/deep): single CSV writer, search-based Commons category discovery (incl. "in <year>" + "by year/decade/family" trees, ≤25 cats), 2.0s pace, 120s global 429 pauses (max 6/person), phash dedupe, per-person CSV+ATTRIBUTION commit, orphan cleanup at start. Wikimedia IP is heavily throttled (429 storms since the 8-worker storm of agent 6); run in progress (log logs/celeb_final4.log). Supply reality: Indian stars thin on CC-licensed photos (Hrithik ~7 total usable so far), Hollywood better.
- code/build_meta.py: new rows carry person_key (existing rows get "" — values untouched, M5 geometry safe).
- code/sync_space_jog.py: copies people.json (ground_key STRIPPED — no real names ship) + faces/ avatars into space_jog/data/.
- code/face_pipeline.py: avatar pick = max(score, area) (was first-match).
- code/celebrity_chain.py (tag local --resume --workers 8 → build_meta → embed_images → face_pipeline --resume → sync → verify) + code/verify_library.py (row-count/emb/space consistency + per-person counts) + code/finish_chain.py (autonomous: wait fetch → chain → detached server restart :8502 → test_jog_people.py → repro/M7/classic/testmode → verify; all logged to logs/finish_chain.log).
- code/test_jog_people.py (NEW): onboarding dialog pick/skip, 'You' label, person filter view, tag-panel People group; desktop + mobile.
- code/test_jog_{widget,app,testmode}.py: dismiss_onboarding() after page load (robust pre/post people.json).
- Tests PASS after fixes: repro 25/25, M7 mobile p95=2596ms 0 JS err, classic, M8 testmode (counterbalance P1-P6, logs download). Desktop QA screenshots qa_desktop_{1..4,*topclip}.png: no black bar, Gemini branding, search hero + runtime tag panel (Places/Moments/Things/Dates from real data), guided flow, classic results, mic "Listening…" state.
- Discovery static re-verified LIVE (title/h1/4 tabs/6 presets, 0 JS errors).
RUNNING: session 83834 fetch_celebs_final (logs/celeb_final4.log); session 52427 finish_chain (logs/finish_chain.log).
NEXT (after chain): fill final numbers into deck/notes_for_deck.md (celebrity per-person counts, final library size, persons/clusters), final visual QA of People row + onboarding + person filter (qa_people_*.png), links.md notes, final message.
STILL USER-GATED (unchanged): dynamic HF Space deploys (402 billing card) / Cloud Run (gcloud auth); 90s recording; deck (module K) — notes accumulated in deck/notes_for_deck.md.
