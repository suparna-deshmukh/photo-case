# LOCKED CONTEXT (v3 - saved verbatim per R12, re-pasted by user 2026-10-06; supersedes v2)

PRODUCT CONCEPT (name: "Jog") Insight: People remember photos episodically (who/what happened before and after/why they took it/roughly when), not by content labels. Recognition is easier than recall. Search UIs ask for precise recall, show a flat grid of near-duplicates, and give no help after the first query fails. Existing Ask Photos answers well-formed questions; Jog treats the query as INCOMPLETE and helps the user reconstruct the memory through guided narrowing. (Any claim about Ask Photos' current availability/behaviour must be verified from official sources before it is shown anywhere.) Jog flow: brain-dump text → editable cue chips with certainty → results grouped into "moments" (not a flat grid) → one discriminating question (information gain) → "this or that" visual comparison (relevance feedback) → anchor pivots ("right after this photo") → graceful fallback to a narrowed timeline (never a dead end). Where AI is used: image tagging (offline), CLIP embeddings (visual matching), cue parsing with certainty (rule-based primary; live LLM optional), information-gain question selection (algorithm, not LLM), relevance feedback (vector math). Where AI is NOT used: confirm/deny UI, fallback timeline.

TARGET SEGMENT (working hypothesis, to be validated by research) Long-tenure, high-volume personal-library Google Photos users aged 20–25 (3+ years of photos, thousands of items), Android-first, who retrieve both experience photos (trips, events) and utility photos (medicine, notes, receipts).

FAILURE GATES (the metric decomposition; use these exact enum values)

expression: user cannot turn what they remember into a query/input
interpretation: system does not understand or ignores the clues given
evaluation: target is among results but user cannot recognize/compare it (too many similar results, grid hides context, too slow)
refinement: first attempt fails and there is no effective way to adjust or recover
persistence: user gives up / stops trying / says they no longer search
not_search_related: sync, backup, deletion, storage problems
unclear: cannot tell

ENUMS (use these exact values everywhere) photo_type: trip_event | people_social | food_place | scenery_pet | document_utility | screenshot | video | other_unspecified retrieval_intent: find_specific_photo | find_set_or_moment | find_info_inside_photo | find_by_person | other photo_age: recent_lt_6m | six_to_24m | over_2y | unspecified cue_type: person | place | time_when | event_context | anchor_relation | visual_detail | setting | activity | emotion_or_vibe | purpose_or_reason | text_in_image | source | device_or_app | other cue_certainty: high | medium | low query_style: keyword | natural_language | date_or_filter | people_or_face | map_or_place | browse_scroll | ask_photos_chat | none_stated workaround: scroll_timeline | search_other_app | ask_other_person | manual_albums_or_favorites | rename_or_describe | use_other_service | switch_to_classic_search | gave_up | none_stated outcome: found | partly_found | not_found | unknown stakes: low | medium | high era (by review date): pre_ask (before 2024-10-01) | early_access (2024-10-01 to 2025-05-31) | wider_rollout (2025-06-01 onward). Working assumption; D0's fact check may refine it; flag "verify before showing in deck" until I approve.

PALETTE (Okabe–Ito, colorblind-safe) blue 
#0072B2, orange 
#E69F00, green 
#009E73, vermillion 
#D55E00, pink 
#CC79A7, sky 
#56B4E9, yellow 
#F0E442, black 
#000000, grey 
#999999. Gate colors: expression=blue, interpretation=orange, evaluation=green, refinement=vermillion, persistence=pink, not_search_related=grey, unclear=sky. Figure standard: matplotlib figsize=(10,5.625), dpi=200, base font size 16, title font 18, always show n in the title or footer, label bars directly (not only legend), PNG.

TECH STACK (fixed; do not substitute without approval)

Everything runs LOCALLY via tools: Python 3.10+ in a virtual environment BASE/.venv; scripts in BASE/code; no notebooks unless I ask; no Google Colab.
BASE = photo_case folder (default ~/photo_case on Mac/Linux, C:\photo_case on Windows, unless I name another). Google Drive/Docs/Sheets/Forms/Slides are used ONLY for shared artifacts and links.
Libraries: pandas, pyarrow, numpy, pydantic v2, openai (client; local helper only), requests, tqdm, scikit-learn, sentence-transformers, altair, matplotlib, google-play-scraper, rapidfuzz, langdetect, statsmodels, Pillow, imagehash, streamlit, python-pptx, pypdf, pymupdf, python-dotenv, huggingface_hub, playwright (Chromium); optional offline-tagging extras: transformers, easyocr. LibreOffice (headless) for deck-to-PDF rendering.
LLM PROFILES (env vars in BASE/.env): • local: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL — my Qwen served through a LiteLLM proxy (OpenAI-compatible). D0 discovers and fills these. LiteLLM may alias model names and may drop unsupported parameters (JSON mode, thinking switches); D0 verifies what actually works. • hosted (public apps' live layer; optional): LIVE_LLM_BASE_URL, LIVE_LLM_API_KEY, LIVE_LLM_MODEL — default Google AI Studio (Gemini) base URL https://generativelanguage.googleapis.com/v1beta/openai/ with a Flash or Flash-Lite model that the CURRENT pricing page marks free of charge (verify). Optional LIVE_DAILY_CAP (default 300). • other secrets in .env: PEXELS_API_KEY, HF_TOKEN (Hugging Face WRITE token). • In Hugging Face Space secrets ONLY the three LIVE_LLM_* names are used (never the local ones, never HF_TOKEN).
Local usage is unlimited: no volume caps unless a module says wall-clock requires one. llm_helper.autotune_workers() picks the worker count (1–8) by measured throughput.
Public-app live-layer constants: PER_SESSION_CAP=10, DAILY_CAP=300, TIMEOUT_S=8, PROBE_TIMEOUT_S=3, circuit breaker (2 consecutive failures → pause live calls for 120 s).
Hosting: Hugging Face Spaces (free CPU), SDK = Streamlit. Spaces: photo-retrieval-discovery and jog-memory-retrieval (if taken, add a neutral suffix such as -lab). Deploy with huggingface_hub scripts; web uploader is the fallback.
Image source for the demo library: Pexels API with an attribution CSV. Fallback: Wikimedia Commons API.
Deck: python-pptx → LibreOffice PDF render → automated checks; Google Slides route as fallback.

NAMING / NEUTRALITY Neutral names only. Hugging Face username must NOT contain my name or ID.

FOLDER LAYOUT (create exactly) BASE with: .venv, cache, code, code/jog_engine, code/prompts, data, data/tables, data/app, figures, figures/screens, research, research/test_logs, library, library/images, library/contact_sheets, space_discovery, space_jog, deck, deck/pages, qa, logs. Plus .env (never uploaded), .gitignore, STATE.md, forbidden.txt (name tokens I type myself; never uploaded, never echoed).

SHARED FILE REGISTRY (names are fixed) code/llm_helper.py (local+hosted client for offline jobs) · code/live_llm.py (public-app live layer) · code/pipeline_counts.py → data/pipeline_counts.json · code/schemas.py · code/evidence_engine.py · data/_raw.parquet · data/docs_clean.parquet · data/docs_for_llm.parquet · data/stage1.parquet · data/episodes_full.parquet · data/validation_report.json · data/tables/T1–T7 CSVs · data/app/ · research/tools_inventory.md · research/llm_probe.json · research/ask_photos_facts.md · research/links.md (every shared Google link, appended by whichever module creates it) · library/{events.csv, images/, images_raw.csv, ATTRIBUTION.md, tags.parquet, meta.parquet, gazetteer.json, image_emb.npy, emb_index.json, tasks.json, task_parses.json, examples.json} · code/jog_engine/* · space_discovery/ · space_jog/ · qa/QA_REPORT.md.

NOTE: In the PALETTE block, each colour name and its hex were received on separate lines (name, then hex on the next line, with the next colour name on the same line as the previous hex). Mapping used: blue #0072B2, orange #E69F00, green #009E73, vermillion #D55E00, pink #CC79A7, sky #56B4E9, yellow #F0E442, black #000000, grey #999999 (standard Okabe-Ito values).
