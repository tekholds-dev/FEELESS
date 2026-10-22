#!/usr/bin/env bash
# FEELESS push gate: the three checks CLAUDE.md demands, judged on REAL exit codes
# (never `test | grep` — grep exits 0 on the word FAIL; that pushed red tests twice on 2026-10-08).
set -euo pipefail
cd "$(dirname "$0")/.."
out="${TMPDIR:-/tmp}/feeless-gate"; mkdir -p "$out"
step() { printf '\n▶ %s\n' "$1"; }
# 🟢 Node ≥ 18 for the frontend (Blob / fetch globals the tests mock): an nvm default of 16 turned the gate red on 2026-10-22
node_ok() { "$1" -e 'process.exit(+process.versions.node.split(".")[0] >= 18 ? 0 : 1)' 2>/dev/null; }
if ! node_ok node; then
  for d in "$HOME"/.nvm/versions/node/v20*/bin "$HOME"/.nvm/versions/node/v22*/bin "$HOME"/.nvm/versions/node/v18*/bin /opt/homebrew/bin; do
    if [ -x "$d/node" ] && node_ok "$d/node"; then PATH="$d:$PATH"; export PATH; break; fi
  done
fi
echo "node $(node -v)"

step "1/3 backend tests"
PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q > "$out/pytest.txt" 2>&1 || { tail -40 "$out/pytest.txt"; echo "✋ GATE RED: backend tests"; exit 1; }
tail -1 "$out/pytest.txt"

step "2/3 frontend tests"
( cd frontend && CI=true yarn test --watchAll=false > "$out/jest.txt" 2>&1 ) || { grep -E "^FAIL |✕|^Tests:" "$out/jest.txt" | head -40;   # failures first — "● Console" noise used to fill all 40 lines and hide the real FAIL
 echo "✋ GATE RED: frontend tests"; exit 1; }
grep -E "^Tests:" "$out/jest.txt" || true

step "3/3 frontend build"
( cd frontend && CI=false npx craco build > "$out/build.txt" 2>&1 ) || { tail -40 "$out/build.txt"; echo "✋ GATE RED: build"; exit 1; }
if grep -rliE "command center|cmd ctr" frontend/build/static/js >/dev/null 2>&1; then echo "✋ GATE RED: HQ name leaked into the bundle"; exit 1; fi

echo; echo "✅ GATE GREEN — safe to push"
