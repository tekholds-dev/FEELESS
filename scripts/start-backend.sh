#!/usr/bin/env bash
# Start (or restart) every FEELESS backend service with the Python environment it needs.
#   main API (5001)          → .venv            (repo root)
#   reputation (5077), FeeCat (5088), candles (5099) → backend/.venv   (has base58/nacl for wallet signatures)
# Logs go to /tmp/feeless-<service>.log
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"

restart() {
  local port="$1" dir="$2" venv="$3" app="$4" name="$5"
  local pid
  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$pid" ]] && kill $pid && sleep 1
  (cd "$dir" && nohup "$venv/bin/python" -m uvicorn "$app" --host 127.0.0.1 --port "$port" > "/tmp/feeless-$name.log" 2>&1 &)
  echo "started $name on :$port"
}

restart 5001 "$root/backend" "$root/.venv"          server:app             api
restart 5077 "$root/backend" "$root/backend/.venv"  reputation_service:app reputation
restart 5088 "$root/backend" "$root/backend/.venv"  feecat_service:app     feecat
restart 5099 "$root/backend" "$root/backend/.venv"  candles_service:app    candles
