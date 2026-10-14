#!/usr/bin/env bash
# 🫀 Keeps every FEELESS backend service up while Fuse runs: checks each port every 20s, restarts ONLY the one that's down.
# Run: nohup bash scripts/keep-alive.sh > /tmp/feeless-keepalive.log 2>&1 &     Stop: pkill -f keep-alive.sh
root="$(cd "$(dirname "$0")/.." && pwd)"
up() { curl -s -m 20 -o /dev/null -w '%{http_code}' "http://127.0.0.1:$1$2" | grep -qE '^[1-4]'; }
# a service started < GRACE seconds ago is not judged yet (cold caches made the first answers slow and the old 10s probe killed it again)
GRACE=120
fresh() { local v="born_$1"; [[ -n "${!v:-}" ]] && (( $(date +%s) - ${!v} < GRACE )); }   # bash 3.2 (macOS): no associative arrays
start() {
  local port="$1" venv="$2" app="$3" name="$4"
  # Stop EVERY copy BY NAME and wait (start-backend.sh's rule): a copy told to stop keeps running while a live stream (HQ › Agents) is
  # open — it gave up its port, kept its loops and sat beside the new copy for 3+ min (2026-10-12; the keeper lock stopped a double trade).
  pkill -f "uvicorn $app" 2>/dev/null
  for _ in $(seq 1 30); do pgrep -f "uvicorn $app" >/dev/null 2>&1 || break; sleep 0.5; done
  pkill -9 -f "uvicorn $app" 2>/dev/null
  (cd "$root/backend" && nohup "$venv/bin/python" -m uvicorn "$app" --host 127.0.0.1 --port "$port" --timeout-graceful-shutdown 10 >> "/tmp/feeless-$name.log" 2>&1 &)
  eval "born_$port=$(date +%s)"
  echo "$(date '+%F %T') restarted $name :$port"
}
# 💻 LM STUDIO WATCHDOG (owner, 2026-10-14: "local lm should be always running"): about once a minute — server down → `lms server start`;
# the agents' model not loaded, or loaded with a context too small for the brain prompt → reload it at LM_CTX (8192). A reload at most once
# every 30 min (a bad load never loops). Model name = LOCAL_LLM_MODEL in backend/.env (first value, like env_loader); nothing is printed but its name.
LMS="$HOME/.lmstudio/bin/lms"; LM_CTX="${LM_CTX:-8192}"; lm_tick=0; lm_reload=0
lm_model() { grep -m1 '^LOCAL_LLM_MODEL=' "$root/backend/.env" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' ' ; }
lm_watch() {
  [[ -x "$LMS" ]] || return 0
  grep -qi '^LOCAL_LLM_ENABLED=false' "$root/backend/.env" 2>/dev/null && return 0
  # LM Studio on ANOTHER machine (LAN base URL): that machine runs its own server + model — nothing to start or load here
  grep -E '^LOCAL_LLM_BASE_URL=' "$root/backend/.env" 2>/dev/null | head -1 | grep -qvE '//(127\.0\.0\.1|localhost)(:|/|$)' && return 0
  local model; model="$(lm_model)"; model="${model:-qwen2.5-7b-instruct-mlx}"
  if ! curl -s -m 5 -o /dev/null http://127.0.0.1:1234/v1/models; then
    "$LMS" server start >/dev/null 2>&1 && echo "$(date '+%F %T') LM Studio server started"
    return 0
  fi
  local ctx; ctx="$(curl -s -m 5 http://127.0.0.1:1234/api/v0/models | python3 -c "import json,sys
d=json.load(sys.stdin); m=[x for x in d.get('data',[]) if x.get('id')=='$model' and x.get('state')=='loaded']
print(m[0].get('loaded_context_length') or 0 if m else 0)" 2>/dev/null)"
  ctx="${ctx:-0}"
  if (( ctx < LM_CTX )) && (( $(date +%s) - lm_reload > 1800 )); then
    lm_reload=$(date +%s)
    (( ctx > 0 )) && "$LMS" unload "$model" >/dev/null 2>&1
    if "$LMS" load "$model" --context-length "$LM_CTX" --gpu max -y >/dev/null 2>&1; then
      echo "$(date '+%F %T') LM Studio: $model loaded at context $LM_CTX (was ${ctx})"
    else
      echo "$(date '+%F %T') LM Studio: could not load $model — next try in 30 min"
    fi
  fi
}
while true; do
  lm_tick=$(( (lm_tick + 1) % 3 )); (( lm_tick == 1 )) && lm_watch
  up 5001 /api/health            || { sleep 5; up 5001 /api/health || start 5001 "$root/.venv" server:app api; }
  # 5077 is probed on a CHEAP route: /fuses/prime rebuilds for 12–13s at times and the old probe restarted a healthy keeper every ~75s (2026-10-12)
  fresh 5077 || up 5077 /api/reputation/perf/config || { sleep 5; up 5077 /api/reputation/perf/config || start 5077 "$root/backend/.venv" reputation_service:app reputation; }
  up 5088 /docs                  || { sleep 5; up 5088 /docs || start 5088 "$root/backend/.venv" feecat_service:app feecat; }
  up 5099 /docs                  || { sleep 5; up 5099 /docs || start 5099 "$root/backend/.venv" candles_service:app candles; }
  if [[ -d "$root/circle/node_modules" ]] && ! lsof -tiTCP:5111 -sTCP:LISTEN >/dev/null 2>&1; then
    (cd "$root/circle" && nohup node server.mjs >> /tmp/feeless-circle.log 2>&1 &); echo "$(date '+%F %T') restarted circle :5111"
  fi
  # ⚡ FEELESS MCP for LM Studio (FEELESS_MCP_AUTOSTART=true in backend/.env): keep it up on :8765
  if grep -qi '^FEELESS_MCP_AUTOSTART=true' "$root/backend/.env" 2>/dev/null && ! lsof -tiTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
    bash "$root/scripts/feeless-mcp.sh" start >/dev/null 2>&1; echo "$(date '+%F %T') started FEELESS MCP :8765"
  fi
  sleep 20
done
