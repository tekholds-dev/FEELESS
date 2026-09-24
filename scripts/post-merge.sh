#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"

# This project intentionally has no committed lockfile. Keep installs
# non-interactive and avoid generating a new lockfile during task merges.
yarn install --non-interactive --ignore-scripts --no-lockfile
yarn build

# Exercise the Feeless Cats collection in a real phone-sized browser before
# the merged preview is considered ready. Reuse the managed preview when one
# is already running; otherwise the check owns and cleans up a temporary one.
bash ../scripts/run-feeless-cats-mobile-check.sh