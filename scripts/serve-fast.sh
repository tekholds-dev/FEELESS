#!/usr/bin/env bash
# ⚡ FAST MODE — run FEELESS from a production build instead of the dev server.
# The dev server (craco start, :51367) runs React in development: an unminified ~2.7 MB bundle, StrictMode mounting every
# poller twice, hot-reload code. This builds once, serves http://localhost:51368, and rebuilds by itself whenever a new
# commit lands (auto-pull.sh pulls it) — reload the page to get it. The dev server keeps running untouched.
#
#   bash scripts/serve-fast.sh          # build + serve on :51368, rebuild on new commits
#   FAST_PORT=51369 bash scripts/serve-fast.sh
#
# A new port is a new origin: connect the wallet / sign in to HQ once there.
set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"

build() {
  echo "$(date +%T) building…"
  if (cd frontend && CI=false GENERATE_SOURCEMAP=false npx craco build > /tmp/feeless-fast-build.log 2>&1); then
    echo "$(date +%T) ✅ build ready — reload the page"
  else
    echo "$(date +%T) ✋ build failed (old build still served): tail /tmp/feeless-fast-build.log"
  fi
}

[[ -f frontend/build/index.html ]] || build
node scripts/fast-server.js &
srv=$!
trap 'kill $srv 2>/dev/null' EXIT INT TERM

last="$(git rev-parse HEAD)"
while kill -0 "$srv" 2>/dev/null; do
  sleep 30
  now="$(git rev-parse HEAD)"
  if [[ "$now" != "$last" ]] && ! git diff --quiet "$last" "$now" -- frontend/src frontend/public frontend/package.json; then
    build
  fi
  last="$now"
done
