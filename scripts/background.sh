#!/usr/bin/env bash
# 🌙 FEELESS in the background on this Mac — no Terminal window needed.
#   bash scripts/background.sh start    every backend service + the keep-alive that restarts any that dies, detached from the
#                                       Terminal (close it, the services stay up) and the Mac is kept from idle-sleeping
#   bash scripts/background.sh status   which services answer, is the watcher running
#   bash scripts/background.sh stop     stop the watcher (services keep running until you stop them or reboot)
# Limits (it is still your Mac): closing the lid sleeps a MacBook unless it is plugged in with an external display, and a reboot
# stops everything — run `start` again after one. A real always-on host is docs/ALWAYS_ON.md (deploy/Dockerfile).
root="$(cd "$(dirname "$0")/.." && pwd)"
pidfile="/tmp/feeless-background.pid"
running() { [[ -f "$pidfile" ]] && kill -0 "$(cat "$pidfile")" 2>/dev/null; }
case "${1:-status}" in
  start)
    pkill -f "scripts/keep-alive.sh" 2>/dev/null; sleep 1
    nohup caffeinate -ims bash "$root/scripts/keep-alive.sh" >> /tmp/feeless-keepalive.log 2>&1 &
    echo $! > "$pidfile"; disown 2>/dev/null || true
    echo "started — watcher pid $(cat "$pidfile"). You can close this Terminal. Log: /tmp/feeless-keepalive.log" ;;
  stop)
    running && kill "$(cat "$pidfile")" 2>/dev/null; pkill -f "scripts/keep-alive.sh" 2>/dev/null; rm -f "$pidfile"
    echo "watcher stopped (services still running; scripts/start-backend.sh restarts them, a reboot stops them)" ;;
  status)
    running && echo "watcher: running (pid $(cat "$pidfile"), Mac kept awake)" || echo "watcher: NOT running — bash scripts/background.sh start"
    for spec in "5001 api" "5077 fuse+reputation" "5088 feecat" "5099 candles" "5111 circle-signer"; do
      set -- $spec; lsof -tiTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1 && echo "  ✓ $2 :$1" || echo "  ✗ $2 :$1 DOWN"
    done ;;
  *) echo "usage: bash scripts/background.sh start|status|stop" ;;
esac
