#!/usr/bin/env bash
set -euo pipefail
ROOT=/Users/apple/photo_case
D=$ROOT/vercel_deploy/api
for f in app.py gp_copy.py icons.py live_llm.py; do
  cp "$ROOT/space_jog/$f" "$D/$f"
done
for d in jog_engine assets data images static .streamlit; do
  rsync -a --delete --exclude '__pycache__' --exclude '*.pyc' "$ROOT/space_jog/$d/" "$D/$d/"
done
find "$D" -name '__pycache__' -type d -prune -exec rm -rf {} +
echo "resync done: $(date)"
