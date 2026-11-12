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
# 🫀 AGT-18 patience: a service whose process is GONE restarts at once; one that is alive but silent (a browser read at Mac load 41 once
# lost its 5088 mid-proof to the old two-tries rule) gets STRIKES failed checks in a row (~20-40 s apart, so ~2.5 min), doubled while the
# 5-min load is over 2x the cores, before it is restarted. bash 3.2: per-port counters are plain variables (miss_<port>).
CORES=$(sysctl -n hw.ncpu 2>/dev/null || echo 8)
strikes() { local l; l=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print int($3)}'); (( ${l:-0} > CORES * 2 )) && echo 8 || echo 4; }
watch() {   # port probe-path venv app name
  local port="$1" v="miss_$1"
  fresh "$port" && return 0
  if up "$port" "$2"; then eval "$v=0"; return 0; fi
  if ! pgrep -f "uvicorn $4" >/dev/null 2>&1; then start "$port" "$3" "$4" "$5"; eval "$v=0"; return 0; fi
  eval "$v=$(( ${!v:-0} + 1 ))"
  if (( ${!v} >= $(strikes) )); then echo "$(date '+%F %T') $5 :$port alive but silent for ${!v} checks — restarting"; start "$port" "$3" "$4" "$5"; eval "$v=0"; fi
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
  # 🚧 Brain › Models is reloading the model right now (backend writes data/lms_reloading, < 5 min old) — never load a second copy beside it
  local mark="$root/backend/data/lms_reloading"
  if [[ -f "$mark" ]] && (( $(date +%s) - $(stat -f %m "$mark" 2>/dev/null || echo 0) < 300 )); then return 0; fi
  # 🎛 the owner's wanted context (Brain › Models / a chat line, data/ai_rig.json local.load.ctx) wins over the default
  local want; want="$(python3 -c "import json; print(((json.load(open('$root/backend/data/ai_rig.json')).get('local') or {}).get('load') or {}).get('ctx') or '')" 2>/dev/null)"
  local LM_CTX="${want:-$LM_CTX}"
  if ! curl -s -m 5 -o /dev/null http://127.0.0.1:1234/v1/models; then
    "$LMS" server start >/dev/null 2>&1 && echo "$(date '+%F %T') LM Studio server started"
    return 0
  fi
  # a busy model answers slowly: no answer = UNKNOWN, never "not loaded" (the old 5s read reloaded a generating gpt-oss every 30 min)
  if "$LMS" ps 2>/dev/null | grep -q "${model##*/}"; then return 0; fi
  local ctx; ctx="$(curl -s -m 20 http://127.0.0.1:1234/api/v0/models | python3 -c "import json,sys
d=json.load(sys.stdin); m=[x for x in d.get('data',[]) if x.get('id')=='$model' and x.get('state')=='loaded']
print(m[0].get('loaded_context_length') or 0 if m else 0)" 2>/dev/null)"
  [[ -z "$ctx" ]] && return 0
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
# 🔁 CODE RELOAD (owner 2026-11-11: "pushed live, no restart"): backend .py files changed (an edit here or a pull) → once the edits have sat
# 15 s, they compile, and no folder build / ad run is live on 5088 (/api/cats/health `busy` = 0; a restart kills a run), restart every
# service from THIS process tree. The owner's one command starts this watcher, so the restarted services keep his Mac's LAN route.
mark=/tmp/feeless-code-mark; touch "$mark"
changed_py() {   # backend code, and backend/.env (a new key goes live without a restart; it is not compiled)
  find "$root/backend" -name '*.py' -newer "$mark" -not -path '*/.venv/*' -not -path '*/tests/*' -not -path '*/data/*' -not -path '*/node_modules/*' 2>/dev/null
  [[ "$root/backend/.env" -nt "$mark" ]] && echo "$root/backend/.env"
}
code_reload() {
  local files newest busy
  files="$(changed_py)"; [[ -z "$files" ]] && return 0
  newest=$(echo "$files" | tr '\n' '\0' | xargs -0 stat -f %m 2>/dev/null | sort -n | tail -1)
  (( $(date +%s) - ${newest:-0} < 15 )) && return 0                                  # still being edited
  if ! echo "$files" | grep '\.py$' | tr '\n' '\0' | xargs -0 "$root/backend/.venv/bin/python" -m py_compile 2>/dev/null; then
    [[ "$code_said" == "$newest" ]] || echo "$(date '+%F %T') code reload waits: a changed file does not compile"; code_said="$newest"; return 0
  fi
  # 🧯 2026-11-12: compiling is not starting — a missing package (numpy) took 5077 down for 8 min. Each service must import in its own
  # Python first (what the gate checks), or the running copy stays up.
  local bad=""
  for m in reputation_service feecat_service candles_service; do (cd "$root/backend" && .venv/bin/python -c "import $m" >/dev/null 2>&1) || bad="$bad $m"; done
  (cd "$root/backend" && "$root/.venv/bin/python" -c "import server" >/dev/null 2>&1) || bad="$bad server"
  if [[ -n "$bad" ]]; then
    [[ "$code_said" == "imp$newest" ]] || echo "$(date '+%F %T') code reload waits: does not start:$bad (the running copy stays up)"; code_said="imp$newest"; return 0
  fi
  busy=$(curl -s -m 8 http://127.0.0.1:5088/api/cats/health | python3 -c 'import json,sys; print(json.load(sys.stdin).get("busy",0))' 2>/dev/null)
  if [[ "$busy" != "0" ]]; then
    [[ "$code_said" == "busy$newest" ]] || echo "$(date '+%F %T') code reload waits: ${busy:-?} build(s) running"; code_said="busy$newest"; return 0
  fi
  touch "$mark"
  echo "$(date '+%F %T') backend code changed ($(echo "$files" | wc -l | tr -d ' ') file(s)), reloading every service"
  start 5001 "$root/.venv" server:app api
  start 5077 "$root/backend/.venv" reputation_service:app reputation
  start 5088 "$root/backend/.venv" feecat_service:app feecat
  start 5099 "$root/backend/.venv" candles_service:app candles
}
code_said=""
while true; do
  lm_tick=$(( (lm_tick + 1) % 3 )); (( lm_tick == 1 )) && lm_watch
  code_reload
  watch 5001 /api/health "$root/.venv" server:app api
  # 5077 is probed on a CHEAP route: /fuses/prime rebuilds for 12–13s at times and the old probe restarted a healthy keeper every ~75s (2026-10-12)
  watch 5077 /api/reputation/perf/config "$root/backend/.venv" reputation_service:app reputation
  watch 5088 /docs "$root/backend/.venv" feecat_service:app feecat
  watch 5099 /docs "$root/backend/.venv" candles_service:app candles
  if [[ -d "$root/circle/node_modules" ]] && ! lsof -tiTCP:5111 -sTCP:LISTEN >/dev/null 2>&1; then
    (cd "$root/circle" && nohup node server.mjs >> /tmp/feeless-circle.log 2>&1 &); echo "$(date '+%F %T') restarted circle :5111"
  fi
  # ⚡ FEELESS MCP for LM Studio (FEELESS_MCP_AUTOSTART=true in backend/.env): keep it up on :8765
  if grep -qi '^FEELESS_MCP_AUTOSTART=true' "$root/backend/.env" 2>/dev/null && ! lsof -tiTCP:8765 -sTCP:LISTEN >/dev/null 2>&1; then
    bash "$root/scripts/feeless-mcp.sh" start >/dev/null 2>&1; echo "$(date '+%F %T') started FEELESS MCP :8765"
  fi
  sleep 20
done
