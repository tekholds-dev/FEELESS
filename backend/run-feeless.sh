#!/usr/bin/env bash
# Starts the FEELESS backend services from backend/.venv (create it with:
#   uv venv .venv --python 3.12 && uv pip install --python .venv/bin/python -r requirements-feeless.txt)
set -euo pipefail
cd "$(dirname "$0")"
UV=.venv/bin/uvicorn
for svc in "reputation_service:app 5077" "candles_service:app 5099" "feecat_service:app 5088"; do
  set -- $svc
  pkill -f "uvicorn ${1}" 2>/dev/null || true
  nohup "$UV" "$1" --host 127.0.0.1 --port "$2" > "/tmp/feeless-${1%%:*}.log" 2>&1 &
  echo "started ${1%%:*} on :$2"
done

# Market + swap API (port 5001) — its own env (../.venv) built from requirements.txt; needs MongoDB running.
pkill -f "uvicorn server:app" 2>/dev/null || true
if [ -x ../.venv/bin/uvicorn ]; then
  nohup ../.venv/bin/uvicorn server:app --host 127.0.0.1 --port 5001 > /tmp/feeless-server.log 2>&1 &
  echo "started server on :5001"
fi
