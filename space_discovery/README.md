---
title: Photo Retrieval Discovery Engine
emoji: 🔎
colorFrom: blue
colorTo: yellow
sdk: streamlit
app_file: app.py
pinned: false
---

Exploration of 5,000+ real public feedback documents (app-store reviews, app-store reviews, Reddit) about finding old photos in a major consumer photo app.

- Ask questions over structured "retrieval episodes" extracted from public feedback, or explore the evidence interactively.
- Paste a new feedback text and see a structured analysis (basic mode needs no AI; AI mode is optional).
- "Discover more" tab: search live public feedback (Play Store, App Store, Reddit) for any query and get a Gemini analysis (or a code-only reading with no AI).
- Every number is computed from the bundled data; every quote is a verified verbatim substring.
- AI mode (optional) sends your question or pasted text to Google's Gemini API for planning/answering; basic mode never leaves the demo.
- Do not paste personal information into this app.
