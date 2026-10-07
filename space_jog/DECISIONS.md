# DECISIONS — space_jog (one line each: decision, reason)

- Icon buttons keep their label as visually-hidden text (font-size:0) rather than aria-label, reason: st.button in Streamlit 1.65 has no aria_label parameter; visually-hidden text is a standard accessible-name pattern and is invisible to sighted users (leak lint matches it only in DOM text, not on screen).
- Lightbox title is static "Photo" instead of the photo's date, reason: st.dialog titles are static in decorator form (1.65); the date is still shown in the position line and Details.
- "Find it" is always enabled and guards on click, reason: text widget state only syncs on blur in this Streamlit build, so a disabled-state button could never be clicked immediately after typing.
- Dialog dismiss handlers only pop session state (no st.rerun), reason: dismissal already triggers a rerun; double rerun caused extra render cycles.
- Google Sans Flex / Roboto Flex served as single variable woff2 (latin subset) from Google Fonts API, reason: the previously committed static subsets were corrupt and rejected by Chromium.
