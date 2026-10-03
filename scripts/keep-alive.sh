#!/usr/bin/env bash
# 🫀 Keeps every FEELESS backend service up while Fuse runs: checks each port every 20s, restarts ONLY the one that's down.
# Run: nohup bash scripts/keep-alive.sh > /tmp/feeless-keepalive.log 2>&1 &     Stop: pkill -f keep-alive.sh
root="$(cd "$(dirname "$0")/.." && pwd)"
up() { curl -s -m 10 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$1$2" | grep -qE '^[1-4]'; }
start() {
  local port="$1" venv="$2" app="$3" name="$4"
  pid="$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"; [[ -n "$pid" ]] && kill $pid && sleep 1
  (cd "$root/backend" && nohup "$venv/bin/python" -m uvicorn "$app" --host 127.0.0.1 --port "$port" >> "/tmp/feeless-$name.log" 2>&1 &)
  echo "$(date '+%F %T') restarted $name :$port"
}
while true; do
  up 5001 /api/health            || { sleep 5; up 5001 /api/health || start 5001 "$root/.venv" server:app api; }
  up 5077 /api/reputation/fuses/prime || { sleep 5; up 5077 /api/reputation/fuses/prime || start 5077 "$root/backend/.venv" reputation_service:app reputation; }
  up 5088 /docs                  || { sleep 5; up 5088 /docs || start 5088 "$root/backend/.venv" feecat_service:app feecat; }
  up 5099 /docs                  || { sleep 5; up 5099 /docs || start 5099 "$root/backend/.venv" candles_service:app candles; }
  if [[ -d "$root/circle/node_modules" ]] && ! lsof -tiTCP:5111 -sTCP:LISTEN >/dev/null 2>&1; then
    (cd "$root/circle" && nohup node server.mjs >> /tmp/feeless-circle.log 2>&1 &); echo "$(date '+%F %T') restarted circle :5111"
  fi
  sleep 20
done
