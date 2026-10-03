#!/usr/bin/env bash
# Always-on runner: every service in the background, the container stays up while any of them runs; a crashed service restarts.
set -uo pipefail
cd /app/backend
run() { while true; do python -m uvicorn "$1" --host 0.0.0.0 --port "$2"; echo "$1 exited — restarting in 3s"; sleep 3; done; }
run server:app 5001 & run reputation_service:app 5077 & run feecat_service:app 5088 & run candles_service:app 5099 &
if [[ -n "${CIRCLE_API_KEY:-}" ]]; then (cd /app/circle && while true; do node server.mjs; sleep 3; done) & fi
wait -n
