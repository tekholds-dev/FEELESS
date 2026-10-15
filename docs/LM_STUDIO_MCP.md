# ⚡ FEELESS × LM Studio — MCP + model setup

Two separate wires:

| Wire | Direction | What it does |
|---|---|---|
| **AI router** | FEELESS → LM Studio | The agents + the Brain chat ask your model (gemma first, qwen as fallback). |
| **FEELESS MCP** | LM Studio → FEELESS | Your model, chatting in LM Studio, reads the live card, the agents, the trades, any coin, and the web. **Read-only.** |

---

## 1 · FEELESS → your LM Studio box (10.0.0.249)

In LM Studio on the box: **Developer → Server settings**
- Serve on local network: **on**, port **1236**
- Require API token: on is fine. Copy the token.
- Load `google/gemma-4-e4b` (context **8192** or more), and qwen as backup.

In `backend/.env` on this Mac, uncomment the block at the bottom (keep only ONE active `LOCAL_LLM_BASE_URL` — the first one wins):

```
LOCAL_LLM_BASE_URL=http://10.0.0.249:1236/v1
LOCAL_LLM_MODEL=google/gemma-4-e4b
LOCAL_LLM_FALLBACK_MODEL=qwen2.5-7b-instruct-mlx
LOCAL_LLM_API_KEY=<the LM Studio token>
```

Then restart the backend (`bash scripts/start-backend.sh`) and press **Test** on the LM Studio row in HQ › Agents › 🧠.

What changes when the model lives on the LAN box:
- this Mac's GPU stays free for Chrome → **no more Agents-tab stutter while it answers**;
- the agents may use it in the background too (it was owner-only because it shared this Mac's GPU), and it pre-reads coins 3× as often;
- the keep-alive watchdog stops loading models on this Mac (the box runs its own).

URL rule: `http://` is allowed **only** for localhost, 127.0.0.1 and private LAN IPv4 (10.x, 172.16–31.x, 192.168.x). Every public host must be `https://`.

---

## 2 · LM Studio → FEELESS (the MCP server)

On this Mac:

```bash
bash scripts/feeless-mcp.sh start
```

```bash
bash scripts/feeless-mcp.sh token
```

```bash
bash scripts/feeless-mcp.sh url
```

To keep it running with the other services, add `FEELESS_MCP_AUTOSTART=true` to `backend/.env`.

In LM Studio (on the box): **Program → Install → Edit mcp.json**, paste:

```json
{
  "mcpServers": {
    "feeless": {
      "url": "http://10.0.0.104:8765/mcp",
      "headers": { "Authorization": "Bearer PASTE_THE_TOKEN" }
    }
  }
}
```

(Use the address from `feeless-mcp.sh url` if this Mac's IP changes. macOS may ask once to allow incoming connections for Python — allow it.)

LM Studio running on **this** Mac instead? Use stdio — no token or port:

```json
{
  "mcpServers": {
    "feeless": {
      "command": "/Users/christopherclark/Desktop/feeless v.o7/backend/.venv/bin/python",
      "args": ["/Users/christopherclark/Desktop/feeless v.o7/backend/feeless_mcp.py"]
    }
  }
}
```

### Tools (all read-only)

| Tool | Gives the model |
|---|---|
| `feeless_card` | the real card: put in → now, all-time P&L, who controls it, every coin's % and $ |
| `feeless_diagnose` | the money picture + the levers: expectancy, biggest leak, rugs, doors, trail lab, blocked-vs-taken, controls with options |
| `feeless_site` | any section: runners · arena · gauntlet · callouts · edge · lists · calls · strategies · brain · learn · forecast · proof · slang · season |
| `feeless_agents` | mission, capital stance + leaks, the 4 seats with Reaper's ruling, top candidates, the Judge |
| `feeless_trades` | what REALLY happened in a window ("last night", "last 3 hours"): closed trades, ledger, Judge reviews |
| `feeless_coin` | FEELESS's full read of one mint (vital, holders, dev, tape, trench read, callers, socials) |
| `token_search` | ticker / name / CA → mint, cap, pool, 1h move |
| `trench_now` | weather + the live launch list with safety marks |
| `web_search` | DuckDuckGo (no key), cached 5 min; Brave if `BRAVE_API_KEY` is set |
| `web_fetch` | any public page / JSON API as text (private network refused) |
| `x_search` | recent X posts about a coin (via search) |
| `deep_research` | several searches (query + scam / team / news angles) and the best pages READ in parallel, each with its URL |
| `investigate` | one coin: FEELESS read + its own website (does it name the mint?) + its X link + web results for the CA |

There are no tools that sign, trade, move money or change a setting.

### Model settings in LM Studio
- Context **8192+** (16K if the box can hold it — tool answers are up to ~6K chars).
- Temperature 0.6 for chat.
- gemma-4 / qwen2.5 both do tool calls; leave "tool use" on.

---

## 3 · The system prompt + preset

The master prompt lives in `docs/lm_fee_prompt.txt` and is already installed as the LM Studio preset **FEELESS FEE Master**
(`~/.lmstudio/config-presets/FEELESS FEE Master.preset.json`): temperature 0.55, no response cap, context 16K on load, top-p 0.9,
min-p 0.05, repeat penalty 1.08. Pick it in the right panel › Preset. It makes the model:
- call `feeless_diagnose` before any advice (real expectancy, the biggest leak, rugs, doors, the trail lab, what the checks blocked);
- answer verdict → 2–4 real numbers → ONE move picked from the real LEVERS / CONTROLS (exact name, current value → a listed option);
- never give textbook filler ("diversify", "risk management is key").

The agents send their own brain prompt (`backend/ai_brain.md`) — editing the chat prompt never changes how they trade.

## 4 · Getting the most out of a small local model
- **One job per chat.** Start a new chat per coin / question — small models drift in long threads.
- **Make it call tools.** "check the card then tell me…" works better than an open question.
- **gemma-4-e4b** is quick and good at tool calls; **qwen2.5-7b** writes better analysis. A 14B+ model (qwen2.5-14b / gemma-3-12b) on the box is the next real upgrade.
- Keep KV cache / Flash Attention on in LM Studio for speed at 8K+.
