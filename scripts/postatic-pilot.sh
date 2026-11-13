#!/bin/bash
# COL-6 · PoStatic pilot on OSSY + G4 — the ONE command (run it from YOUR Terminal; Claude has no LAN route to G4).
# 1) bash scripts/postatic-pilot.sh          → checks every mind and service, then tells you the one step left.
# 2) (on Sicario's desk) create a PoST and approve its plan — the loop runs itself: build → OSSY+G4 review →
#    headless playtest → file → stash → grade → stamp → events → vitals.
# 3) bash scripts/postatic-pilot.sh --check  → reads the newest PoStatic proof and ticks each kept piece.
set -euo pipefail
cd "$(dirname "$0")/.."
ENV=backend/.env
val() { grep -m1 "^$1=" "$ENV" 2>/dev/null | cut -d= -f2-; }
FAIL=0
ok() { printf '  ✅ %s\n' "$1"; }
bad() { printf '  ❌ %s\n' "$1"; FAIL=1; }

if [ "${1:-}" = "--check" ]; then
  exec .venv/bin/python scripts/postatic-pilot-check.py
fi

echo "— Services —"
for p in 5001 5077 5088 5099; do
  if nc -z 127.0.0.1 "$p" 2>/dev/null; then ok "port $p up"; else bad "port $p DOWN — bash scripts/start-backend.sh"; fi
done

echo "— OSSY (this Mac's LM Studio) —"
L_URL=$(val LOCAL_LLM_BASE_URL); L_KEY=$(val LOCAL_LLM_API_KEY)
if curl -s -m 5 -H "Authorization: Bearer $L_KEY" "${L_URL:-http://127.0.0.1:1234/v1}/models" | grep -q '"id"'; then ok "OSSY answers"; else bad "OSSY not answering — open LM Studio on this Mac and start its server"; fi

echo "— G4 (the desktop's LM Studio, LAN) —"
G_URL=$(val LAN_LLM_BASE_URL); G_KEY=$(val LAN_LLM_API_KEY)
if [ -z "$G_URL" ]; then bad "LAN_LLM_BASE_URL not set in backend/.env"; elif curl -s -m 6 -H "Authorization: Bearer $G_KEY" "$G_URL/models" | grep -q '"id"'; then ok "G4 answers at $G_URL"; else bad "G4 not answering at $G_URL — start LM Studio's server on the G4 and check the LAN"; fi

echo
if [ "$FAIL" = 1 ]; then echo "Fix the ❌ lines, then run this again."; exit 1; fi
echo "Everything answers. The one step left is yours:"
echo "  Open Sicario's desk → 💻 PoStatic → create a PoST (e.g. 'create a PoST named Pilot: a one-page FEELESS fee explainer')"
echo "  → approve its plan. The loop runs itself. When it's graded, run:  bash scripts/postatic-pilot.sh --check"
