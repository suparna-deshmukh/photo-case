#!/bin/bash
# Purpose: install every locked-context library into BASE/.venv (idempotent, resumable by re-run).
# Inputs: BASE layout exists; network access.
# Outputs: logs/install.log content, populated .venv, chromium for playwright, per-library import+version report.
set -uo pipefail
BASE="/Users/apple/photo_case"
cd "$BASE"
PY="$BASE/.venv/bin/python"
PIP="$BASE/.venv/bin/pip"
echo "== $(date '+%F %T') install start =="
"$PY" -m pip install --upgrade pip
"$PIP" install pandas pyarrow numpy pydantic openai requests tqdm scikit-learn sentence-transformers altair matplotlib google-play-scraper rapidfuzz langdetect statsmodels Pillow imagehash streamlit python-pptx pypdf pymupdf python-dotenv huggingface_hub playwright
echo "== $(date '+%F %T') playwright chromium =="
"$BASE/.venv/bin/playwright" install chromium
echo "== $(date '+%F %T') import check =="
"$PY" - << 'PYEOF'
import importlib
mods = ["pandas","pyarrow","numpy","pydantic","openai","requests","tqdm","sklearn","sentence_transformers","altair","matplotlib","google_play_scraper","rapidfuzz","langdetect","statsmodels","PIL","imagehash","streamlit","pptx","pypdf","pymupdf","dotenv","huggingface_hub","playwright"]
for m in mods:
    try:
        mod = importlib.import_module(m)
        print(f"OK  {m} {getattr(mod,'__version__','?')}")
    except Exception as e:
        print(f"FAIL {m} {type(e).__name__}: {str(e)[:120]}")
PYEOF
echo "== $(date '+%F %T') install done =="
