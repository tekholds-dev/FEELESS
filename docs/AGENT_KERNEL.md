# ⚙ The agent kernel — one market state, one candidate lifecycle, one ten-agent brain

Branch `refactor/agent-command-kernel` (2026-10-12). Philosophy: `backend/trench_crew.py` + `docs/TRENCH_CREW.md`.

## The ONE path

```
sources (open board · newest launches · Pump live / pulse / trending / migrations · callouts · movers · volume · new pools · tracked lists)
  → the desk (agents.py: Tally's tape, Sherlock's drivers, Trigger's chart read, Devil's objections) builds ONE row per mint
  → trench_kernel.state.MintStore.ingest   one MintState per mint (deduped), events raised only for what changed
  → trench_kernel.brain.think               ten pure opinions → ONE reducer → status + rank   (only affected mints re-judged)
  → KERNEL.ready()                          the ONE list a seat fill reads (trench mode)
  → Warden (office.warden) → agent_seat → the ONE keeper (fuse_wallet / _fw_execute)
live prices (6-second guard) → KERNEL.price_event → Reaper's opinion now; office.fast_reap acts on the card
```

## MintState (one per mint, each section its own timestamp)

| section | fields | timestamp |
|---|---|---|
| identity | mint · symbol · pair · sources[] · ageH · launch | firstSeen |
| market | price · marketCap · liquidity · volume5m / 1h · pace · buyShare · move5m · liqChange · trades1h | priceAt · marketAt |
| chart | state · phase (market_wake.PHASES) · src · candles · quality · entry | candleAt |
| chain | holderStatus (PENDING / READY) · holderSafe · top10 · rug · earlyWallets · press · cls | holderAt · walletAt |
| research | status (READY / UNKNOWN) · site · x | researchAt |
| objections | Devil's raw objections from the desk | — |

## Candidate lifecycle (one meaning everywhere)

`DISCOVERED → TRACKING → CONTENDING → READY → ORDER_PENDING → HELD → EXIT_PENDING → CLOSED`

- TRACKING = data pending, outside the universe, or the hard wall — **never "rejected"**.
- CONTENDING = passes the wall, ranked.
- READY = Trigger ENTER + no hard veto + execution healthy + rank ≥ 120.
- Held positions are HELD / EXIT_PENDING whatever their cap (a winner over $200K is never sold for crossing the entry cap).
- Cooldown is metadata on the candidate, not a second universe.

## The ten agents (pure — they never fetch)

Tally measures · Sherlock lists known / UNKNOWN and *requests* evidence · Weather ×0.8…×1.1 · Trigger reads the live narrative (ENTER / ARM /
WAIT / NO) · Devil grades INFO / WARNING / STRONG_WARNING / HARD_VETO (only the wall is HARD) · Warden sizes (≥ ×0.5, ×0 only on a hard
veto) · Courier = execution health · Reaper = HOLD / PROTECT / TAKE / EXIT for held coins · Archivist = sources · Judge = evidence weight.

Rank = `opportunity.open_score` (newness × volume velocity × buyer velocity × momentum × early wallets × Judge × Devil confidence) × Weather × Sherlock.

## Four hunter lanes

HUNTING (searching; shows the best contender) · ARMED (a READY coin lined up) · HELD (capital in). The office never sleeps because seats are cash.

## Enrichment tiers (one scheduler: `_kernel_pass`)

- Tier 0: every discovered coin — board numbers only, **zero Solana RPC** (tested).
- Tier 1: real 1-minute candles for the fresh / strongest (`office_edge.candle_order`, the candles service).
- Tier 2: holder / early-wallet scans for the `ENRICH_TOP` 4 best-ranked candidates Sherlock asks about → `_runner_intel` (one scan per mint in flight).
- Tier 3: public research (`social_research`) on the strongest.

## RPC

`chain_rpc._rpc` = singleflight over `_rpc_physical`: identical in-flight reads share one request (writes never coalesced). `RPC_STATS`
(logical · physical · saved · 429 · refused) is in the payload. `RPC_SCAN_RPS` default stays **1.0** (the deliberate 2026-10-08 value; 0.3 / 0.5
starved the scan queue). Keyed lanes, quota parking, per-method refusal, keeper priority, public fallback and re-broadcast are unchanged.

## UI

