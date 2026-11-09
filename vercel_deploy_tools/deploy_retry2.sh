#!/bin/zsh
set -u
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
FULL=/Users/apple/photo_case/vercel_deploy_mine
REDIR=/Users/apple/photo_case/vercel_redirect
LOG=/tmp/deploy_retry2.log
echo "[$(date '+%Y-%m-%d %H:%M:%S')] retry loop started" >> $LOG
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] attempting redirect deploy" >> $LOG
  rout=$(cd $REDIR && vercel deploy --prod --yes 2>&1)
  echo "$rout" >> $LOG
  if echo "$rout" | grep -q "fair use"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] still fair-use blocked, sleeping 180s" >> $LOG
    sleep 180
    continue
  fi
  if echo "$rout" | grep -q "Production:"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] REDIRECT DEPLOY SUCCEEDED - shared URL live" >> $LOG
  else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] redirect deploy failed, sleeping 120s" >> $LOG
    sleep 120
    continue
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] attempting full-app deploy" >> $LOG
  out=$(cd $FULL && vercel deploy --prod --yes 2>&1)
  echo "$out" >> $LOG
  if [ $? -eq 0 ] && echo "$out" | grep -q "Production:"; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] FULL APP DEPLOY SUCCEEDED - done, exiting" >> $LOG
    exit 0
  fi
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] full deploy failed, will retry in 300s (redirect stays live)" >> $LOG
  sleep 300
done
