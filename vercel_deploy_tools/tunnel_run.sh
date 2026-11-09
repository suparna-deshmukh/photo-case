#!/bin/zsh
while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting ssh tunnel" >> /tmp/tunnel_events.log
  ssh -o StrictHostKeyChecking=no -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -R 80:localhost:8601 nokey@localhost.run >> /tmp/tunnel_events.log 2>&1
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] ssh exited, reconnecting in 10s" >> /tmp/tunnel_events.log
  sleep 10
done
