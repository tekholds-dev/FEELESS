#!/usr/bin/env bash
# FEELESS push gate: the three checks CLAUDE.md demands, judged on REAL exit codes
# (never `test | grep` — grep exits 0 on the word FAIL; that pushed red tests twice on 2026-10-08).
set -euo pipefail
cd "$(dirname "$0")/.."
out="${TMPDIR:-/tmp}/feeless-gate"; mkdir -p "$out"
step() { printf '\n▶ %s\n' "$1"; }

step "1/3 backend tests"
PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q > "$out/pytest.txt" 2>&1 || { tail -40 "$out/pytest.txt"; echo "✋ GATE RED: backend tests"; exit 1; }
tail -1 "$out/pytest.txt"

step "2/3 frontend tests"
( cd frontend && CI=true yarn test --watchAll=false > "$out/jest.txt" 2>&1 ) || { grep -E "FAIL|●|Tests:" "$out/jest.txt" | head -40; echo "✋ GATE RED: frontend tests"; exit 1; }
grep -E "^Tests:" "$out/jest.txt" || true

step "3/3 frontend build"
( cd frontend && CI=false npx craco build > "$out/build.txt" 2>&1 ) || { tail -40 "$out/build.txt"; echo "✋ GATE RED: build"; exit 1; }
if grep -rliE "command center|cmd ctr" frontend/build/static/js >/dev/null 2>&1; then echo "✋ GATE RED: HQ name leaked into the bundle"; exit 1; fi

echo; echo "✅ GATE GREEN — safe to push"
