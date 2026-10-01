# FEELESS — system map

One page: which engine owns what, where its data lives, and which shared hook/poller the UI reads it through.
If you add a feature, plug it into the row that already owns that data — never add a second source.

## Services (restart all after backend changes: `bash scripts/start-backend.sh`)

| Service | Port | Owns |
|---|---|---|
| `server.py` + `market.py` + `trading.py` | 5001 | market feeds (DexScreener + own indexes, **no GeckoTerminal**), quotes/swaps (Jupiter), chat (Mongo) |
| `reputation_service.py` | 5077 | reputation/case files, fees + fee ledger, quests/badges, Fuse, seasons, profiles, notifications, admin |
| `feecat_service.py` + `feecat_brain.py` | 5088 | FeeCat paper-trading agent (discipline: 9 lives, tilt/cold pauses, probation sizing) |
| `candles_service.py` | 5099 | candles (sanitize → gap-fill → continuous), trade tape (Helius → Solana RPC fallback), live price stream |

## Engines (pure, tested modules)

| Module | Decides | Read by |
|---|---|---|
| `investigate.py` | reputation score, every point cited | case files, rug shield, radar, alerts |
| `quests.py` | 40 badges, tasks, daily/weekly quests, XP/levels, perks, season score | `/quests/*`, `wallet_badges`, fee perk on quotes |
| `fuse.py` | Fuse legs, index, A–F score, split, creator cut, real-pool filter | `/fuses*`, Cmd Ctr Fuse builder |
| `fee_report.py` | per-wallet fees / FeeBack; totals rebuilt from the ledger (`_fee_totals_heal`) | fee report, Cmd Ctr fee book |
| `feecat_brain.py` | setup memory, edge, discipline | FeeCat loop + HQ strip |
| `candles_service._sanitize/_fill_gaps` | valid, gap-free, continuous candles | every chart |

## Shared client data (one request per key, never one per card)

| Data | Hook / store |
|---|---|
| market feeds, pairs | `useMarket` (SWR — same URL = one shared request) |
| your holdings | `lib/myHoldings.js` (`useHeld`, `useHeldList`, `HeldChip`) |
| quests, badges, perks, season | `useQuests` (QuestBoard, QuestNudge, ReserveProgress, Season, MintedTimeline) |
| launch forensics | `lib/coinIntel.js` (tape tags) |
| coin mood (chat bg) | `lib/coinMood.js` |
| snipers-out | `lib/snipersOut.js` |
| pump pulse | `lib/pumpPulse.js` |

## Money paths (see CLAUDE.md › Money rules)

Quote → simulate → wallet signs → server verifies the signed message equals the quote → broadcast → confirm sweep →
fee ledger (`fee_ledger.json`, the source of truth) → fee totals / FeeBack / Fuse creator cuts / quest metrics.
Anything that "counts" a trade (quests, Fuse buys, war-room trades) must find the signature in the wallet's
confirmed FEELESS trades — nothing is self-reported.

## Safety nets

- `tests/conftest.py` sandboxes every backend data path per test (tests can never write real data).
- `test_no_undefined_names.py` (pyflakes), `test_no_geckoterminal.py`, `styles/cssHygiene.test.js` (dead CSS + budgets).
- Lag catcher: auto fx-lite is temporary (6h, recovers after 3 smooth minutes).
