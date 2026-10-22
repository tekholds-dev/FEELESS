## 🔁 HANDOFF 2026-10-21 late — read first
Conserve usage · finish everything by priority · never dead-style. Owner rule: research the best sites first, then a FEELESS twist; every page
complete top to bottom. Order = `CLAUDE.md › CURRENT TASKS › FIFTH list`, then FOURTH, then THIRD.
1. 🐆 AGENTS clickables (timeframes / seat cards / decision cards "stopped working"): NOT FOUND YET. Ruled out: backend (every /admin call
   200, agent data fresh), crashes (none in bugs.json today), symTap (seat + tape cards are real buttons), QuickTrade (sibling, not nested).
   NEXT: the owner signs HQ with the new 📱 scan (`/hq-link`, Phantom deeplink) in the Chrome the extension controls → open HQ › Sicario's
   → click each control, read the console → fix with a test. (The Chrome profile the extension uses has no Phantom; the scan solves that.)
2. 🏦 FEE CITY ×3 with real markets: BACKEND DONE (`fee_markets.py`, `GET /api/reputation/familia-markets`: 13 Solana markets with TVL +
   busiest pool, `coins` = today's top 12 Solana coins; 60s cache). FRONTEND TODO: three market islands around Old Town in `FeeCapital`
   (east MARKET ROW = dex, west VAULT DISTRICT = lend/perps/stake, south NEW MONEY = coins), internal bridges, gates move to the outer
   islands (N heights / W harbor / E bay / S docks), world ≈ 2086×1170 (CityStage base zoom min → 0.3). A market = a big Building (dex
   tower / lend bank / perps casino / stake lab / coin mart) + a billboard (name + TVL or 24h move) + an activity light whose pulse speed
   follows volume; tap → camera flies + a MarketPanel (WHAT IT OFFERS · LIVE · ACTIONS: DEX pool → open on FEELESS; others → the market's
   own app, the wallet signs there — never custody). Lenses (Ranked, Raids, Errands, Challenges, Crew deck, Rewards, Cartels) move into city
   places (pop-out over the map from a landmark), the lens tab row goes. Stoplights at Old Town crossings (cars hold).
   BUG to fix first: `cityParts.buildingOf` builds `{at: 0}` and `Plot` passes `nowS={0}` → `Building` thinks EVERY city building is under
   construction (crane + scaffold = the "wand" the owner hates). Pass a real `nowS` (Date.now()/1000) in cityParts / FeeCapital / RaidStage.
3. 🛡 Security list item (no data hoarding; defend + learn; never attack back) — not started.

## 🔁 HANDOFF 2026-10-17 13:05 — read first (session "Ossy v G4 turn-based trading")
Conserve usage · finish everything by priority · never dead-style.
LIVE (backend restarted 13:05, one copy, all pushed to main, gate green):
- Agent coins HOLD: a soft exit needs OSSY / G4's TIGHTEN (`office.HOLD_SOFT`); time rules never sell a base (`BASE_TIME_RULES`, `base_of`);
  15-min breakout window; R11b dead-on-a-base holds; per-coin take `TAKE_ATR` 12× candle (≤ +200%); breakout skim 33% when accelerating.
- Reaper partnered: `SNAP_N` 3 alone / 1 on TIGHTEN / 5 on RIDE; pending sells get the model's exit read first.
- Owner one-click ✋ Hold / 👍 Good entry on every seat (`SeatHints` → `seatHint`, 30 min, graded by `_hint_grade`, also holds take lines).
- OSSY / G4: strict turns (only the holder / hunter is asked; a 10-min empty hunt passes the turn), cook 4 min, `structure_hold`, `line_hold`
  (SELL between SL/TP needs a chart reason; a +20% runner SELL → 33% skim), `TP_MIN` 25, read 1m + 5m charts every call, no gun-line coins,
  6h no-repeat (`recent_ai_buys`), no look-alikes, chat merge (owner lines never lost), coin rooms, between-trade talk, idle comments.
- Agents: models' BUY picks go first into agent seats, coins a model said SELL on are skipped; a coin left ≥3% red sits out 1h.
- Night guard + night shift OFF (owner's call, `_night_off_fix_1017`).
- Trades tab: model trades = 🔁 OSSY · G4 (orders carry `aiSeat`), never YOURS.
NOT DONE / NEXT: (1) re-run the exit report split before/after 12:12 and 13:05 (agent_archive positions, by rule + start red/green) and
tell the owner the numbers first; (2) find an entry reading that predicts a RED START (26% won vs 68% green) — none separated yet;
(3) G4 (desktop LAN) answered WAIT 70× in 6h — check its packet / candidate list isn't empty after the gun-line filter.
Restart rule: check no `pending` in fuse_wallet.db books, `pkill`-by-PID the reputation uvicorn, keep-alive restarts it, confirm count = 1.

# HANDOFF — start here (any Claude account, any new session)

Read this first (2 min), then `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING + 📋 CURRENT TASKS), then only the history lines your task
touches (`grep -n "<topic>" docs/FEELESS_HISTORY.md` — 700 KB of "why", never read it whole). This page is the map.

> ⚡ EVERY SESSION, EVERY HANDOFF (owner, 2026-10-15 — repeat these three lines in any handoff you write):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. All requests get done; the most important first.
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 1 · What this is
FEELESS = a Solana degen trading terminal. One owner, one REAL money card run by ten agents, plus a big site (trade, Fuse, Arena,
chats, FeeCat). Money rules are strict and tested — read `CLAUDE.md › Money rules` before touching anything that buys or sells.

## 2 · Run / check
| What | Command |
| --- | --- |
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest` — it lacks the babel config) |
| build | `cd frontend && CI=false npx craco build` |
| all gates (pre-push hook) | `bash scripts/gate.sh` |
| restart backend | `bash scripts/start-backend.sh`, then `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1 |
| real card money trail | `.venv/bin/python scripts/fuse-report.py 6` |
| is there an edge? | `.venv/bin/python scripts/edge-audit.py` (run BEFORE advising on real-money buying) |

Services: `server` 5001 · `reputation_service` 5077 · `feecat_service` 5088 · `candles_service` 5099 · frontend 51367 (the owner's own dev
server — attach, never start a second). Push to `main`; the owner's Mac auto-pulls. After a backend push, restart the backend yourself.

## 3 · Where things live (the 20 files that matter most)
| Area | Files |
| --- | --- |
| agents (the real card) | `backend/agents.py` · `office.py` · `office_edge.py` · `trench_kernel/` · `opportunity.py` · `capital.py` |
| keeper (signs, sells, books) | `backend/fuse_wallet.py` · `arena_prime.py` (tier engine) |
| AI | `backend/ai_router.py` (providers) · `ai_duet.py` (Gemma + Qwen) · `ai_learn.py` (grading) · `ai_chat.py` (Brain) · `ai_brain.md` |
| owner's LM Studio | `backend/feeless_mcp.py` (read-only MCP) · `docs/lm_fee_prompt.txt` · `docs/LM_STUDIO_MCP.md` · `docs/FEE_BRAIN.md` |
| big service | `backend/reputation_service.py` (16K+ lines — grep, never read whole) |
| UI | `frontend/src/components/command/` (HQ, Agents cockpit) · `components/HomeEngine.jsx` · `styles/` |

## 4 · Current state (2026-10-21)
- The open list is `CLAUDE.md › 📋 CURRENT TASKS` (owner's order). Approved build ideas: `backend/data/build_queue.json`.
- AI: G4 (desktop LAN) + OSSY (this Mac, gpt-oss-20b, 12 GB — the main reason this Mac swaps) take turns on one real seat; NEXA =
  the Windows i5 (llamafile, 1 slot): keep her chat prompt cached (re-warm after reads), answers ≤ 70 tokens, 20-min quiet after owner chat.
- Familia: `family_city.py` (the block) + `family_world.py` (the map: FEE CITY hub + 6 boroughs in 4 outer cities, rules, ranks, paid-hit math; bridges, CPU towns, cartels from the blocklist, chess
  raids, errands, challenges, rewards, FEECAT redeem claim). UI: `FamilyWorld` → `FamilyCity3D` (camera) → `FeeCapital` / outer islands, `cityParts`, `FamiliaHud`; HQ `FamiliaAdmin`.
- Edge audit: still no rule positive on unseen coins — say so before any real-money advice.

## 5 · How to work here (the owner's rules, short)
- Brief with the owner. Verdict, what changed, what was tested, what wasn't.
- Conserve usage · finish every request in priority order (never half-done) · never dead-style (see the box at the top).
- Every money change ships with a test that fakes the network. Never hit mainnet or move funds.
- UI = m-* presets, transform / opacity only, day theme + fx-lite + reduced motion + 640px blocks.
- When you ship something: tick it off `CLAUDE.md › CURRENT TASKS`, add ONE line to `docs/FEELESS_HISTORY.md` (the end), and update this page if the map changed.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
