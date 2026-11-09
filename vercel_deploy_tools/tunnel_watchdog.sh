#!/bin/zsh
# Keep the localhost.run ssh tunnel alive; log new URLs on (re)connect.
set -u
LOG=/tmp/tunnel_watchdog.log
SSH_PID_FILE=/tmp/lhr_ssh_pid
while true; do
  if ! kill -0 $(cat $SSH_PID_FILE 2>/dev/null) 2>/dev/null; then
    echo "[$(date '+%H:%M:%S')] tunnel ssh dead, restarting" >> $LOG
    : > /tmp/lt2.log
    nohup ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 80:localhost:8601 nokey@localhost.run >> /tmp/lt2.log 2>&1 &
    echo $! > $SSH_PID_FILE
    sleep 20
    url=$(grep -oE 'https://[a-z0-9]+\.lhr\.life' /tmp/lt2.log | head -1)
    echo "[$(date '+%H:%M:%S')] new tunnel URL: $url" | tee -a /tmp/tunnel_urls.log >> $LOG
  fi
  sleep 30
done
