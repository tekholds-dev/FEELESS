#!/usr/bin/env bash
# ⚡ FEELESS MCP for LM Studio — read-only desk + web tools (backend/feeless_mcp.py).
#   bash scripts/feeless-mcp.sh start    # HTTP on :8765 (LAN only, Bearer token) — for LM Studio on another machine
#   bash scripts/feeless-mcp.sh stop | status | url
#   bash scripts/feeless-mcp.sh token    # prints the Bearer token (paste it into LM Studio's mcp.json; keep it private)
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
py="$root/backend/.venv/bin/python"; [[ -x "$py" ]] || py="$root/.venv/bin/python"
port="${FEELESS_MCP_PORT:-8765}"
ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo 127.0.0.1)"
case "${1:-status}" in
  start)
    if lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then echo "already running on :$port"; exit 0; fi
    (cd "$root/backend" && FEELESS_MCP_PORT="$port" nohup "$py" feeless_mcp.py --http >> /tmp/feeless-mcp.log 2>&1 &)
    sleep 1; curl -s -m 3 "http://127.0.0.1:$port/health" && echo && echo "MCP url: http://$ip:$port/mcp" ;;
  stop) pkill -f "feeless_mcp.py --http" && echo stopped || echo "not running" ;;
  status) curl -s -m 3 "http://127.0.0.1:$port/health" && echo || echo "not running (bash scripts/feeless-mcp.sh start)" ;;
  url) echo "http://$ip:$port/mcp" ;;
  token) (cd "$root/backend" && "$py" -c "import feeless_mcp; print(feeless_mcp.token())") ;;
  *) echo "usage: $0 start|stop|status|url|token"; exit 1 ;;
esac
