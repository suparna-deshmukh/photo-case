# JOG MVP — Complete UI/UX Handoff Document
**Audience:** another LLM/agent that needs the entire context of the product to keep building, fixing, or extending it.
**Source of truth:** `space_jog/app.py` (single-file Streamlit app, ~2,800 lines) + `space_jog/jog_engine/`.
**Snapshot date:** 2026-10-07 ~02:45 IST. ⚠️ The Photos-home tab is being actively iterated by the main thread at snapshot time; everything else below is stable and code-verified.

---

## 1. What this product is

A research prototype for a **guided photo-retrieval feature inside a Google-Photos-style app**, called **Jog**. It simulates a full Google Photos experience (search, memories, people, month grid, lightbox) on a **synthetic library of 3,252 free-licensed photos** (CC0/CC BY/CC BY-SA, 2022-08 → 2026-09) with synthetic dates, places, and 13 face-clustered "people" (public figures used as anonymized stand-ins so face-grouping works; shipped labels are always "Person N", never names).

The product studies how people retrieve photos they only **half-remember**:
- **Classic mode** = control: one search box → ranked grid (CLIP visual similarity + keyword/place/year boosts).
- **Jog (guided) mode** = the feature: user describes a half-memory → immediate moment-clustered results → quick skippable questions → this-or-that comparisons → anchor dates → guaranteed fallback (never a dead end) → success screen with feedback.

**Two modes of text understanding:**
- **Basic (always works):** local rule-based cue parser + CLIP embeddings. Zero LLM.
- **AI mode (optional):** if `LIVE_LLM_API_KEY` (Gemini API) is set, the memory text is parsed by Gemini first; rules are the fallback. Mode badge shows "Gemini understanding" vs "Basic understanding".

**Honesty rules baked into the product:** demo banner on first launch, "synthetic or freely licensed" everywhere, privacy footer per mode. This is a demo for a research deck — it must never pretend to be a real personal library.

