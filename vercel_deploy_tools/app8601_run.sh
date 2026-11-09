#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting 8601 app" >> /tmp/app8601_events.log
  cd /Users/apple/photo_case/vercel_deploy_mine/api || exit 1
  exec env HF_HOME=/var/tmp/hf_cache PYTHONPATH=/Users/apple/photo_case/.venv/lib/python3.13/site-packages /Users/apple/photo_case/.venv/bin/python -u -m jog_child run app.py --global.developmentMode false --server.headless true --server.address 0.0.0.0 --server.port 8601 --browser.gatherUsageStats false >> /tmp/app8601.log 2>&1
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] 8601 app exited (code $?), restarting in 10s" >> /tmp/app8601_events.log
  sleep 10
done
