# Google Photos Retrieval Case Study — "Jog" MVP

**Jog** (project dir: `photo_case`): a fellowship case study on the problem
"Increase the percentage of Google Photos users who successfully retrieve a
photo they remember but cannot precisely describe."

It ships two public web apps — a **Google Photos-styled, AI-guided photo
retrieval MVP ("Jog")** and a **Discovery Engine** over ~32k real public
feedback documents about finding old photos — plus the research artifacts
behind both (interview kit, test kit, pre-registered hypotheses, 10-slide deck).

Everything must be real, reproducible, and traceable. Both apps work with
**ZERO LLM configured** (R15); the live LLM is an optional layer.

## System design

```
                       ┌──────────────── browser (Streamlit, GP-2026 chrome) ────────────────┐
                       │ space_jog/app.py — Material 3 tokens (assets/gp.css), inline SVG    │
                       │ search hero (text + voice) · tag panel · People · Memories · date   │
                       │ custom lightbox overlay · mobile bottom nav · ?test=1 task mode     │
                       └───────────────────────────────┬─────────────────────────────────────┘
                                                       │ same process (no API boundary)
                       ┌───────────────────────────────▼─────────────────────────────────────┐
                       │ jog_engine (code/jog_engine, mirrored into the app):                │
                       │  parse_memory: cache → optional LLM → rule parser (PRIMARY)         │
                       │  retriever: score = W_VISUAL·vis + W_TIME·t + W_PLACE·p +           │
                       │               W_ATTR·attr    (CLIP embeddings + meta.parquet)       │
                       │  question picker: Shannon entropy × prior × don't-know decay        │
                       │  why-matched lines (deterministic) · this-or-that vector update     │
                       │  fallback: narrowed window + day-grouped grid (no dead ends)        │
                       └───────────────────────────────┬─────────────────────────────────────┘
                                                       │ optional
                       live_llm.py — requests-only, never raises · caps 10/session, 300/day
                       (LIVE_DAILY_CAP) · breaker 2 fails → 120 s · LRU-500 input cache
                       (hits free) · nothing written to disk or logs, keys never printed
                       (zero-LLM mode: every path above still works, nothing leaves the box)

                       ┌─────────────────────────────────────────────────────────────────────┐
                       │ Discovery Engine (space_discovery; Streamlit + static build)        │
                       │ 32.4k public feedback docs (Play 24.1k · App Store 5.0k ·           │
                       │   Reddit 3.3k) → 8,383 clean → 765 relevant → 182 episodes          │
                       │ ask-over-episodes · interactive exploration · paste-analysis ·      │
                       │ "Discover more": live Play/App Store/Reddit search via              │
                       │   discovery-feedback-api.vercel.app (10 req/min/IP)                 │
                       │ every number computed from bundled data · every quote a verified    │
                       │ verbatim substring · hold-out TEST set never tuned on (R18)         │
                       └─────────────────────────────────────────────────────────────────────┘
```

- **Library**: a synthetic "one person's photo history" — 3,252 free-licensed
  photos (CC0 / CC BY / CC BY-SA, credits in `library/ATTRIBUTION.md`) with
  generated dates, places (gazetteer) and recurring people. CLIP (ViT-B/32)
  embeddings (`image_emb.npy` + `emb_index.json`) and insightface (buffalo_l)
  face vectors back the People view. No uploads; nothing personal is stored.
  Images and model weights live on disk only (gitignored).
- **Jog MVP** (`space_jog/`): search is the hero — type or dictate a vague
  memory (Web Speech API, local only); clarifying questions narrow the
  window, "why this matched" explains each hit (no LLM), Memories cluster
  the top-K into moments, People groups recurring faces and lets you pick
  which one is you. `?test=1` runs the locked task suite (X1–X4/Y1–Y4) with
  contract-locked event logging.
- **jog_engine** (`code/jog_engine/`, mirrored into the app): rules are the
  PRIMARY path — the memory parser, retriever, question picker, explainer and
  fallback are all deterministic (no LLM, no network); the LLM is only an
  optional cache-bypass inside `parse_memory`.
- **Discovery Engine** (`space_discovery/`): the 182 retrieval episodes come
  from a two-stage extraction pipeline with prompt SHAs + all counts pinned in
  `data/pipeline_counts.json`; episode labels were written by an independent
  second model (declared in-app and in the deck; blind CSV kept for a later
  human pass). Paste-analysis and episode Q&A run in basic mode with zero LLM.
- **Live layer** (`code/live_llm.py`, mirrored per app): optional — local
  profile (Qwen via LiteLLM proxy, `LLM_*` env) or hosted Gemini free tier
  (`LIVE_LLM_*` env). Guarded imports, never raises; 5-min `/models` probe;
  PER_SESSION_CAP=10 / DAILY_CAP=300 (`LIVE_DAILY_CAP`); breaker 2 fails →
  120 s open; LRU-500 input cache; inputs/outputs never hit disk or logs.
- **Integrity**: R7 — the student's login email never appears in any project
  file (QA scans the `forbidden.txt` tokens); R18 — no task, metric or prompt
  is tuned on the held-out TEST data; secrets live only in `BASE/.env`
  (never uploaded) and Space/Vercel env under `LIVE_LLM_*` names.

