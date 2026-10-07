# CHANGELOG — space_jog (UI revamp)

## 2026-10-07 (layout/tile/search fix session, continued)
- Fixed fatal `NameError: _confirm_free` (leftover call after per-photo confirm moved to lightbox) that broke all classic searches after the results grid.
- Fixed `AttributeError: live_session` (never initialized) that broke every Ask search; now a plain `{"live_calls": 0}` dict, reset with the session.
- Fixed `NameError: SETTING_PRETTY` (missing module dict) that broke Ask result groups.
- Converted all six `st.dialog(key=...)` blocks to Streamlit 1.65 decorator form (`with st.dialog` does not exist in 1.65): lightbox, success, anchor sheet, avatar menu, About/How, test-mode confirm.
- Fixed duplicate element key `wr_15` (group header loop) → `wr15_{tk}_{gi}`.
- "Find it" button no longer disabled-locked while typing (Streamlit text widgets sync on blur); short text is guarded in `_start_ask`.
- Self-hosted fonts were corrupt (Chromium "invalid sfntVersion"); re-fetched valid variable woff2 (Google Sans Flex, Roboto Flex, latin) and simplified to one @font-face per family.
- Lightbox icon buttons: hover state now translucent white (white icons were invisible over the light hover background).
- Verified: full Ask journey (desktop 1440 + mobile 390), classic search, nudge banner, zero-results, collections, test mode P1 smoke, admin log download, 7-viewport home audit (photos load, horizontal scroll locked), leak lint clean (only visually-hidden icon-button labels remain in DOM).

## 2026-10-07 (previous session)
- photo_cell now uses st.image + transparent overlay button (fixed gray-box photos).
- Horizontal scroll locked at all widths; mobile st.columns fix with weighted _wrow rows.
- Data-grounded memory cards; measured "Things" suggestions.
