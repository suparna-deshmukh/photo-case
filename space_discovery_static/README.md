---
title: Photo Retrieval Discovery Engine
emoji: "🔎"
colorFrom: blue
colorTo: yellow
sdk: static
app_file: index.html
pinned: false
---

Photo Retrieval Discovery Engine — offline research demo. 182 retrieval episodes extracted from 8,383 public Google Photos feedback documents (play store, app store, reddit), screened and structured by an open model run on a personal computer.

All analysis runs in your browser from bundled data: preset evidence answers, an episode explorer, a vague-memory "try it" estimator (TF-IDF nearest episodes, no AI), and an opportunity scorecard with live weight sliders. Validation: model-vs-human agreement on a held-out sample (n=40) — failure_gate 67.5%, is_retrieval 97.5%, photo_type 100%, outcome 80.0%.

This static build has no server-side AI and sends nothing anywhere. No personal information needed; do not paste personal information into the demo fields.