## Run it

```bash
cd photo_case
.venv/bin/pip install -r space_jog/requirements.txt
.venv/bin/streamlit run space_jog/app.py              # Jog MVP → :8501 (?test=1 task mode)

.venv/bin/streamlit run space_discovery/app.py \
  --server.port 8502                                  # Discovery Engine → :8502
```

Keys live in `.env` (gitignored, never uploaded, values never printed). Both
apps run with no keys set at all.

```env
LLM_BASE_URL=...        # local LLM profile (Qwen via LiteLLM proxy) — optional
LLM_API_KEY=
LLM_MODEL=
LIVE_LLM_BASE_URL=      # hosted live layer (Gemini free tier) — optional
LIVE_LLM_API_KEY=
LIVE_LLM_MODEL=
LIVE_DAILY_CAP=300
PEXELS_API_KEY=         # library build only
HF_TOKEN=               # HF Space deploy only
```

## Live links & deploy

- **Jog MVP**: https://space-jog.vercel.app — full 3,252-photo library
  (Vercel 2.5 GB function-size cap, noted in the UI). Returns 502 as of
  2026-11-10 (redeploy the `vercel_deploy/` staging copy). Backup dev-machine
  tunnel recorded in `space_jog/VERCEL_URL.txt`. HF Space
  `jog-memory-retrieval` pending billing card:
  `.venv/bin/python code/deploy_space.py --folder space_jog --name jog-memory-retrieval`.
- **Discovery Engine** (live, static build):
  https://pm-ai-18-photo-retrieval-discovery.static.hf.space/ — the full
  Streamlit app runs locally; the dynamic HF Space is pending billing card:
  `.venv/bin/python code/deploy_space.py --folder space_discovery --name photo-retrieval-discovery --sync-data`.
- **"Discover more" backend**: https://discovery-feedback-api.vercel.app/
  (Vercel project `pm28/discovery-feedback-api`; `LIVE_LLM_*` as production
  env; 10 req/min/IP; CORS open for the public static page).
- Deploy staging copies: `vercel_deploy/`, `vercel_deploy_mine/`,
  `vercel_deploy_tools/`, `vercel_discovery_api/`, `vercel_redirect/`
  (model weights + image caches gitignored).

## Deliverables
1. AI-powered Discovery Engine (public web app analyzing public user feedback)
2. Deployed AI-native MVP "Jog" (public web app)
3. Research artifacts (interview kit, test kit)
4. 10-slide PDF deck

## Thread protocol (tool-first, rules v3)
1. Start every thread by pasting: ROLE + HARD RULES (docs/role-and-rules.md), the STATE BLOCK (BASE/STATE.md), and any module context. The agent then lists its tools (TP1) and continues from STATE.md.
2. The agent does the work with its own tools (shell, filesystem, browser, APIs, deploy, screenshots) and runs every CHECKPOINT itself, showing real output with PASS/FAIL.
3. The human only handles HUMAN GATES: sign-in/2FA/CAPTCHA/terms + entering secrets into .env or Space secrets (one keys-and-logins session in D0); interviews (R1/R2), user tests (T1), hand-labeling (D7), hand-editing task fragments (M5) and unsupported cached-answer sentences (D10); approval words ("pilot ok" D6, "tags ok" M2, "answers approved" D10, "approve" M5); sending messages; final deck look + submission (K1).
4. Every shell command is appended to BASE/logs/actions.log (timestamp, command, exit code). Secrets are never printed (show only "set"/"empty").
5. Locked names, paths, enums, constants: docs/locked-context.md (R12 - no changes without explicit approval).
6. The student's login email must NEVER appear in any file in this project (R7); it is used for browser login only. forbidden.txt (typed by the user) holds the name tokens QA scans for.
7. Secrets live only in BASE/.env (never uploaded) and HF Space secrets (LIVE_LLM_* names only). Never in chat, code, logs or app text.
8. Both public apps must work with ZERO LLM configured (R15); live LLM is an optional layer behind code/live_llm.py.
9. Never tune a task, metric or prompt on the held-out TEST data (R18).

## Folder map (BASE = this folder)
- .venv (Python 3.13.14), cache, code, code/jog_engine, code/prompts, data, data/tables,
  data/app, figures, figures/screens, research, research/test_logs, library, library/images,
  library/contact_sheets, space_discovery, space_jog, deck, deck/pages, qa, logs
- vercel_deploy, vercel_deploy_mine, vercel_deploy_tools, vercel_discovery_api, vercel_redirect
  (deploy staging; model weights / image caches gitignored)
- plus .env (never uploaded), .gitignore, STATE.md, forbidden.txt (user-typed, never uploaded/echoed)
- docs/ = archive of role-and-rules.md (v3) and locked-context.md (v3 verbatim) - additive, not in the locked layout

## Status
Initialized 2026-10-06. Living status + session log: `STATE.md` (milestones M*/D*/T*).
Public apps: Discovery Engine live on HF (static build); Jog MVP deployed to Vercel
(space-jog.vercel.app — 502 on 2026-11-10, redeploy pending).
Repo committed to GitHub 2026-11-10 (`suparna-deshmukh/photo-case`, private).