`frontend/src/lib/agentHub.js` — `useAgentHub()` is the one store (snapshot + shared live prices) with selectors; `KernelBoard` (SeatOps) shows the
lanes and candidates; `agentRead.rowState` is the one decision meaning (a Devil warning is ⚠, only a hard veto is ✕ BLOCKED).

THE COCKPIT (`components/command/AgentCockpit.jsx` + `lib/cockpit.js` + `styles/agentCockpit.css`, the top of HQ › Agents, built to the owner's
reference): mission ribbon (`missionTiles`: put in · equity · net P&L · phase · breakeven · lives · occupancy · cycle · last real action · cash ·
keeper · execution) → four seats (`seatCards` + `seatState`: HUNTING · ARMED · HELD · PROTECT · ROTATE · EXITING · OPEN) → ONE market-cap chart
(price × the kernel's resolved supply; unknown supply = MC UNAVAILABLE, never a price chart) with the tape's real events lettered T D W B R X
(`letterMarkers`) → the LIVE DECISIONS strip (the kernel's decision tape) | the AGENT DECISION PANEL (live decision · inputs with freshness words ·
seats · owner review · trace in chain order) → the ten-agent matrix | review queue + OWNER REVIEW → operator controls (the creator's own limits on
the same `/admin/agents {cfg}` path) + the AI chip. Everything older (KPI tiles, lenses, the office room) sits in ONE `▸ MORE` fold. An agent pulses
only when ITS tape id moves (`newEvents`); MC / % / $ glide to each real value at ≤ 30fps (`useEasedNumber` — display only, no request).

## AI router (advisory; a PROVEN stance may weigh ±10% on the rank)

`backend/ai_router.py` (`ROUTER.reason(http, env, cfg, case, role)`): OpenAI-compatible chat providers tried in order — local LM Studio
(`LOCAL_LLM_ENABLED` / `LOCAL_LLM_BASE_URL` loopback only / `LOCAL_LLM_MODEL`, ONE inference at a time + a queue of 2) → Groq → OpenRouter → OpenAI →
xAI → any OpenAI-compatible host. Timeout / 429 / refused / malformed = the next provider; all fail = `NONE` (deterministic only). Answers are a
validated JSON object (`parse_advice`: stance from a fixed list, numbers clamped, summary ≤ 200 chars) cached per case state and shared while in
flight. Roles that may ask: Sherlock · Devil · Judge · owner review · manager. NEVER: Tally, Trigger, Reaper, Courier, Warden (refused in code).
The service's `_ai_loop` (own task, every 15s, ≤ 3 cases: owner review → a conflicted ENTER + Devil warning → the top contender → the newest Judge
review) writes `office.ai.notes[mint][role]` + the decision log `office.ai.log` (🧠 AI tab). LOW USAGE: `case_key` = the case's STATE (status ·
trigger · Devil's objections · coarse numbers), cached 10 min — a coin that only wiggled is not asked again. Sherlock's brief (`_ai_brief`: holders ·
chart · flow · launch · crowd, one short line each) is built from readings the desk already has — no fetch. THE AGENTS LEARN FROM THE MODEL ON ITS
RECORD (`backend/ai_learn.py`, `data/ai_proof.json`): each stance is noted at that price, judged 15 min later (no price for 1h = −100%); a stance moves
the kernel's rank (`opportunity.open_score(ai_w=)`, ctx `aiw`) by ×0.9 / ×1.1 only with ≥ 20 judged calls AND a typical result clearly better / worse
than the model's other calls. Unproven = ×1.0. The model never places, sizes, blocks or sells. `POST /admin/ai/ask` = the owner asks about one coin. Owner routes: `GET|POST /admin/ai/providers` (order + on / off,
`data/ai_providers.json`, no secrets) · `POST /admin/ai/test` · `POST /admin/ai-key` (keys tested, saved to backend/.env, never returned).

## Legacy kept on purpose

- `agents.py` desk (desk / investigate / manage / evolve / survival / lives / burn) — it still builds the rows the kernel reads, runs the four
  desks' learning and real-money survival, and manages positions when trench mode is off. Its GO is an input, not the decision.
- `fill_plan` (GO / cleared cases / round-3 ENTERs) — the non-trench path when `agentOpen` is off.
- `arena_prime.py` / Prime cards — other products; they do not reach the kernel.
