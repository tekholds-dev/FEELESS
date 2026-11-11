#!/usr/bin/env bash
# The owner's one command runs this (then `yarn start`). It starts every backend service (scripts/start-backend.sh) and the watcher
# (scripts/background.sh → keep-alive.sh) from HIS Terminal, so the services keep the Mac's LAN route. From then on nothing needs a restart:
# frontend edits hot-reload, and the watcher reloads changed backend code by itself once no build is running (log: /tmp/feeless-keepalive.log).
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
bash "$root/scripts/start-backend.sh"
bash "$root/scripts/background.sh" start
