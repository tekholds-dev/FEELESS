#!/usr/bin/env bash
set -euo pipefail

api_port="${API_PORT:-5001}"
node scripts/preview-api.js &
api_pid=$!

cleanup() {
  local exit_code=$?
  if kill -0 "$api_pid" 2>/dev/null; then
    kill "$api_pid" 2>/dev/null || true
    wait "$api_pid" 2>/dev/null || true
  fi
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

# Do not let the frontend report port 5000 ready while its required local API
# proxy target is still starting (or has already failed).
for _ in {1..60}; do
  if ! kill -0 "$api_pid" 2>/dev/null; then
    echo "Preview API exited before becoming ready." >&2
    wait "$api_pid" 2>/dev/null || true
    exit 1
  fi
  if curl --silent --show-error --fail --max-time 1 "http://127.0.0.1:${api_port}/api/" >/dev/null; then
    break
  fi
  sleep 0.25
done

if ! curl --silent --show-error --fail --max-time 1 "http://127.0.0.1:${api_port}/api/" >/dev/null; then
  echo "Preview API did not become ready on port ${api_port}." >&2
  exit 1
fi

cd frontend
HOST=0.0.0.0 PORT=5000 npm start
