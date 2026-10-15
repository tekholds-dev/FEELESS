#!/bin/bash
# 🖥 LAN BUNDLE: everything the DESKTOP Mac's LM Studio needs to be the same FEE as this one — the FEE system prompt preset, the MCP
# connection to THIS Mac's FEELESS MCP (all tools: card, agents, diagnose, trades, site, coin, investigate, pump trending, notes, deep
# research, web), and the steps. Writes ./lan_bundle/ (git-ignored: it holds the MCP token). Copy the folder to the desktop Mac.
#   bash scripts/lan-bundle.sh
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/lan_bundle"; mkdir -p "$out"
ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo THIS-MAC-IP)"
tok="$(bash "$root/scripts/feeless-mcp.sh" token)"
preset="$HOME/.lmstudio/config-presets/FEELESS FEE Master.preset.json"
[ -f "$preset" ] && cp "$preset" "$out/" || echo "⚠ preset not found on this Mac — copy docs/lm_fee_prompt.txt into LM Studio by hand"
cp "$root/docs/lm_fee_prompt.txt" "$out/"
cat > "$out/mcp.json" <<JSON
{
  "mcpServers": {
    "feeless": { "url": "http://$ip:8765/mcp", "headers": { "Authorization": "Bearer $tok" } }
  }
}
JSON
cat > "$out/README.txt" <<TXT
On the DESKTOP Mac:
1. Copy "FEELESS FEE Master.preset.json" into ~/.lmstudio/config-presets/  (LM Studio › right panel › Preset › FEELESS FEE Master)
2. LM Studio › Program › Install › Edit mcp.json → paste the "feeless" entry from mcp.json here (merge with what is there).
3. On THIS Mac keep the MCP running:  bash scripts/feeless-mcp.sh start   (or FEELESS_MCP_AUTOSTART=true in backend/.env)
4. Load the model with context 8192+ (16K if it fits), temperature ~0.55. Start a NEW chat per question.
The token in mcp.json is private: anyone on your Wi-Fi with it can READ your desk (nothing can trade or move money).
TXT
grep -qx 'lan_bundle/' "$root/.gitignore" || echo 'lan_bundle/' >> "$root/.gitignore"
echo "✅ wrote $out (MCP at http://$ip:8765/mcp)"
