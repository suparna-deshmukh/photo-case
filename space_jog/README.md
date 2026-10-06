---
title: Jog — guided photo retrieval
emoji: 🧭
colorFrom: blue
colorTo: yellow
sdk: streamlit
app_file: app.py
pinned: false
---

Jog is a research prototype styled like Google Photos: a demo of **AI-guided retrieval for photos you only half-remember**. The library is synthetic and public — ~3,000 free-licensed photos (CC0 / CC BY / CC BY-SA, credits in ATTRIBUTION.md) with generated dates, places, and recurring people, standing in for one person's photo history. No uploads; nothing personal is stored.

Search is the hero: type or dictate a vague memory (voice search in Chrome/Edge), browse a tag panel built from the actual library, or ask **Gemini-guided search** — it turns your half-memory into cues, asks quick clarifying questions, and narrows to likely moments. **People** groups recurring faces and lets you pick which one is you. **Memories** and the date view are computed from the library itself.

AI mode is optional: when enabled, your description is sent to Google's Gemini API (free tier) to parse it into search cues; without it, a built-in rule-based parser does the same work locally and nothing leaves your browser. Do not enter personal information..
