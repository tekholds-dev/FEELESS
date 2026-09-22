#!/usr/bin/env bash
set -euo pipefail

node scripts/preview-api.js &
api_pid=$!
cleanup() {
  kill "$api_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

cd frontend
HOST=0.0.0.0 PORT=5000 npm start