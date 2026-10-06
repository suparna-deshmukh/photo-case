# Google Photos Retrieval Case Study - Project Folder (BASE)

Fellowship case study: "Increase the percentage of Google Photos users who successfully retrieve a photo they remember but cannot precisely describe."

Deliverables:
1. AI-powered Discovery Engine (public web app analyzing public user feedback)
2. Deployed AI-native MVP "Jog" (public web app)
3. Research artifacts (interview kit, test kit)
4. 10-slide PDF deck

Everything must be real, reproducible, and traceable.

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
- plus .env (never uploaded), .gitignore, STATE.md, forbidden.txt (user-typed, never uploaded/echoed)
- docs/ = archive of role-and-rules.md (v3) and locked-context.md (v3 verbatim) - additive, not in the locked layout

## Status
Initialized 2026-10-06. BASE layout complete, .venv created (3.13.14). No modules delivered yet.
.env missing (keys-and-logins session in D0). forbidden.txt empty (user types it).
