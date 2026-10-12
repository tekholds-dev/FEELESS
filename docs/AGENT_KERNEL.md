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

## Legacy kept on purpose

- `agents.py` desk (desk / investigate / manage / evolve / survival / lives / burn) — it still builds the rows the kernel reads, runs the four
  desks' learning and real-money survival, and manages positions when trench mode is off. Its GO is an input, not the decision.
- `fill_plan` (GO / cleared cases / round-3 ENTERs) — the non-trench path when `agentOpen` is off.
- `arena_prime.py` / Prime cards — other products; they do not reach the kernel.
