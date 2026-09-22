#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/../frontend"

# This project intentionally has no committed lockfile. Keep installs
# non-interactive and avoid generating a new lockfile during task merges.
yarn install --non-interactive --ignore-scripts --no-lockfile
yarn build