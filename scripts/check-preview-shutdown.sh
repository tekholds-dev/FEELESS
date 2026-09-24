#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/preview-shutdown.XXXXXX")"
PREVIEW_PORT="${PREVIEW_PORT:-}"
API_PORT="${API_PORT:-}"
launcher_pid=""
api_pid=""
launcher_log=""

free_port() {
  node -e "const net = require('net'); const server = net.createServer(); server.listen(0, '127.0.0.1', () => { console.log(server.address().port); server.close(); });"
}

if [[ -z "$PREVIEW_PORT" ]]; then
  PREVIEW_PORT="$(free_port)"
fi
if [[ -z "$API_PORT" ]]; then
  API_PORT="$(free_port)"
  while [[ "$API_PORT" == "$PREVIEW_PORT" ]]; do API_PORT="$(free_port)"; done
fi
export PREVIEW_PORT API_PORT

cleanup() {
  local pid
  set +e

  if [[ -n "$launcher_pid" ]] && kill -0 "$launcher_pid" 2>/dev/null; then
    kill -TERM "$launcher_pid" 2>/dev/null || true
  fi
  if [[ -n "$api_pid" ]] && kill -0 "$api_pid" 2>/dev/null; then
    kill -TERM "$api_pid" 2>/dev/null || true
  fi

  # If a failed check left the frontend in the foreground, clean up only the
  # listeners this check started so the next preview can still run.
  for pid in $(port_pids "$PREVIEW_PORT") $(port_pids "$API_PORT"); do
    [[ -n "$pid" ]] && kill -TERM "$pid" 2>/dev/null || true
  done

  for pid in "$launcher_pid" "$api_pid"; do
    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
      kill -KILL "$pid" 2>/dev/null || true
    fi
  done

  wait "$launcher_pid" 2>/dev/null || true
  wait "$api_pid" 2>/dev/null || true
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

port_pids() {
  lsof -nP -t -iTCP:"$1" -sTCP:LISTEN 2>/dev/null | sort -u || true
}

fail() {
  echo "Preview shutdown check failed: $*" >&2
  if [[ -n "$launcher_log" && -f "$launcher_log" ]]; then
    echo "--- launcher output ---" >&2
    tail -n 80 "$launcher_log" >&2 || true
    echo "--- end launcher output ---" >&2
  fi
  exit 1
}

assert_port_free() {
  local port="$1"
  local pids
  pids="$(port_pids "$port")"
  [[ -z "$pids" ]] || fail "port ${port} is already occupied by PID(s): ${pids//$'\n'/, }"
}

wait_for_http() {
  local url="$1"
  local description="$2"
  for _ in {1..240}; do
    if curl --silent --show-error --fail --max-time 1 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  fail "${description} did not become ready"
}

wait_for_exit() {
  local pid="$1"
  local description="$2"
  for _ in {1..120}; do
    if ! kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    sleep 0.25
  done
  fail "${description} (PID ${pid}) did not exit after SIGTERM"
}

start_launcher() {
  local label="$1"
  launcher_log="$WORK_DIR/${label}.log"
  (
    cd "$ROOT_DIR"
    bash scripts/start-preview.sh
  ) >"$launcher_log" 2>&1 &
  launcher_pid=$!

  wait_for_http "http://127.0.0.1:${API_PORT}/api/" "preview API"
  wait_for_http "http://127.0.0.1:${PREVIEW_PORT}/" "frontend preview"

  api_pid="$(port_pids "$API_PORT" | head -n 1)"
  [[ -n "$api_pid" ]] || fail "preview API is responding but no process owns port ${API_PORT}"

  local api_parent
  api_parent="$(ps -o ppid= -p "$api_pid" | tr -d ' ')"
  [[ "$api_parent" == "$launcher_pid" ]] || fail \
    "preview API PID ${api_pid} is not owned by launcher PID ${launcher_pid} (parent: ${api_parent:-unknown})"
}

echo "Starting managed preview launcher..."
assert_port_free "$PREVIEW_PORT"
assert_port_free "$API_PORT"
start_launcher first

echo "Stopping managed preview launcher (PID ${launcher_pid}); checking API child cleanup (PID ${api_pid})..."
kill -TERM "$launcher_pid" 2>/dev/null || fail "could not signal launcher PID ${launcher_pid}"
wait_for_exit "$api_pid" "preview API child"
wait_for_exit "$launcher_pid" "preview launcher"

assert_port_free "$PREVIEW_PORT"
assert_port_free "$API_PORT"
echo "Managed stop released ports ${PREVIEW_PORT} and ${API_PORT}."

launcher_pid=""
api_pid=""
echo "Starting the preview again to confirm immediate port reuse..."
start_launcher second
echo "Preview restarted successfully on ports ${PREVIEW_PORT} and ${API_PORT}."