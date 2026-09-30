#!/usr/bin/env bash
# Keep this local copy in sync with GitHub while you work.
# Every 30s: fetch, fast-forward the current branch, and restart the backend if backend code changed.
# The frontend dev server (port 51367) hot-reloads Chrome on its own when files change.
#
#   bash scripts/auto-pull.sh            # follow the current branch
#   bash scripts/auto-pull.sh 60         # check every 60s instead
#
# Never overwrites your work: it skips a round while you have uncommitted changes
# and only ever fast-forwards (no merges, no resets).
set -uo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
interval="${1:-30}"
# Always follow main (the live site). A copy left on an old session branch would otherwise never update.
branch="${FEELESS_BRANCH:-main}"
current="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current" != "$branch" ]]; then
  git checkout -q -- frontend/yarn.lock frontend/package-lock.json 2>/dev/null || true
  if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
    echo "On $current with local edits, so NOT following $branch. Run: git stash && git checkout $branch"
  elif git fetch -q origin "$branch" && { git checkout -q "$branch" 2>/dev/null || git checkout -q -b "$branch" "origin/$branch"; }; then
    echo "Switched from $current to $branch"
  else
    echo "Could not switch to $branch; run: git checkout $branch"
  fi
fi
echo "Following origin/$branch every ${interval}s in $root (Ctrl+C to stop)"

while true; do
  if git fetch -q origin "$branch" 2>/dev/null; then
    local_rev="$(git rev-parse HEAD)"
    remote_rev="$(git rev-parse "origin/$branch")"
    # Nothing to pull when GitHub has nothing new (same commit, or this copy is already ahead).
    if [[ "$local_rev" != "$remote_rev" ]] && ! git merge-base --is-ancestor "origin/$branch" HEAD; then
      # yarn install rewrites lockfiles on its own: those are never real work, so put them back instead of stalling forever.
      git checkout -q -- frontend/yarn.lock frontend/package-lock.json 2>/dev/null || true
      dirty="$(git status --porcelain --untracked-files=no)"
      if [[ -n "$dirty" ]]; then
        echo "$(date +%T) new commits on origin/$branch, but these files have local edits, so skipping:"
        echo "$dirty" | sed 's/^/    /'
        echo "    keep them: git stash   ·   drop them: git checkout -- <file>"
      elif git merge-base --is-ancestor HEAD "origin/$branch"; then
        changed="$(git diff --name-only HEAD "origin/$branch")"
        git merge -q --ff-only "origin/$branch"
        echo "$(date +%T) updated to $(git log --oneline -1)"
        if grep -q '^backend/' <<<"$changed"; then
          echo "$(date +%T) backend changed, so restarting services"
          bash "$root/scripts/start-backend.sh" || echo "backend restart failed, see /tmp/feeless-*.log"
        fi
        if grep -qE '^frontend/(package.json|yarn.lock)$' <<<"$changed"; then
          echo "$(date +%T) frontend dependencies changed, so installing them"
          (cd "$root/frontend" && yarn install --prefer-offline) \
            && echo "$(date +%T) dependencies installed (the dev server picks them up; restart it if it still errors)" \
            || echo "$(date +%T) yarn install failed: run 'cd frontend && yarn install' by hand"
        fi
      else
        echo "$(date +%T) your branch and origin/$branch have diverged, so not pulling (resolve manually)"
      fi
    fi
  else
    echo "$(date +%T) fetch failed (offline?), retrying"
  fi
  sleep "$interval"
done
