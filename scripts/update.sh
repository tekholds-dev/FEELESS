#!/usr/bin/env bash
# One command to get the Mac onto the latest FEELESS: bash scripts/update.sh   (run from anywhere inside the repo)
# Puts back yarn-rewritten lockfiles, parks any other local edits in a stash (never deletes them),
# switches to main, pulls, installs packages if they changed, restarts the backend.
set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"; cd "$root"
echo "FEELESS at $root · on $(git branch --show-current) · $(git log --oneline -1)"
git checkout -q -- frontend/yarn.lock frontend/package-lock.json 2>/dev/null || true
if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
  echo "Local edits found, saving them in a stash (get them back with: git stash pop):"
  git status --short --untracked-files=no | sed 's/^/    /'
  git stash push -q -m "auto-saved by update.sh $(date +%F-%T)"
fi
before="$(git rev-parse HEAD)"
git fetch -q origin main || { echo "Could not reach GitHub"; exit 1; }
git checkout -q main 2>/dev/null || git checkout -q -b main origin/main
git merge -q --ff-only origin/main || { echo "main has local commits that GitHub doesn't: run 'git reset --keep origin/main' if you don't need them"; exit 1; }
echo "Now on $(git log --oneline -1)"
if ! git diff --quiet "$before" HEAD -- frontend/package.json 2>/dev/null; then (cd frontend && yarn install --prefer-offline); fi
bash scripts/start-backend.sh
echo "Done. Hard-refresh Chrome (Cmd+Shift+R). The footer should show build $(git rev-parse --short HEAD)."
