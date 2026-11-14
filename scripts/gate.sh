#!/usr/bin/env bash
# FEELESS push gate: the three checks CLAUDE.md demands, judged on REAL exit codes
# (never `test | grep` — grep exits 0 on the word FAIL; that pushed red tests twice on 2026-10-08).
set -euo pipefail
cd "$(dirname "$0")/.."
out="${TMPDIR:-/tmp}/feeless-gate"; mkdir -p "$out"
step() { printf '\n▶ %s\n' "$1"; }
# 🟢 Node ≥ 20: serialize-javascript in the current build uses global crypto.getRandomValues.
node_ok() { "$1" -e 'process.exit(+process.versions.node.split(".")[0] >= 20 ? 0 : 1)' 2>/dev/null; }
if ! node_ok node; then
  for d in "$HOME"/.nvm/versions/node/v20*/bin "$HOME"/.nvm/versions/node/v22*/bin "$HOME"/.nvm/versions/node/v18*/bin /opt/homebrew/bin; do
    if [ -x "$d/node" ] && node_ok "$d/node"; then PATH="$d:$PATH"; export PATH; break; fi
  done
fi
echo "node $(node -v)"

# ⚡ only what the push touches (owner 2026-10-30: "the slow pushes"): docs-only → nothing to run; backend-only → no jest / build.
# Frontend changes still run the backend suite (test_no_geckoterminal & co. scan frontend files). GATE_ALL=1 forces all three.
unset $(git rev-parse --local-env-vars)   # a pre-push hook sets GIT_DIR: a test running `git init` in its own folder would then rewrite THIS repo (set core.bare=true, 2026-11-06)
# ⚡ owner 2026-11-14 "I want you to be able to push easily": a CLEAN commit that went green is written down, so the pre-push hook lets that
# exact commit through without running the whole gate a second time (any other commit, or a dirty tree, still runs it).
green() { echo; echo "✅ GATE GREEN — safe to push"; if git diff --quiet HEAD 2>/dev/null; then git rev-parse HEAD >> "$(git rev-parse --git-common-dir)/feeless-green"; fi; exit 0; }
base="$(git merge-base HEAD origin/main 2>/dev/null || git rev-parse HEAD~1)"
changed="$( { git diff --name-only "$base"; git diff --name-only; } | sort -u)"
front=0; back=0
if [ "${GATE_ALL:-0}" = 1 ] || grep -qE '^frontend/' <<<"$changed"; then front=1; back=1; fi
if grep -qE '^(backend/|scripts/|requirements|\.venv)' <<<"$changed"; then back=1; fi
if [ "$front$back" = 00 ]; then echo "docs / config only — nothing to test"; green; fi

step "1/3 backend tests"
if [ "$back" = 1 ]; then
# 4 workers, one file per worker (conftest sandboxes per test; files keep their own order) — 2,373 tests in ~1.7 min under load
( cd backend && for m in feecat_service reputation_service; do .venv/bin/python -c "import $m" || { echo "✋ GATE RED: $m does not start in its own Python"; exit 1; }; done ) || exit 1
if ! PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q -n 4 --dist loadfile -p no:cacheprovider > "$out/pytest.txt" 2>&1; then
  # 🔁 load flakes (2026-11-10: timing tests failed at load 10-59, then passed alone, blocking 5 pushes in one day): re-run ONLY the failed
  # tests, one at a time with nothing beside them. Still failing = a real break = red. Passing = named here, so a real pattern is never hidden.
  failed="$(grep -E '^FAILED ' "$out/pytest.txt" | sed -E 's/^FAILED ([^ ]+).*/\1/' | sort -u)"
  if [ -z "$failed" ] || [ "$(wc -l <<<"$failed")" -gt 12 ]; then tail -40 "$out/pytest.txt"; echo "✋ GATE RED: backend tests"; exit 1; fi
  echo "↻ re-running $(wc -l <<<"$failed" | tr -d ' ') failed test(s) alone:"; echo "$failed" | sed 's/^/   /'
  # shellcheck disable=SC2086
  PYTHONPATH=backend:. .venv/bin/python -m pytest $failed -q -p no:cacheprovider > "$out/pytest-rerun.txt" 2>&1 || { tail -40 "$out/pytest-rerun.txt"; echo "✋ GATE RED: backend tests (failed again alone)"; exit 1; }
  echo "   passed alone: load flake, not a break"; tail -1 "$out/pytest-rerun.txt"
fi
tail -1 "$out/pytest.txt"
else echo "no backend changes — skipped"; fi

step "2/3 frontend tests"
if [ "$front" = 0 ]; then echo "no frontend changes — tests + build skipped"; green; fi
# ≤ 4 jest workers: with the dev servers up, 7 workers starved the heavy suites into timeouts (FuseMore / SwapWorkspace / FusePage flaked, 2026-10-22)
( cd frontend && npx eslint -c eslint.undef.config.cjs --no-warn-ignored --no-inline-config "src/**/*.{js,jsx}" ) || { echo "✋ GATE RED: a name nobody defined would crash a page"; exit 1; }
( cd frontend && CI=true yarn test --watchAll=false --maxWorkers=4 > "$out/jest.txt" 2>&1 ) || { grep -E "^FAIL |✕|^Tests:" "$out/jest.txt" | head -40;   # failures first — "● Console" noise used to fill all 40 lines and hide the real FAIL
 echo "✋ GATE RED: frontend tests"; exit 1; }
grep -E "^Tests:" "$out/jest.txt" || true

step "3/3 frontend build"
( cd frontend && CI=false npx craco build > "$out/build.txt" 2>&1 ) || { tail -40 "$out/build.txt"; echo "✋ GATE RED: build"; exit 1; }
if grep -rliE "command center|cmd ctr" frontend/build/static/js >/dev/null 2>&1; then echo "✋ GATE RED: HQ name leaked into the bundle"; exit 1; fi

green