**Companion tool (not part of this doc's app):** a separate "Discovery Engine" (research analytics over user-feedback episodes) runs at `:8501` (Streamlit) and as a static site. The Jog MVP is at `:8502`.

**Deployment:** localhost `http://localhost:8502` is the source of truth. User decision 2026-10-07: deploy to **Vercel** later, once satisfied with localhost (note: Streamlit app needs a Streamlit-capable host or a static rebuild — decided with user at that time).

---

## 2. Tech stack & architecture (context for any code changes)

- **Streamlit 1.65** (pinned), Python 3.13, single `app.py`. Runs headless: `python -m streamlit run app.py --server.headless true --server.port 8502`, cwd `space_jog/`, env from `BASE/.env` (LIVE_LLM_* keys — never printed, never in files under space_jog/).
- **Data (loaded once at import, cached):**
  - `space_jog/data/meta.parquet` — 3,252 rows: `img_id` (img_0001…), `filename`, `event_id` (e01–e13, HIDDEN from users), `timestamp` (synthetic, +05:30), `place_name`, `area`, `lat`, `lon`, all tag fields (`caption`, `scene`, `setting_type`, `indoor_outdoor`, `time_of_day`, `people_count_bucket`, `dominant_colors`, `objects`, `activity`, `visible_text`, `has_text`, `season_hint`, `distinctive_detail`), `person_key` (ground truth, stripped before shipping), `synthetic_metadata=True`.
  - `space_jog/data/image_emb.npy` — 3,252×512 CLIP (clip-ViT-B-32) embeddings; `emb_index.json` row→img_id.
  - `space_jog/data/people.json` — 13 persons `{id: p1..p13, label: "Person N", count, avatar}` + `img2person` map (175 images have a face).
  - `space_jog/data/gazetteer.json` — place names + lat/lon + aliases (Goa→Panjim/Palolem, Bengaluru→Bangalore, Pondicherry→Puducherry, etc.).
  - `space_jog/data/tasks.json` — 8 retrieval tasks (X1–X4, Y1–Y4) + 2 practice (P1, P2) with `fragment_text`, `target_img_id`, decoys, fairness metadata.
  - `space_jog/data/task_parses.json` + `examples.json` — cached parses + 5 example memory chips.
  - `space_jog/images/` — the 3,252 JPEGs (≤800px, ~287 MB). `space_jog/data/faces/` — 13 avatar JPEGs.
- **Engine:** `space_jog/jog_engine/` (importable package, must stay 1:1 synced with `code/jog_engine/`): `config.py` (weights W_VISUAL .50 / W_TIME .20 / W_PLACE .20 / W_ATTR .10; certainty multipliers sure 1.0 / unsure 0.5; TOP_K 40; SOFTMAX_T .08; MAX_ROUNDS 4; moment gap 8h/10km; REL_FEEDBACK alpha 1.0 beta .6 gamma .3), `cues.py` (parse_memory: cache → llm → rules), `cues_rules.py` (the rule parser: gazetteer fuzzy match, year/season/festival windows, time-of-day words, hedge detection within 4 tokens, negation within 3 tokens, anchor phrases), `retrieval.py` (scored retrieval, min-max normalized cosine), `clusters.py` (moment clustering), `explain.py` (why-matched line), `questions.py` (entropy-based next question), `feedback.py` (this-or-that pair selection + query vector update), `anchors.py`, `fallback.py`, `session.py` (JogSession state machine).
- **Logging:** `logger.py` appends JSONL to `space_jog/logs/events.jsonl` (see §13).
- **UI error boundary:** `main()` is wrapped in try/except → writes `space_jog/logs_ui_error.txt` (check this file after any E2E) and shows only "Something went wrong in the demo. Please press Reset or reload." + a short technical note. **No stack trace may reach the user.**

**Streamlit 1.65 gotchas (learned the hard way — do not regress):**
1. `st.markdown('<div class=…>')` wrapper divs render as EMPTY standalone divs → all layout is done via **keyed `st.container(key=…)`** + CSS on `.st-key-<key>`. Never emit a `<div>` wrapper and expect children inside it.
2. Raw CSS markdown must be wrapped in `<style>…</style>` or it renders as visible text.
3. Bare-span markdown needs `unsafe_allow_html=True` or HTML is escaped to text.
4. **Widget-key collisions are fatal:** two widgets sharing a key → Streamlit resets state at the rerun boundary (this caused a real bug where the confirm dialog never opened; the fallback day-grid flag now uses `fbday_open_{task_id}_{day}`, distinct from the button key).
5. `st.rerun()` after inline `session_state` set preserves state (fine) — only the shared-key case is fatal.
6. `st.image(width="stretch")` is dead → `use_container_width=True`.
7. Raw `<img src="images/…">` NEVER works in Streamlit (unknown paths return the SPA HTML shell with HTTP 200!) → always `st.image`.
8. Playwright: clicks landing mid-rerun are dropped → every test uses click-retry loops; cold CLIP start ~14–16s after app reload (settle in tests); `animations="disabled"` for screenshots.
9. The `:has(.marker)` over-matching bug: CSS selectors like `:has(.marker)` matched app-wide and broke button styling — all styling is now keyed per-container. Do not re-introduce broad `:has()` selectors.
10. `stElementToolbar` (the dot on images) hidden globally via CSS.

---

## 3. Design system (tokens, type, motion)

**Color tokens (CSS `:root`):**
| Token | Hex | Use |
|---|---|---|
| `--gp-primary` | `#1a73e8` | primary buttons, links, active nav, focus rings, progress bar |
| `--gp-primary-d` | `#1765cc` | primary hover |
| `--gp-tonal` | `#e8f0fe` | tonal chips, badges, active-pill bg, success chips |
| `--gp-text` | `#202124` | primary text |
| `--gp-secondary` | `#5f6368` | secondary text, inactive nav |
| `--gp-disabled` | `#80868b` | disabled, counts, captions |
| `--gp-hairline` | `#e8eaed` | borders, rules |
| `--gp-fill` | `#f1f3f4` | search pill bg, chips, fills |
| `--gp-bg` | `#f8f9fa` | subtle backgrounds |
| `--gp-error` | `#d93025` | errors |
| `--gp-success` | `#188038` | success tags |
| cue negated | bg `#fce8e6` / text `#a50e0e` | negated cue chips |
| Gemini gradient | `#1ba1e2 → #9a63f0 → #ea4c89 → #f9ab00` (4-stop) | ONLY on the sparkle icon, in the search pill, guided header, mode badge |

**Typography:** self-hosted **Roboto Flex** variable (weights 100–1000, optical sizing) from `assets/roboto-flex.woff2` (local, no CDN). Headings `letter-spacing:-0.01em`. Scale: section heads 21–22px/500; card titles 16px/500; body 14–15.5px; sub 13px; micro 11–12.5px. App title "Photos" 22px/500 (desktop) / 19px (mobile).

**Shape/elevation/motion:**
- Radii: cards 16px, grid images 8px, buttons/chips/pills 999px (full pill).
- Shadows: rest `0 1px 2px rgba(60,64,67,.10)`; hover `0 4px 10px rgba(60,64,67,.16)` + `translateY(-1px)`.
- Easing `cubic-bezier(.2,0,.27,1)`, 200ms; view fade 180ms; photo cell fade-in 200ms.
- Focus ring: 2px `#1a73e8`, offset 1px, radius 8px.
- Buttons: primary = blue pill, min-height 40px, white 14px/500; secondary/tertiary = pill, min-height 36px, 14px/500, tertiary is text-style.
- Chips: pill, 7px/14px, 13.5px/500, fill `#f1f3f4`, hover `#e4e7ea`; tonal variant `#e8f0fe`/`#1a73e8`.

**Layout:** `stMain` max-width 1200px, 24px gutters (mobile: full width, 12px gutters, 40px bottom pad). Breakpoints: **900px** = desktop↔mobile (app bar vs top row + bottom nav); 700px, 1100px, 1280px adjust grids. Streamlit's own header/sidebar/toolbar are hidden via CSS. White background everywhere (the "black bar" was fixed by forcing white html/body).

**Icon system:** single inline-SVG helper `icon(name, s, c)` (Material Symbols Rounded paths) + `pinwheel` (GP pinwheel, 4-color) + `sparkle` (Gemini 4-stop gradient). No CSS ::before data-URI icons except bottom-nav.

**Gemini branding rule:** the sparkle symbolizes AI *inside* search — it appears in (a) the search pill (right side), (b) the guided-flow header, (c) mode badges, (d) suggestion/nudge cards. It is a mode, never a destination tab (except the mobile center nav pill, which is the guided tab).

---

## 4. App chrome (both viewports)

### Desktop (≥901px) — sticky app bar (64px, white, 1px hairline bottom)
Left→right, one row:
1. **Pinwheel** (27px GP logo) — decorative.
2. **"Photos"** button (22px/500, text-styled) → goes to Photos home.
3. **Search pill** (flex-1, max 720px): `#f1f3f4` pill, 4px/6px/4px/16px padding. Inside left→right: text input (aria-label **"Search Google Photos"**, 15px, placeholder grey) · **mic icon button** (40px circle, "Voice search") · **Gemini sparkle button** (34px circle, "Ask Gemini").
   - **Enter / on-change submit** → classic search: sets `search_q`, switches to Search tab, runs `_classic_go`.
   - **Sparkle click** → guided search with the pill text prefilled + autostart (even if empty).
   - Focus state: white bg + shadow `0 1px 6px rgba(60,64,67,.28)`.
4. **Avatar** (28px circle, `#1a73e8`, white "D") → **popover menu**: caption "Demo user", then buttons **"How this works"** (→ Settings/How), **"About this demo"** (→ Settings/About), **"Reset"** (secondary, clears all session state → Photos home).

### Mobile (≤900px)
- **Top row** (replaces app bar): pinwheel 24px + "Photos" 19px · **search icon** (40px icon button → Search tab) · **settings gear** (→ Settings tab).
- **Bottom nav** (fixed, white, hairline top, 56px + safe-area-inset; 5 equal columns): **Photos** · **Search** · **Gemini** (center, sparkle icon, accessible name **"Ask Gemini"**, tonal-pill style) · **People** · **Settings**. Active item = icon inside `#e8f0fe` tonal pill, icon `#1a73e8`, 24px icon + 11px/500 label; inactive `#5f6368`.
- **Footer note** (all tabs, 12px `#80868b`, 28px top margin):
  - AI mode: "No uploads. In AI mode, your description is sent to Google's Gemini API to understand it (free tier). Don't enter personal information. Demo data only."
  - Basic mode: "No uploads. Your text is processed inside this demo and not sent to any external AI service. Demo data only."

**Navigation model:** `st.session_state["tab"]` ∈ {photos, search, guided, people, settings}. All nav actions set tab + `st.rerun()`. In test/admin mode the app bar/bottom nav are replaced by a minimal bar (pinwheel + "Photos" only).

---

## 5. Photos home (tab: photos) — full inventory, top to bottom

1. **Filter chip** (only when a filter is active — memory/person/place/event): tonal pill `#e8f0fe`/`#1a73e8` with the filter title (e.g. "Goa · 116 photos") on the left + **"✕"** tertiary button on the right → clears filter.
2. **Demo card** (first visit only, until dismissed): row = [blue "DEMO" chip 11px/600 white-on-`#1a73e8`] + text 13.5px "A Google Photos demo — every photo, date, place and person is synthetic or freely licensed." + small close icon button (right). Dismissal persists in session.
3. **Memories** section (head 21px/500): horizontal snap-scroll row, cards 280px (mobile 236px), 16:9 full-bleed photo with dark bottom gradient scrim; overlays: "Memory" chip (top-left, dark blur pill), white title 15.5px/500, white-78% sub 12px (e.g. "Jan 2023 · 321 photos"). Whole card clickable → sets `mem_filter` (event/person/theme) and re-renders the month grid filtered. **Computed at runtime, never hand-written**: top events by photo count; "With Person N" (persons with ≥15 photos); caption-theme memories (regex: Sunset moments, Coffee & café mornings, Food & feast days, Documents & receipts, On the move, Rainy days, Nights out — only if ≥25 matches); "Photos of you" (if user picked themselves, ≥15). Max 8, sorted by size.
4. **People** section (head 21px/500):
   - **Onboarding card** (only while `you_person` unset AND not skipped — appears here AND on People tab): bordered card; sparkle 18px + "Which one is you?" 16px/500; sub 12.5px "Pick yourself and we will recognise your photos. Skip if you like."; up to 4 persons side by side, each: 72px round avatar, label 12.5px, **"This is me"** primary button (full width). Below: **"Not sure"** tertiary (skips forever). Picking a person relabels them **"You"** everywhere (people row, filters, memories, smart questions).
   - **People row** (horizontal scroll, up to 8): each 84–96px column = 56px avatar (64px desktop) with 2px white ring + shadow, name 12.5px/500 ("You" if selected), count 11px "N photos". Click → `person_filter` → month grid of that person's photos. If >8 persons: **"See all"** tertiary → People tab.
5. **"Still searching" proactive card** (only if a guided fallback occurred this session): tonal card `#e8f0fe`: sparkle + "We kept searching in the background" 14px/500 `#174ea6` + "Closest match for “<query>”" 12.5px + one photo cell + **"Open"** secondary button (→ lightbox) + small close icon.
6. **Year/month grid:** year headers (19px/500 + "N photos" 12.5px grey + hairline rule). The **2 most recent years are expanded**; older years show a **"Show all"** tertiary to expand. Month headers: 14px/500 grey month + "N photos" 12.5px + rule. Grid: **3 cols mobile / 4 (≥700) / 5 (≥901) / 6 (≥1280)**, 8px gap, square 1:1 cells, 8px radius, 200ms fade-in. Each cell: photo (hover brightens) + an invisible full-cell button labeled "Open photo from <date>" → **lightbox**. Months with >12 photos show the first 12 + **"Show all N"** tertiary (expands in place, keyed so it survives reruns).

**Lightbox** (opens from any home/search/fallback photo cell): fixed full-screen overlay `rgba(16,16,18,.94)`; top center: caption 13.5px white + date 12.5px white-60%; image max 92vw × 76vh, 8px radius; **floating dark pill control bar** (fixed, bottom 22px, blur, border rgba(255,255,255,.12)): **Previous** / **Next** (disabled at ends) / **Close** / **"This is it ✔"** (blue primary) / **Share**. Free-play "This is it ✔" → toast "Noted — nice find." (logs `confirm_attempt`, correct=None — free play has no target). "Share" → toast "Share link copied (demo)."

---

## 6. Search (tab: search) — THE HERO FEATURE

**Search bar** (top): 56px pill, `#f1f3f4`, 2px transparent border; focus: white bg + 2px `#1a73e8` border + soft blue shadow. Inside-left: 20px search icon (55% opacity). Input aria-label **"Search your photos"** (placeholder "Search for a person, place, or thing", 15.5px). Right: **mic button** (40px target; on click: "Listening… (works in Chrome or Edge over https)" caption + Web Speech API `en-IN`; transcript fills the input and auto-clicks Search after 300ms) and **"Search"** primary pill button (label "Search"). ≤700px: bar stacks vertically (full-width input, then full-width 48px button).

**Empty state (no query yet) — "Try searching" card** (bordered): Gemini head (sparkle 18 + "Try searching" 19px/500). Then:
- 3 sentence starters (rows with 18px photo icon, 14.5px): "I'm looking for a photo of…" · "A photo from a trip to…" · "I can't quite remember, but it was…" (display only — copy/paste intent).
- Chip groups computed from the actual library (`_build_tag_panel`), 12px uppercase group heads, tonal pill chips:
  - **People** (up to 6: "Person N" → person filter)
  - **Places** (up to 6: "Name · N" → classic search that place)
  - **Things** (up to 6: caption-noun "· N" → classic search)
  - **When** (up to 6: "Year · N" → classic search)

**Results state** (`_grouped_results`), top to bottom:
1. Head: "Results" 21px/500 + grey count "for “<query>” · N".
2. **People group** (rendered when ANY of: a person has **≥2** photos in results; the query text contains a person-label token; OR a person-intent query (friends|family|people|person|mom|dad|mother|father|brother|sister|kids|child|me|myself|with me|who|faces) with **≥1**): head "People" + "in these results" + **"See all"** (→ People tab); up to **4** circles (56px) with name + "**N in results**" (count = that person's photos inside this result set); click → person filter view.
3. **Places group:** head "Places" + "where these were taken"; up to 4 cards "**Name · N photos**" (N = library-wide count); click → place filter.
4. **Scenes group:** head "Scenes" + "moments these fit" + **"See all"**; up to 4 cards (16:10 hero + title + "N photos"); click → event filter.
5. **Photos group:** head "Photos" + "closest matches"; grid 3/4/5 cols of the **top 30** results; each photo has a **"This is it ✔"** tertiary button below → confirm dialog.
6. Action row: **"Search again"** tertiary (left, clears results) + **"Describe it instead ✨"** tertiary (right → guided, prefilled with the query, autostart).
7. **Nudge card** (bordered, shown when `_nudge_needed`: query contains hedge words ("i think|maybe|not sure|kind of|roughly|somewhere|vaguely|half-remember|can't remember|don't remember"), OR top cosine < 0.20, OR ≥2 reformulations with top < 0.26): Gemini head "Can't find the right one?" + "Guided search asks a few quick questions and narrows it down — built for half-memories." + **"Try guided search"** secondary button → guided autostart with query.

**Zero/low-confidence state** (top cosine < 0.22, unless "show anyway" chosen): "No exact matches" card: "Nothing close to “<q>”. Describe it in a sentence — guided search is built for half-memories." + **"Describe it instead ✨"** primary + **"Show closest photos anyway"** tertiary (forces the grouped results view).

**Classic search mechanics (the "control"):** CLIP cosine of query vs image embeddings + boosts: +0.04 per caption token hit (tokens ≥4 chars), +0.15 if a gazetteer place/alias is in the query, +0.25 for year match. Top 30 returned. The nudge gating above means easy one-shot searches never get pushed into the guided loop.

**Confirm dialog (classic free play):** bordered card "Is this the photo?" + "Your pick — say yes if it's right." + "caption · date" + photo; **No** (secondary) → toast "Not this one — keep browsing."; **Yes** (primary) → "Noted" card ("Noted — thanks for trying. In free play there's no single right answer." + the photo + **"Search something else"** button).

---

## 7. Gemini guided flow (tab: guided) — THE FEATURE

**Idle view:** Gemini head (sparkle 24 + "Gemini" 19px/500 + "guided search" 13px grey); sub "Find a photo you half-remember — describe it, and we ask quick questions to narrow it down." Then: **textarea** "Describe the photo" (90px tall, collapsed label, placeholder "a café in Goa, daytime, coffee before the beach…") + row: **"Find it"** primary (left) + **3 example chips** (tertiary pills, from examples.json, word-boundary-truncated to 28 chars + "…"). Chip click → prefills + autostarts.

**Entry points (all autostart the same engine):** guided tab "Find it"; example chips (home/ tab); "Try guided search" nudge; "Describe it instead ✨" (zero state / results action); desktop pill sparkle button; test-mode task start.

**Active session layout:**
- **Desktop:** split view — left 1/4 = conversation panel; right 3/4 = results side. (Mobile: stacked, conversation first.)
- **Conversation panel, top to bottom:**
  1. **User echo bubble:** "“<memory text, ≤200 chars>”" (grey bg `#f8f9fa`, 10px radius, 13.5px).
  2. **Parse badge:** tonal chip (sparkle + "Gemini understanding") if LLM parse, else grey chip "Basic understanding".
  3. **"What I understood — tap to correct"** (13px grey).
  4. **Cue chips** (one per parsed cue): pill `#f1f3f4` (negated: `#fce8e6` bg / `#a50e0e` text): 11px uppercase grey cue type + value + 11px "sure"/"unsure" state. Below each chip, a 3-button row (tertiary, small): **"not this" / "is this"** (toggles negation) · **"sure" / "unsure"** (toggles certainty) · **"✕"** (removes). Any edit re-scores immediately. (If no cues: "No cues detected — relying on visual similarity.")
  5. **Confirm dialog / anchor card / this-or-that card / question card** — rendered in this slot (priority order: confirm > anchor > pair > question).
  6. Bottom row: **"I'm stuck"** tertiary (forces fallback immediately) + **"Start over"** tertiary (clears the session).
- **Results side, top to bottom:**
  1. **Confidence strip:** 13px label ("Narrowed to N days · N photos" when a time window exists, else "N photos in the closest moments") + 4px progress bar (width 40–96%, blue).
  2. **Low-confidence hint** (when top moment score < 0.55): "Closest matches so far — the question below usually helps." (or without question: "…correct a cue, or press I'm stuck to browse.")
  3. **Moment cards** (up to 5): bordered card; 16:9 cover photo; label row "**Place · Jan 10–13, 2025 · Setting**" (15px/500, humanized date ranges) + "N photos" (12.5px grey); **why-matched** line 12px grey (e.g. "café ✓ · Goa ✓ · daytime ~" — ✓ = sure match, ~ = unsure match); action row: **"This is it ✔"** tertiary (left half) + **"Use as anchor"** tertiary (right half); **"Show all in this moment"** tertiary expands a 4-col grid (3 mobile) of the moment's photos, each with **"✔ This one"** tertiary.
- **This-or-that card** (after the first answered question, then every 2nd round): bordered; "Which is closer to your memory?"; two 16:10 images side by side (16px radius); 3 buttons: **"Left is closer"** / **"Right is closer"** (secondary) + **"Neither"** (tertiary). Chosen image → positive feedback into the query vector (α=1.0, β=0.6, γ=0.3), rejected → negative.
- **Question card:** bordered; "Quick question" 500 + question text; option buttons (secondary, full-width, ~44px) with **humanized labels** (raw enums never shown): Indoors/Outdoors/Unclear · Morning/Afternoon/Evening/Night · Café/Beach/Street/Campus/Classroom or study/Home or hostel/Restaurant/Temple or ruins/Nature or landscape/Transport/Office/Party or event/Shop or market/Document or receipt/Somewhere else · Summer/Monsoon/Winter · No one/Just one person/Two or three/A group · Yes, some writing/No writing · place names capitalized. **"I don't remember"** is always a tertiary text-style button (never an equal option). Questions are chosen by entropy × answerability prior × (0.5^dont_know-counts); at most **4 rounds**; attributes are never repeated.
  - **Smart face question** (when ≥2 people have ≥3 photos among the top candidates): "Was this with Person A or Person B?" with 30px face thumbnails; buttons **"With Person N"**; answering boosts that person's images ×1.3.
- **Anchor sub-flow:** "Use as anchor" → bordered card "Use **<date>** as an anchor?" + 4 secondary buttons: **"Same day"** (±12h) · **"Right after"** (+3 days) · **"Right before"** (−3 days) · **"Around that time"** (±14 days) → becomes a sure time window; re-runs scoring.
- **Fallback** (round ≥ 4 or "I'm stuck"): bordered card: "**I'd narrow it to <Mon D, YYYY> – <Mon D, YYYY>**" 16px/500 + "Browse by day, or start over." 13px; up to 6 day buttons "**Mon D · N photos**" (tertiary; expand to a 16-photo grid with "✔ This one"); **"Start over"** tertiary. Side effect: seeds the home "Still searching" card. **The search never dead-ends.**
- **Confirm dialog (guided):** "Is this the photo?" card as in classic, plus a third option: **"Close, but not it"** tertiary → narrows the time window to ±3 days around that photo + toast "Narrowed to 3 days around that photo." (no reset).
  - **No** → toast "Not this one — keep browsing, or use another photo as an anchor."
  - **Yes** → **success screen**.
- **Success screen:** bordered card: found photo (16px radius, max-height 420px); two tonal chips: "**Found it in Ns**" + "**N guided steps**"; (AI mode only) sparkle + "Understood with Gemini" 12.5px; row: **"Share"** primary (toast) + **"Search another"** (clears session → idle); then "Was this the right photo?" 14.5px/500 + **Yes**/**No** tertiary (logs `success_feedback`, then clears).
- **"Back to search"** tertiary at the very bottom of an active session (abandons the session, keeps the search tab state).

**Engine behavior behind the flow (for reasoning about results):** start = parse cues → score all 3,252 images (0.50 visual + 0.20 time + 0.20 place + 0.10 attributes; each cue × certainty multiplier; a matched NEGATED cue subtracts 0.5) → cluster top-40 into moments (new moment when time gap >8h or distance >10km; label "Place · date range · most-common setting"; top 5 by max score) → ask best question (if expected info gain ≥ 0.4 bits, top moment < 55% weight mass, round < 4) → this-or-that every 2nd round after first answer. Visual-only and full-score ranks for the 8 canonical tasks are documented in M6 test output (rules-only: 6/8 within top-40; Y1/Y2 fail by task design, documented honestly).

---

## 8. People tab (tab: people)

Head "People" 21px/500 + grey count (13). If onboarding not answered: onboarding card (same as home). Then a **4-column grid** (3 mobile / 5 @701 / 6 @1100) of ALL persons: 64px avatar + name ("You" if selected) + "N photos" 11px. Click → person filter on Photos home. Empty state (no face data): "Face groups appear here once the library is scanned."

---

## 9. Settings tab (tab: settings)

Two sections, switched via `settings_sec` (avatar menu entries deep-link):
- **"How this works":** 3 paragraphs — (a) "A research prototype inside a Google-Photos-style app. It studies how people find photos they only half-remember." (b) "**Guided search.** Describe the photo in a sentence. We show your closest matches right away, then ask a few quick questions only where the library is still ambiguous — you can skip or correct everything at each step." (c) "**Understanding.** <mode label> — your description is sent to Google's Gemini API (free tier)." (AI) / "— your text is processed offline; nothing is sent anywhere." (basic).
- **"About this demo":** "**Library.** N free-licensed photos (CC0 / CC BY / CC BY-SA — see ATTRIBUTION.md) with synthetic dates, places and people. No real personal data." · "**People.** Photos are grouped automatically by faces; the person you pick is labelled “You”." · "**Privacy.** <mode privacy note>".
- **"Reset"** secondary button (bottom, both sections): clears all jog/classic/guided/filter/you/search/demo state → Photos home.

---

## 10. Voice search (both surfaces)

- Mic button in the desktop pill (target "pill") and in the mobile/search-tab bar (target "search").
- On click: "Listening… (works in Chrome or Edge over https)" caption; `MIC_JS` polls for a `span.micreq`, launches `webkitSpeechRecognition` (`en-IN`, single result), writes the transcript into the target input via the native value setter + input event, then auto-clicks the "Search" button after 300ms. Silent failure if unsupported.

---

## 11. Test mode (`?test=1`) + admin (`?admin=1`) — CONTRACT-LOCKED

Minimal chrome (pinwheel + "Photos" top row; no bottom nav; footer note kept).

**Start screen:** bordered card "Join the study" + "2 practice + 8 tasks · about 30 minutes"; input **"Your participant code (e.g. P1)"** + **"Start session"** primary. Invalid code → red "Please enter a code like P1, P2 … P8." (P1–P20 accepted).

**Counterbalancing (deterministic):** for participant index i (P1→0): practice = P1 classic + P2 jog (always, first, not counted, 1:00 each); set X (X1–X4) and set Y (Y1–Y4) each get opposite modes — i even → X classic / Y jog, i odd → swapped; first set shown = X if (i//2) even else Y. Total 10 tasks.

**Task card phase:** bordered card: "Task <ID>" 16px/500; tags: blue "practice (not counted)" or "task N of 8" + grey "mode: CLASSIC/JOG"; the **fragment text** in a `#f8f9fa` 12px-radius box (15px, 1.55 leading); "3:00 · no feedback until the end." (practice: "1:00…"); **"Start task"** primary → timer starts.

**Running phase:** live countdown caption "⏱ M:SS left" (1s fragment). Timeout → red "Time's up — let's move on." + task ends as `timeout`.
- **Jog task:** "Your memory" card — textarea prefilled with the fragment (editable) + **"Find it"** primary → full guided UI (non-split, full width).
- **Classic task:** input "Search your photos" (placeholder "a café in Goa, daytime, coffee") + **"Search"** primary; results = 4-col grid, each photo with **"This is it ✔"**.
- Always available: **"I give up"** tertiary → ends as `give_up`.
- **Confirm:** "Is this the photo?" card + "Your pick — say yes if it's right." + caption · date + photo; **Yes** primary: correct → task ends `success`; wrong → toast "Hmm, keep looking." (2nd wrong → same; 3rd wrong → task ends `fail`). **No** → back to browsing.

**Post phase:** bordered "Task <ID> finished" + green outcome tag + "Ns · N queries"; two selectboxes side by side: **"How sure are you that you picked the right photo? (1–5)"** and **"How easy was this task? (1–7)"**; **"Continue"** primary.

**Complete:** "Session complete" card + green "Session complete — thank you!" + **"Download my session log"** (JSONL of this session's events). (Note: the M8 spec's 3 free-text boxes are NOT in the current build — only the download.)

**Admin (`?admin=1`):** "Admin" card + **"Download all events (events.jsonl)"** secondary → download button "Download events.jsonl"; caption "Admin view — normal visitors do not see this."

---

## 12. The label contract (do NOT change these strings without updating all tests)

"Find it" · "This is it ✔" · "✔ This one" · "Use as anchor" · "Same day" / "Right after" / "Right before" / "Around that time" · "Left is closer" / "Right is closer" / "Neither" · "Is this the photo?" · "Yes" / "No" · "Close, but not it" · "Found it in" · "I'd narrow it to" · "I'm stuck" · "Start over" · "Back to search" · "Search another" · "Search" · "Search again" · "Search something else" · "Show all in this moment" · "Show all" / "Show all N" · "Voice search" · "Listening… (works in Chrome or Edge over https)" · "not this" / "is this" · "sure" / "unsure" · "✕" · "This is me" · "Not sure" · "Which one is you?" · "Describe it instead ✨" · "Try guided search" · "Show closest photos anyway" · "No exact matches" · "Can't find the right one?" · "What I understood — tap to correct" · "Gemini understanding" / "Basic understanding" · "Quick question" · "I don't remember" · "Was this the right photo?" · "With Person N" · "Person N" · "You" · "See all" · "In results: N in results" · "Ask Gemini" · "Photos" / "Search" / "People" / "Settings" (nav) · "How this works" / "About this demo" / "Reset" · "Demo user" · "Dismiss demo note" · "DEMO" · "Memory" · "Start task" / "I give up" / "Continue" / "Start session" · "Download my session log" / "Download all events (events.jsonl)" / "Download events.jsonl" · "Join the study" · "Task N finished" · "Session complete" · "Time's up — let's move on." · "Hmm, keep looking." · "Noted — nice find." · "Noted — thanks for trying. In free play there's no single right answer." · "Share" / "Share link copied (demo)." · "Previous" / "Next" / "Close" · "Open photo from <date>" · "Open" (proactive card) · "We kept searching in the background" · "Narrowed to 3 days around that photo." · "Not this one — keep browsing, or use another photo as an anchor." · "Closest matches so far — …" · "No cues detected — relying on visual similarity." · "Type a search first." · "Please enter a code like P1, P2 … P8." · "Something went wrong in the demo. Please press Reset or reload." · "Admin view — normal visitors do not see this." · "Face groups appear here once the library is scanned." · Question option labels per §7 (Indoors…A group, Yes, some writing/No writing, place names).

---

## 13. Analytics / logging contract (JSONL, `space_jog/logs/events.jsonl`)

Fields per line: `ts` (ISO), `session_id` (uuid, per browser session), `participant_id`, `mode` (jog|classic|test|free), `task_id`, `event`, `payload`.
Events (names + payload keys are contract-locked): `session_start` (queue) · `live_status` (mode label) · `task_start` (limit_s, practice) · `dump_submitted` (memory text VERBATIM — participants are told at consent) · `cues_parsed` (count, parse_source ∈ cache|llm|rules) · `cue_edited` (count) · `moments_shown` (n, img_ids) · `results_shown` (classic: img_ids) · `question_shown` (attribute) · `question_answered` (attribute, value | "dont_know" | person label) · `pair_shown` (left, right) · `pair_choice` (choice) · `anchor_set` (relation, img_id) · `fallback_shown` (start, end) · `thumbnail_opened` · `confirm_attempt` (img_id, correct) · `task_end` (outcome ∈ success|fail|give_up|timeout, seconds, n_queries, n_rounds) · `post_task` (confidence, ease) · `success_feedback` (img_id, verdict).
Text length is logged for everything EXCEPT the jog memory dump and classic typed queries, which are logged verbatim.

---

## 14. User journeys (end-to-end)

**J1 — First launch, discover:** load → demo card → Memories carousel → People row with onboarding → "This is me" (or "Not sure") → browse month grid → tap a photo → lightbox (prev/next/share) → "This is it ✔" toast.
**J2 — Easy classic search:** type "goa" → Enter → grouped results (People/Places/Scenes/Photos) → tap a Places card → filtered month grid on home → browse → done. (No guided nudge for confident one-shots.)
**J3 — Half-memory guided search (the money journey):** type a hedged description (or tap nudge/chip/sparkle) → "Narrowing…" → echo + badge + cue chips → moments with why-matched → answer 1–3 quick questions (or "I don't remember") → this-or-that → optional anchor ("the evening after we walked the French quarter") → "This is it ✔" on a moment cover → "Is this the photo?" → Yes → success (time + steps + share + "Was this the right photo?").
**J4 — Failing gracefully:** keep answering "I don't remember" / "Neither" 4 rounds → fallback card "I'd narrow it to <range>" → browse day grids → "✔ This one" → confirm (Yes/No/"Close, but not it") — never an empty dead end. "I'm stuck" jumps straight there. "Start over" anywhere.
**J5 — Zero results:** gibberish/absent query → "No exact matches" → "Describe it instead ✨" (guided) or "Show closest photos anyway".
**J6 — People journey:** People tab or row → pick "You" on first run → every surface relabels → person filter → "With You" memory appears; smart face questions in guided flow ("Was this with Person A or Person B?" with thumbnails).
**J7 — Voice search:** mic → speak → transcript into box → auto-search.
**J8 — Test mode (researcher):** open `/?test=1` → enter code → 2 practice → 8 tasks (counterbalanced classic/jog) → per-task confirm rules + timeout + give-up → confidence/ease per task → download own log; researcher downloads all at `/?admin=1`.
**J9 — AI vs basic:** with Gemini key: parse badge "Gemini understanding", success line "Understood with Gemini", footer explains the API; without: everything identical but "Basic understanding" and offline footer. Any LLM failure falls back to rules silently.

---

## 15. Session-state keys (for anyone debugging)

`tab` · `pill_q`, `search_q`, `classic_q_free`, `classic_res_free_classic`, `classic_queries_free_classic`, `force_show_free`, `classic_success_free` · `jog_free` (JogSession), `jog_state_free` (moments/question/pair/fallback/top), `jog_text_free`, `jog_success_free` · `guided_prefill`, `guided_autostart`, `guided_q_g` · `confirm_img_{task}`, `confirm_task` · `anchor_img_{task}` · `moment_expanded_{task}_{i}`, `month_open_{key}`, `fbday_open_{task}_{day}` · `mem_filter`, `person_filter` · `you_person`, `you_skipped` · `demo_card_dismissed` · `lightbox` {ids, idx} · `mic_req`, `mic_target` · `still_searching` {q, img} · `year_open_{y}` · `settings_sec` · `nav_req` · `live_session` (LLM session) · test mode: `participant`, `test_queue`, `test_pos`, `test_phase` (card|running|post), `test_done`, `task_deadline_{tid}`, `task_running_{tid}`, `task_timeout_{tid}`, `task_wrong_{tid}`, `task_result_{tid}`, `task_queries_{tid}`, `pcode`.

---

## 16. Verification & current status (as of snapshot)

- **E2E:** `code/test_jog_e2e.py` (desktop 1440×1000 + mobile 390×844, fresh contexts, JS-error collection, screenshots → `figures/screens/`). Last full run: PASS 0 fails / 0 JS errors. Known weakness: the search-results screenshots can capture a post-rerun home state — the checks assert presence of "See all"/"This is it" which exist on home too, so a dropped search-submit can go unnoticed. Fix = wait for the "Results for" header after Enter (retry loop), as already done for mobile classic.
- **Legacy suites:** `code/test_jog_app.py` (+`--classic`), `code/test_jog_testmode.py`, `code/test_jog_people.py`, `code/repro_jog_widget.py` — written for the pre-redesign UI; they were FAILING at snapshot (stale labels "Skip for now"→"Not sure", "Search Google Photos" button→pill input, expander fallback→card, avatar-menu About/Reset). Updating them to current labels is the main thread's in-flight task.
- **Library state:** 3,252 non-deleted images fully chained (meta/emb/faces/sync/verify all PASS); 13 person clusters (49/45/38/32/29/28/23/22/15/10/10/9/7 photos); celebrity ground-truth mapping verified; `space_jog` synced (287 MB images).
- **Servers:** `:8502` Jog (the one to test), `:8501` Discovery Streamlit, static Discovery on `:8610` + live HF static space.
- **Open items (main thread):** legacy test updates; deterministic E2E search shots; fresh visual QA (People bucket counts after search — user requested "people bucket should show after clicking search"; verify the ≥2 threshold renders on real result sets); 90s demo recording (`code/record_demo.py` → `figures/demo_recording_90s.webm`); STATE.md/links.md/deck-notes updates; secret scan; Vercel deploy decision; 3 friends for `?test=1` (protocol: `research/mvp_user_test.md`).
- **Deck:** explicitly SKIPPED per user; notes accumulate in `deck/notes_for_deck.md` (honesty framing: n=182 episodes, gate agreement κ=.569/67.5% v1 prompt, validation = second-model audit not human, read-aloud interviews, synthetic library, "better than GP" = demo-level finding only).

## 17. Invariants (non-negotiable)

1. Test-mode log event names + payload keys unchanged. 2. Label contract unchanged unless tests are updated in lockstep. 3. No stack trace to the user; no secrets anywhere under `space_jog/`; no raw img_ids/enums in user-facing copy; all dynamic HTML values escaped (`esc()`). 4. Gemini = mode inside search, never a destination. 5. Every search must be able to end in a fallback (no dead ends). 6. Mobile-first 480px feel; buttons ≥44px tap targets on mobile. 7. `code/jog_engine/` and `space_jog/jog_engine/` stay byte-identical. 8. No CDNs at runtime — all assets local. 9. Honest labels: demo/synthetic everywhere. 10. Keep `requirements.txt` pinned to the .venv versions.
