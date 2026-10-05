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
  [[ -n "$pid" ]] && kill $pid 2>/dev/null || true
  # A process can give up its port and still be alive (its loops keep running) — an old keeper left like that traded every order
  # twice. Stop EVERY copy of this app by name and wait until none is left; force it after 10s.
  pkill -f "uvicorn $app" 2>/dev/null || true
  for _ in $(seq 1 20); do pgrep -f "uvicorn $app" >/dev/null 2>&1 || break; sleep 0.5; done
  pkill -9 -f "uvicorn $app" 2>/dev/null || true
  (cd "$dir" && nohup "$venv/bin/python" -m uvicorn "$app" --host 127.0.0.1 --port "$port" > "/tmp/feeless-$name.log" 2>&1 &)
  echo "started $name on :$port"
}

restart 5001 "$root/backend" "$root/.venv"          server:app             api
restart 5077 "$root/backend" "$root/backend/.venv"  reputation_service:app reputation
restart 5088 "$root/backend" "$root/backend/.venv"  feecat_service:app     feecat
restart 5099 "$root/backend" "$root/backend/.venv"  candles_service:app    candles

# Circle wallets sidecar (localhost:5111), only when it's installed and a Circle key is set.
if [[ -d "$root/circle/node_modules" ]] && grep -q '^CIRCLE_API_KEY=.' "$root/backend/.env" 2>/dev/null; then
  pid="$(lsof -tiTCP:5111 -sTCP:LISTEN 2>/dev/null || true)"
  [[ -n "$pid" ]] && kill $pid && sleep 1
  (cd "$root/circle" && nohup node server.mjs > /tmp/feeless-circle.log 2>&1 &)
  echo "started circle on :5111"
fi
