# WORK QUEUE — user-authorized, 2026-10-06 (side conversation)
Execute AFTER Gate 0 completes. Order is dependency-ordered. Update STATE.md + deck/notes_for_deck.md as phases land.

## GATE 0 (current task, already running — do NOT start queue before this)
Celebrity resume (session 88895) → fetch_celebrities_deep.py for under-target persons →
tag_images --provider local --resume --workers 8 → build_meta (person_key column) →
embed_images → face_pipeline --resume (avatar-pick bug already fixed) → verify cluster purity vs
person_key → sync_space_jog (people.json + faces/ now auto-synced) → restart :8502 →
repro/M7/classic/testmode all PASS (tests already patch for onboarding dialog "Skip for now").

## INVARIANTS (every phase)
- Log event names + payload keys unchanged (analysis pipeline).
- Test-mode label contract unchanged (see STATE.md contracts); update Playwright tests in lockstep with any UI text change.
- No stack trace to user; no secrets in space_jog/; no raw img_id/enums in user-facing copy; html-escape all dynamic values.
- After each phase: repro 25/25 + M7 (jog+classic) + testmode + 0 JS errors; screenshots to figures/screens/.
- Keep space_jog deployable (requirements.txt pinned, .streamlit theme ships).

## PHASE 1 — Design system + chrome
1.1 Font: self-host Roboto Flex (variable, optical sizing; weights 400/500/600). Replace Roboto/Inter. Type scale 12/14/16/22/28, headings -0.01em. All assets local (no CDN at runtime).
1.2 CSS token set: primary #1a73e8, text #202124, secondary #5f6368, disabled #80868b, hairline #e8eaed, fill #f1f3f4, bg #f8f9fa, error #d93025, success #188038. 8pt spacing grid, 24px gutters, 1200px max width.
1.3 ONE icon system: Material Symbols Rounded, 24px, via single inline-SVG helper. Remove all CSS ::before data-URI icons.
1.4 Radii: cards 16px, buttons/chips full-pill, grid images 8px. Elevation: rest 0 1px 2px rgba(60,64,67,.10); hover 0 4px 10px rgba(60,64,67,.16) + translateY(-1px); ease cubic-bezier(.2,0,.27,1) 200ms.
1.5 Gemini: official 4-stop brand gradient on the sparkle; used ONLY in search pill, guided-flow header, mode badge.
1.6 Desktop app bar (64px, white, 1px bottom hairline): pinwheel + "Photos" (22px/500) left; search pill in the bar (max 720px, 48px, #f1f3f4, search icon left, mic + sparkle inside right); avatar 28px right → menu (About, How this works, Reset). Remove "Uploads", "Gemini", "About" as top-level nav items (Gemini = mode inside search, not a destination).
1.7 Mobile: top row pinwheel + "Photos" + search icon + settings; bottom nav 56px + safe-area-inset: Photos / Search / Gemini (center tonal pill) / People / Settings. Active state = icon inside #e8f0fe tonal pill (GP's real active style), inactive #5f6368, 24px icon / 12px label.
1.8 Black bar: white html/body bg inline in <head> pre-bundle; verify with top-clipped screenshots both viewports.

## PHASE 2 — Home (Photos tab)
2.1 Landing intro: compact dismissible card (12px "DEMO" chip + 1 line + collapse), first launch only. No hero copy.
2.2 Order = GP: Memories carousel → People row → month grid.
2.3 Memories cards: 16:9 full-bleed (216x150 desktop), dark bottom gradient scrim, white title + date, "Memory" chip. Bigger than current 118px thumbs — cinematic.
2.4 People row: 56-64px face circles, 2px white ring + shadow, name + "N photos", "See all →".
2.5 Onboarding "Which one is you?" → INLINE card inside People section (4 face options, "This is me" / "Not sure"). Not a modal. (Needs people.json — post Gate 0.)
2.6 Month grid: 14px #5f6368 month headers with hairline rule + count; 3 cols mobile / 4 tablet / 5 desktop / 6 @1440+; 8px gap; square object-fit cover; 200ms fade-in; lazy; aspect-ratio boxes (CLS 0).
2.7 LIGHTBOX (new): tap photo → full-screen viewer, dark scrim, image + caption + date, "This is it" + share, swipe prev/next. Biggest missing "real photo app" moment.

## PHASE 3 — Search (hero feature)
3.1 Pill: 56px, #f1f3f4, focus #1a73e8 border + soft shadow; mic (40px target) + sparkle inside right.
3.2 Focused-empty = Suggestions: 3 tappable sentence starters ("I'm looking for a photo of…"), then computed chip groups, 12px uppercase headers (PEOPLE / PLACES / THINGS / WHEN), tonal pill chips 14px.
3.3 GROUPED results (make-or-break): People (circles) → Places (pin+count cards) → Scenes (horizontal strip) → Photos grid; each group header + "See all". Never one flat grid.
3.4 Zero results = router moment: "No exact matches" + ONE primary button "Describe it instead ✨" → pre-fills guided flow with typed text.
3.5 ROUTER GATING (production rule): loop activates only on zero/low-confidence results, hedged language, or 2nd keyword-swap reformulation. Easy one-shot searches never enter the loop.

## PHASE 4 — Guided loop (Gemini mode)
4.1 DESKTOP: split view — 380px left conversation panel, live re-ranked grid on the right updating per answer (progressive results: results visible from step 0, every step skippable, degrades to normal search). Mobile: full-screen conversational sheet.
4.2 Conversation style: system lines 14px left + 16px sparkle; user answers right-aligned #d3e3fd bubbles; options = 44px full-width tonal rows + chevron; "I don't remember" = tertiary text button, never an equal option.
4.3 This-or-that: 16:9 pair, radius 16, segmented control (Left/Right/Neither); mobile left/right swipe gesture.
4.4 Moment cards: GP-memory style (cover + 3 overlapping corner thumbs + label + "N photos" + why-matched 12px: "café ✓ · Goa ✓ · daytime ~").
4.5 Confidence strip, top of panel: "Narrowed to 2 days · 14 photos" + thin progress bar.
4.6 Cue editor: chips with ✓/✗ states, not a data table.
4.7 Success screen: photo large, "Found in 48s · 3 steps", Share (primary), Find another (text), "Was this the right photo?" Yes/No (logged).
4.8 "Not this, but close" third confirm option (tightens window, no reset).

## PHASE 5 — Intelligence features (post Gate 0)
5.1 FACE-BASED QUESTIONS: when a person is a candidate discriminator, next question = "Was this with [Person N]?" with face thumbnails as options. (jog_engine/questions.py + person attribute.) Highest wow; GP has no equivalent.
5.2 CANDIDATE-COMPLETION CARDS: ambiguous cue → guess-and-confirm: "Did you mean the Goa trip (Jan 2023) or Gokarna (Jan 2025)?" Multiple-choice beats open questions (35.9% state no query).
5.3 FESTIVAL/WORLD-KNOWLEDGE DATE INFERENCE: "around Diwali" → event window (library has e03 Diwali, e12 Ganesh Chaturthi); "monsoon 2023" → Jun-Sep. Small holiday table in parser + LLM prompt.
5.4 ASK LESS: auto-fill cues from identity ("you" known), faces, festival inference, past queries, EXIF; skip questions the library already answers confidently. Target: median 2 interactions to found for 80% of tasks.
5.5 PROACTIVE "STILL SEARCHING" CARD (simulated is fine): failed/abandoned search becomes a background job; "We found the medicine photo you were looking for." Demo on home or About. Retention-engine narrative.
5.6 SHARE ON SUCCESS: on success screen, share action to friend who asked (discovered workaround loop). Simulated send is fine for demo.

## PHASE 6 — Motion, loading, polish
6.1 CLIP cold start: GP-style skeleton shimmer grid + "Loading N photos…" — never white page + spinner.
6.2 150-250ms view transitions; card hover lift; no white flashes.
6.3 Delete Uploads tab (empty-state nav item = loudest "not real" signal). Reset/About in avatar menu.
6.4 No st.expander in user views → cards.
6.5 Copy pass: locked label list, no lorem, no <>, no raw ids.
6.6 Focus rings 2px #1a73e8; keyboard nav for loop (arrows pick this-or-that).

## PHASE 7 — Ship + evidence (final)
7.1 PUBLIC URL (deliverable 3) — USER DECISION 2026-10-07: deploy to VERCEL once user is satisfied with the localhost version (replaces HF/PythonAnywhere/Cloud Run paths). Note: Vercel hosts static/Node — the Discovery Engine static site (space_discovery_static) deploys there directly; the Streamlit Jog MVP needs a Streamlit-capable host or a rebuilt static frontend — decide with user at that time. Keep localhost :8502 as the source of truth until then.
     7.1b (superseded, keep for reference): try free options first WITHOUT user action (PythonAnywhere free tier...).
7.2 90s screen recording of one full vague-memory search (Playwright video), save figures/.
7.3 PART 6: 3+ real users through ?test=1 (friends; 15 min each). Synthesize: success by round, time-to-find, recovery-after-fail, confidence/ease, gate diagnostics. Save research/mvp_user_test.md. FLAG TO USER (they schedule friends).
7.4 DECK (module K, last): 10 slides from deck/notes_for_deck.md + 1-slide discovery-workflow explainer. Every number from files; limitations slide (n=182, gate κ=.569, sim directional, synthetic library, read-aloud interviews); "better than GP" phrased as demo-level finding.
7.5 Validation polish (optional): 95% CI on 67.5% gate agreement; human-audit 40 TEST docs if any label looks off.
7.6 Final: links.md (LINK_mvp), STATE.md, keepalive if hosted, secret scan of both spaces.

## FLAG TO USER ON RETURN
(a) HF billing card OR PythonAnywhere account if 7.1 free path fails. (b) 3 friends for Part 6 (7.3). (c) Review screenshots + cached answers + deck.
