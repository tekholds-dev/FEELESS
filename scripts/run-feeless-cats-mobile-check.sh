#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/feeless-cats-mobile.XXXXXX")"
PREVIEW_PID=""
STARTED_PREVIEW=0
CHECK_PREVIEW_PORT="${CHECK_PREVIEW_PORT:-5003}"
CHECK_API_PORT="${CHECK_API_PORT:-5004}"
PREVIEW_URL="${PREVIEW_URL:-http://127.0.0.1:${CHECK_PREVIEW_PORT}}"

cleanup() {
  local exit_code=$?
  set +e
  if [[ "$STARTED_PREVIEW" == "1" && -n "$PREVIEW_PID" ]] && kill -0 "$PREVIEW_PID" 2>/dev/null; then
    kill -TERM "$PREVIEW_PID" 2>/dev/null || true
    wait "$PREVIEW_PID" 2>/dev/null || true
  fi
  rm -rf "$WORK_DIR"
  exit "$exit_code"
}
trap cleanup EXIT INT TERM

wait_for_preview() {
  for _ in {1..120}; do
    if curl --silent --show-error --fail --max-time 1 "${PREVIEW_URL}/" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "Preview did not become ready on port 5000." >&2
  if [[ -f "$WORK_DIR/preview.log" ]]; then
    tail -n 80 "$WORK_DIR/preview.log" >&2
  fi
  return 1
}

if ! curl --silent --show-error --fail --max-time 1 "${PREVIEW_URL}/" >/dev/null 2>&1; then
  (
    cd "$ROOT_DIR"
    API_PORT="$CHECK_API_PORT" PREVIEW_PORT="$CHECK_PREVIEW_PORT" bash scripts/start-preview.sh
  ) >"$WORK_DIR/preview.log" 2>&1 &
  PREVIEW_PID=$!
  STARTED_PREVIEW=1
  wait_for_preview
fi

cd "$ROOT_DIR"
PREVIEW_URL="$PREVIEW_URL" python3 scripts/feeless-cats-mobile-check.py