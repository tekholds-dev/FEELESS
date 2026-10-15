#!/bin/bash
# 🖥 LAN BUNDLE — get the desktop Mac's LM Studio to the SAME FEE as this one (FEE preset + this Mac's FEELESS MCP: card, agents, diagnose,
# trades, site, coin, investigate, pump trending, notes, deep research, web).
#
#   On THIS Mac (the one running FEELESS):   bash scripts/lan-bundle.sh
#       → starts the MCP if needed, writes lan_bundle/ (git-ignored: it holds the MCP token) and prints ONE line to paste on the desktop.
#   On the DESKTOP Mac, either:
#       • paste that one line into Terminal (curl … | bash), or
#       • copy lan_bundle/install.sh over (AirDrop) and run:  bash install.sh
#       • or, with this repo there + the lan_bundle folder copied in:  bash scripts/lan-bundle.sh install
set -e
root="$(cd "$(dirname "$0")/.." && pwd)"
out="$root/lan_bundle"
if [ "$1" = "install" ]; then
  [ -f "$out/install.sh" ] || { echo "✗ no lan_bundle/install.sh here — run 'bash scripts/lan-bundle.sh' on the FEELESS Mac and copy the folder over"; exit 1; }
  exec bash "$out/install.sh"
fi
mkdir -p "$out"
ip="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo THIS-MAC-IP)"
curl -fsS -m 3 "http://127.0.0.1:8765/health" >/dev/null 2>&1 || { bash "$root/scripts/feeless-mcp.sh" start >/dev/null 2>&1 || true; }
tok="$(bash "$root/scripts/feeless-mcp.sh" token)"
py="$root/.venv/bin/python"; [ -x "$py" ] || py="$root/backend/.venv/bin/python"
(cd "$root/backend" && "$py" -c "import feeless_mcp as m, sys; sys.stdout.write(m.install_script('http://$ip:8765/mcp', '$tok', prompt=open('../docs/lm_fee_prompt.txt').read()))") > "$out/install.sh"
chmod +x "$out/install.sh"
cp "$root/docs/lm_fee_prompt.txt" "$out/"
cat > "$out/README.txt" <<TXT
DESKTOP MAC — one of these:
  A) Terminal, paste:   curl -fsS -H "Authorization: Bearer <token>" http://$ip:8765/lan-install | bash
  B) copy install.sh here, then:   bash install.sh
Then in LM Studio: Preset › FEELESS FEE Master · turn on the 'feeless' MCP · load the model with context 8192+ · new chat per question.
This Mac must keep the MCP running (bash scripts/feeless-mcp.sh start, or FEELESS_MCP_AUTOSTART=true in backend/.env).
The token is private: anyone on your Wi-Fi with it can READ your desk (nothing can trade or move money).
TXT
grep -qx 'lan_bundle/' "$root/.gitignore" || echo 'lan_bundle/' >> "$root/.gitignore"
echo "✅ wrote $out"
echo
echo "👉 On the DESKTOP Mac, paste this ONE line into Terminal:"
echo
echo "curl -fsS -H \"Authorization: Bearer $tok\" http://$ip:8765/lan-install | bash"
echo
