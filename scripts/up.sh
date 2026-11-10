#!/usr/bin/env bash
# ⚡ ONE COMMAND to run FEELESS's backend with local network access (G4, NEXA) and keep it in sync with GitHub.
# Run it from the macOS Terminal app (not from inside Claude: macOS blocks the local network for programs started there).
#
#   bash scripts/up.sh
#
# It stops every old auto-pull copy (wherever it was started), restarts all backend services from this window, then follows main
# here: a pushed backend change restarts them from THIS window too, so they keep the local network. Ctrl+C stops following.
set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
pkill -f "scripts/auto-pull.sh" 2>/dev/null && echo "stopped old auto-pull copies" || true
bash "$root/scripts/start-backend.sh"
exec bash "$root/scripts/auto-pull.sh"
