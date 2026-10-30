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

# ⚡ only what the push touches (owner 2026-10-30: "the slow pushes"): docs-only → nothing to run; backend-only → no jest / build.
# Frontend changes still run the backend suite (test_no_geckoterminal & co. scan frontend files). GATE_ALL=1 forces all three.
base="$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD~1)"
changed="$( { git diff --name-only "$base"; git diff --name-only; } | sort -u)"
front=0; back=0
if [ "${GATE_ALL:-0}" = 1 ] || grep -qE '^frontend/' <<<"$changed"; then front=1; back=1; fi
if grep -qE '^(backend/|scripts/|requirements|\.venv)' <<<"$changed"; then back=1; fi
if [ "$front$back" = 00 ]; then echo "docs / config only — nothing to test"; echo; echo "✅ GATE GREEN — safe to push"; exit 0; fi

step "1/3 backend tests"
if [ "$back" = 1 ]; then
# 4 workers, one file per worker (conftest sandboxes per test; files keep their own order) — 2,373 tests in ~1.7 min under load
PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q -n 4 --dist loadfile -p no:cacheprovider > "$out/pytest.txt" 2>&1 || { tail -40 "$out/pytest.txt"; echo "✋ GATE RED: backend tests"; exit 1; }
tail -1 "$out/pytest.txt"
else echo "no backend changes — skipped"; fi

step "2/3 frontend tests"
if [ "$front" = 0 ]; then echo "no frontend changes — tests + build skipped"; echo; echo "✅ GATE GREEN — safe to push"; exit 0; fi
# ≤ 4 jest workers: with the dev servers up, 7 workers starved the heavy suites into timeouts (FuseMore / SwapWorkspace / FusePage flaked, 2026-10-22)
( cd frontend && CI=true yarn test --watchAll=false --maxWorkers=4 > "$out/jest.txt" 2>&1 ) || { grep -E "^FAIL |✕|^Tests:" "$out/jest.txt" | head -40;   # failures first — "● Console" noise used to fill all 40 lines and hide the real FAIL
 echo "✋ GATE RED: frontend tests"; exit 1; }
grep -E "^Tests:" "$out/jest.txt" || true

step "3/3 frontend build"
( cd frontend && CI=false npx craco build > "$out/build.txt" 2>&1 ) || { tail -40 "$out/build.txt"; echo "✋ GATE RED: build"; exit 1; }
if grep -rliE "command center|cmd ctr" frontend/build/static/js >/dev/null 2>&1; then echo "✋ GATE RED: HQ name leaked into the bundle"; exit 1; fi

echo; echo "✅ GATE GREEN — safe to push"
