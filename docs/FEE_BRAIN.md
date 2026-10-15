# FEE BRAIN — the portable AI pack

Everything a model needs to become FEELESS's brain, in one place. When a bigger / newer model arrives (local or cloud),
load THIS file's pieces into it — nothing else has to be rebuilt. The record it will be judged on already exists.

## 1 · The three prompts (and who reads which)

| Prompt | File | Who uses it | Shape |
| --- | --- | --- | --- |
| **FEE** — the owner's chat partner | `docs/lm_fee_prompt.txt` (+ LM Studio preset `FEELESS FEE Master`) | the owner, in LM Studio with the MCP tools | prose: verdict → numbers → one lever |
| **Brain** — the agents' coin reader | `backend/ai_brain.md` (condensed twin `BRAIN_LITE` in `ai_router.py`) | Sherlock / Devil / Judge / coach / exit reads | strict JSON case answer |
| **Brain chat** — in-app 🧠 Brain | `ai_chat.CHAT_ASK` / `IMPROVE_ASK` / `BUILD_ASK` | HQ › Agents › Brain + the mini cat | short prose / proposals |

A new model: paste `lm_fee_prompt.txt` as its system prompt for chat, point `LOCAL_LLM_*` / `LAN_LLM_*` (or a cloud key) at it for
the agents. Restart the reputation service. Done.

## 2 · The models today

| Slot | Provider key | Model | Where | Role |
| --- | --- | --- | --- | --- |
| 1 · primary | `lan` (`LAN_LLM_BASE_URL/MODEL/API_KEY`) | Gemma (`google/gemma-4-e2b`) | desktop Mac, LM Studio, LAN | lead read for every background case; first in chat |
| 2 · secondary | `local` (`LOCAL_LLM_*`) | Qwen (`qwen2.5-7b-instruct-mlx`) | this Mac, LM Studio | second read in the duet; owner chat |
| 3+ | groq · openrouter · openai · xai · custom | cloud | keys in `backend/.env` | the seat gate's cloud read, fallbacks |

`AI_PROVIDER_ORDER=lan,local,groq,…` (or the ▲▼ in HQ › Agents › AI providers). Gemma thinks by default — `EXTRA_BODY['lan']`
sends `reasoning_effort: none` or every answer comes back empty.

## 3 · 🤝 The duet — how the two grow together (`backend/ai_duet.py`)

1. Gemma reads the best unread READY / CONTENDING coin (the local lane).
2. If Gemma made a real call (CAUTION / FAVOR), Qwen re-reads the same case (≤ once / 150 s, never while a browser lags).
3. Both reads are graded on their own (15 min later, real price) **and** as a PAIR: agree %, how agreed calls did, who was right
   when they split.
4. A split stays NEUTRAL until one model has won ≥ 10 called splits at ≥ 60% — then splits go its way. The pair learns whose voice
   to trust from its own record, never from a rule someone typed.
5. An AGREED CAUTION may hold a coin back from a real seat (a lone small model never could). It can only make the agents buy LESS.
6. Chat: Brain › model switch › 🤝 Duet — Gemma answers, Qwen reads Gemma's answer and agrees or pushes back; both are shown.

Shown on HQ › Agents › 🧠 AI: the MODEL REPORT CARD (every model on one yardstick) + the DUET meters.

## 4 · Where model reads touch the agents (and the hard line)

| Agent | What a model gives it | Can it ever… |
| --- | --- | --- |
| Sherlock | the case read (call, risks, chart phase, scout of site / thesis) | rank a coin DOWN ≤ 15%, only once that stance is proven (`ai_learn`) |
| Devil | the seat gate read before a REAL buy | hold a coin back this tick on a strong, specific CAUTION (cloud, or the agreed duet) |
| Reaper | the exit read RIDE / TIGHTEN on held seats | widen / tighten the trail only once its own word is proven (`exit_read`) |
| Judge / coach | loss reviews, directives in a fixed vocabulary | add a graded ranking penalty; a wrong model rule ends itself |
| Rule lab | proposes rules in the record's own words | nothing until the rule passes walk-forward on REAL fills |
| Tally · Trigger · Warden · Courier · Reaper's stops | — | **never** asked (hot loops + the money boundary) |

No model places, sizes, signs or sells. That is code, not a promise: `FORBIDDEN_ROLES` in `ai_router.py`, tests in
`test_ai_router.py`.

## 5 · The MCP (owner's LM Studio chat) — `backend/feeless_mcp.py`

Read-only tools: `feeless_card` · `feeless_agents` · `feeless_diagnose` (money picture + real levers) · `feeless_trades` ·
`feeless_site` · `feeless_coin` · `investigate` (coin + its own site — does it name the mint? — its X link + web results for the CA) ·
`token_search` · `trench_now` · `deep_research` (several searches with scam / team / news angles, pages READ in parallel) ·
`web_search` · `web_fetch` · `x_search`. Every fetch is public-host only, re-checked on each redirect hop (no loopback / LAN /
metadata address can be reached). No tool signs, trades, moves money or changes a setting. Start: `bash scripts/feeless-mcp.sh start`.

## 6 · THE COUNCIL LOOP — the idea that ties it to money

```
 market ─► Tally/Sherlock read ─► 🖥 Gemma reads ─► 💻 Qwen challenges ─► Devil / seat gate (can only say "not this one")
                                                                                  │
 real fills ◄─ Courier ◄─ Warden sizes from the CAPITAL DESK (Kelly on the long real record, rug budget, drawdown brake)
     │
     ▼
 Archivist files it ─► graders (15 min price · real exit) ─► Judge blames a desk ─► rule lab / coach / duet trust update
     │                                                                                      │
     └──────────────► FEE (owner chat, MCP) reads the same record ─► ONE lever ─► owner ✅ ─┘
```

The only thing that compounds is the record. Models earn weight on it, the capital desk sizes from it, the owner changes a lever
from it. A bigger model plugs into the same loop and is judged on the same yardstick on day one.

## 7 · Upgrading to a bigger model — checklist
1. Load it in LM Studio (context ≥ 8192). 2. Set `LAN_LLM_MODEL` (or `LOCAL_LLM_MODEL`) in `backend/.env`. 3. Restart the reputation
service. 4. HQ › Agents › AI providers › Test. 5. Watch the MODEL REPORT CARD for ≥ 20 judged calls before trusting it over the old one.
