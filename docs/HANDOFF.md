# HANDOFF — THE ONE PAGE every Claude works from (any account, any session)

Owner, 2026-10-23: "the handoff should be ONE — it is where all Claudes are working from". So: **rewrite the 🔁 NOW section in place at the
end of every session — never stack a new dated handoff on top.** Finished work → one line in `docs/FEELESS_HISTORY.md` (the end); the
open list → `CLAUDE.md › 📋 CURRENT TASKS`. Old stacked handoffs live in `docs/FEELESS_HISTORY.md › 📦 ARCHIVED HANDOFFS` (grep, never load).

Read this (2 min) → `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING + 📋 CURRENT TASKS) → `docs/DECISIONS.md` (before any money / custody work) → only the history lines your task touches
(`grep -n "<topic>" docs/FEELESS_HISTORY.md`).

> ⚡ EVERY SESSION (owner, 2026-10-15 — repeat in anything you hand off):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. FULLY redo what is asked (owner: "not half do, not some side shit").
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 🔁 NOW (rewrite this section in place every session)
**Updated 2026-10-29 · Real card stopped buying (auto-halt) — fixed + live.** The Fuse wallet's gas reserve (fees + coin-account rent outside the books) ran dry: wallet 0.0311 SOL vs books 0.0345 → every 60 s balance read halted `degen` ("confirmed wallet SOL is below card books"); ▶ Resume bought once, the next read halted again. `fuse_wallet.fit_gas_shortage`: a gap ≤ 0.01 SOL the cards can cover is booked as fees the cards paid (`cardFeesSol`, P&L unchanged), never while an order is pending; bigger gaps still halt. Resume button shows "auto-paused" + the reason. Live 01:31: gasfit 0.003375 SOL → unhalt by itself. Also committed the agentStyle WIP (auto/scalp/ride) that 7b110495 already depended on (warden crashed without `real_learn.style_record`).

Gate: backend 2,268 passed/26 skipped · frontend 1,641 passed · build OK · pushed main b91cc98a · reputation :5077 restarted from Claude's watcher. Not browser-verified (the auto-paused label only shows while halted). OWNER: top up ~0.02 SOL of gas to the Fuse wallet — until then each trade's fees/rent come out of card cash (booked as fees).

Conserve usage · finish the selected work by priority · never dead-style.

| Live | Where |
| --- | --- |
| 🩹 SOL trades work from ANY wallet again: the fee wallet's wSOL account was closed (since 2026-09-30, a trade from that wallet closes it) → every SOL trade failed simulation; missing ⇒ the fee is plain SOL to the fee wallet (verified live: quote + simulate OK) · 🎚 agents' risk scale 1–4 (R4; a 4 = ¼ seat + quick scalp +8 %) · ⏱ NSFA 1/5/15-min survival watch (risk flags + intake meters) · 💬 OSSY × G4 beside the chart (phone sheet) · 👑 creator owns every Strike Zone gun | `trading.account_exists`, `fee_tx.fee_owner`, `office.risk_scale`, `survival_watch.py`, `AgentCockpit` |
| 📱📱 DUO FLOOR (iPhone Duo: folded 466×678 · open 890×626 wide / 626×890 upright, DPR 3, crease mid-screen, Safari has NO viewport segments): the Trenches coin floor on any Duo / tablet / sideways phone = a full-screen split app — wide: rail (← back · recent coins · ⇄ · home) \| chart half \| dock half, split on the crease; upright: coin bar + vitals · chart 58 % · dock · pump-style BUY / SELL bar. Dock = TRADE · CHAT · CALLS · COINS (intake + feed, tap = this chart) · TAPE; ‹ › / swipe = next coin. Every page on a wide Duo: ONE slim top bar (was 4 bars, 200 px). Familia: SWAP tab locked to the edge | `DuoFloor.jsx`, `duoFloor.css`, `lib/duo.js`, `duo.css`, `DuoBar.jsx` |
| 🫧 Intake: TRADE opens the Trenches floor (never the war room); in HQ › Agents it lands on the agents' chart · 🏆 BEST IN THE TANK (top 5 tradable: germ floor · READY · move · 1h vol · feeds agreeing) | `LiveTank.bestCoins`, `openTrenchTrade` |
| 🎯 STRIKE ZONE (replaced the Raceway): full-screen third-person shooter on three.js's Octree + Capsule physics + its Soldier model — bots or online rooms, the gunsmith (parts unlock by level), XP on the server's clock, family MP per kill · 📲 Telegram Mini App + level-up posts (`docs/TELEGRAM.md`) | `StrikeZone.jsx`, `StrikeGame.jsx`, `lib/strikeGame.js`, `arena.py`, `tg_auth.py` |
| 🫧 Intake lanes everywhere (the HQ band's look: water levels + colour dots + legend, a tap pops the coin's vitals first; HQ Agents gets an ALL LEVELS view) — site tank + the pool intake (replaced the waves) · 🔥 Pool Hall HIGH YIELD row + any typed amount · 💵 AutoRange sized to your typed amount (net-by-width curve + 7 vitals) · 🎯 Kalshi strike ladder (+ strike orders on the DFlow key) | `LiveTank`, `PoolWaves`, `autoRange.sizeBand`, `KalshiDesk.StrikeLadder` |
| 📱 Duo: second screen = TRADE by default (chart one screen, Quick trade + Dip/Rip + Shield the other) · phone: chart + BUY/SELL on one screen | `duo.css`, `lib/duo.js` |
| 🃏 live Card Room · ⚖ every Rep cartel raidable from any city · 🌊 Night Vault = a room of the Pool Hall · 📱 trench chart first on phones + Duo (icon rail, 50/50, Duo bar: swap + 2nd screen) | `CardRoom`, `CartelBoard`, `family_world.can_raid`, `duo.css`, `DuoBar` |
| 🔤 6 site fonts (tokens `--f-display/ui/mono/tech/noir/noir-it`, all loaded — JetBrains Mono had never loaded) · Perps: swipe provider rail, most-used first + market counts, your Jupiter recent trades, Crypto.com's FULL list (every perp w/ max lev + spot, searchable, tap → ticket) | `index.css`, `PerpsDash`, `PerpTrades`, `BrokerDesk.CdcMarkets`, `brokers.cdc_caps` |
| ⚡ Pump Radar = simple cards in a SMALL window; Runners Track + Trade Center are its rooms (row chips fixed) · Family HQ + its rooms open BIG, two columns · the Fuse / Skyline sections no longer paint over a big room | `CityAvenue.PumpRadar`, `cityPlan`, `familyWorld.css`, `familyHQ.css` |
| 📜 Settings › Updates (git → NEW / FIX · SITE · BACKEND · MOBILE, private bits dropped) + 📱 Duo screens (closed / open × portrait / landscape, this screen lit) | `/api/reputation/updates`, `updates_log.py`, `UpdatesLog.jsx` |
| 🚀 Launch: where-it-launches first (pump.fun = 2 steps, its own terms · FEELESS rail = SOL/$FEE pair · LaunchLab faint until its key), live pump.fun launch floor, form on the page, no review button | `MetaLaunchSetup`, `LaunchLab.LaunchFloor`, `LaunchModes` |
| ✅ HQ › Launch › Ready board (every way to launch: READY / exactly what's missing / one button) | `LaunchRailAdmin.ReadyBoard` |
| 🤖 AutoRange REAL (Meteora DLMM + Raydium CLMM open · close · re-center, simulated on mainnet, wallet signs) + phone ping when a move is due | `lib/rangeExec.js`, `AutoRangeDesk`, `/familia-pools/autorange/arm` |
| 🫧 Live intake tank, 5 levels (NEW · GERM · DESK · TRENDING · TOP NEW) on Trenches + Pump Radar · 🗼 Trench Towers live cards · 🧬 Fuse wallet glass | `LiveTank`, `TrenchTowers`, `FuseWalletGlass` |
| 📉 Perps: 250×, pay with USDC/SOL, landing card, provider-themed station, Crypto.com spot + perps keys | `docs/PERPS.md`, `brokers.cdc_*` |
| 🛟 Support: Ideas + 👍/👎/💬 · FEEd: X-style rows, ops pings out of the feed, Sign in with X · whitepaper = system cards · Settings: Small/Medium/Large, chart themes, Day/Night, Lite | `SupportHub`, `FeedX`, `FeelessUniverse`, `CommandDocuments` |
| 📱 Phones: clipboard on iPhone, wallet stays connected, no focus-zoom, Duo/foldable splits, trench chart fits + one swipe row of chart buttons | `lib/clipboard.js`, `lib/duo.js`, `styles/duo.css` |

| 🔑 OWNER PREREQUISITES (see WORK_QUEUE for engineering work too) | |
| --- | --- |
| `X_CLIENT_ID` (+ `X_CLIENT_SECRET`) from an X developer app; callback `PUBLIC_SITE_URL/api/reputation/x/oauth/callback` | Sign in with X |
| `PUBLIC_SITE_URL` (a public https domain) | FEELESS-rail + House launches, X sign-in |
| Sign the one-time FEELESS launch rules (HQ › Launch › Ready board) | FEELESS-rail coins |
| `DFLOW_API_KEY` · `SNAPTRADE_*` · a Raydium LaunchLab provider key | Kalshi · any broker · LaunchLab |
| `TELEGRAM_BOT_TOKEN` · `TELEGRAM_GROUP_ID` · `TELEGRAM_APP_URL` (steps: `docs/TELEGRAM.md`) | Strike Zone as a Telegram Mini App + group level-up posts |
| Crypto.com **Exchange** key + secret (`CRYPTO_COM_API_KEY` / `CRYPTO_COM_API_SECRET` in `.env` ride the owner wallet; the `cdc_` key in .env is a Developer Platform key — reads Cronos, can't trade) | Crypto.com trading |
| RPC quota (Helius / Alchemy were 429 — `SOLANA_RPC_URL` + `_3` answered) · a 4th `JUPITER_READ_KEY` | every wallet-signed action, prices |
| Circle account per user · "sign once, AIs trade" | needs counsel (custody, DECISIONS #2) — not built on purpose |
| First real money checks: a $25 AutoRange band, a Jupiter perps open, a Crypto.com key | proof on mainnet |

### Where today's work lives (frontend only; grep the history for "2026-10-23 evening")
- 🌆 Fee City METRO: `lib/cityPlan.js` (`METRO`, `KEYS`, `feePlan(v, mk, pools)`, `moneyShare` = 81 %) · `lib/cityEngine.js` (merged neon trims,
  `p.cars` budget, fog scales with the city) · `FeeCity3D.jsx` (`chipsOf`, money-first `Directory` + `DIR_GROUPS`, the `feeless:desk` host).
- 💸 `components/MoneyDesk.jsx` + `styles/moneyDesk.css`: `providersOf` (in-place only), `growth`, SAFE · DEGEN · MOON (`feeHunters`,
  `moonHunters`, `bandBoost`), `RangePicture`, `openDesk` (side panels open it over the map). Used by the family block pop-out
  (`FamilyBlock3D.BlockCard`), Fee City market / pool panels, the Pool Hub, FeeCat's combo.
- 🏙 Family block: `FamilyBlock3D` controls (☀ / 🌙 shared key `feeless.city.mode`, ⤢, 360°, ⌂) + `pop` over the stage; `errandGo` never links out.
- 💬 `StreetChat.jsx`: `BestStrip` (`bestCall`, `pumpHot`), starters, reconnecting line. 🐱 `catForge.css` (scope `.cfv`) + violet `createCat.css`
  + `StepRail`. 🚀 `launchFlow.css` + `STYLE_ART`, supply meter, `ReadyRing`. 📉 perps: `PerpsDash` (the room) → `perps/PerpsChart` · `PerpTicket` · `PerpPositions` · `KalshiDesk` + `PaperPerps` (🧪) — all in `docs/PERPS.md`.
- ⚖ `docs/COUNSEL_BRIEF.md` + DECISIONS #6.

### Gate + restart rules learned the hard way
- jest `--maxWorkers=4`; NEVER run tests while a gate runs; harden timing tests (poll, never a tight wall clock) — read the stack first.
- Chart libraries (`lightweight-charts`) load LAZILY from anything the city renders — jest can't parse their ESM; a static import turned 9
  Familia suites red on 2026-10-23 ("Test suite failed to run" with 0 failed tests = an import, not a test).
- A test's fixture clock must be the real clock when the component reads `Date.now()` (a fixed future epoch silently expires later).
- Restart backend: no `pending` in fuse_wallet.db books → start the watcher FROM CLAUDE (`/usr/bin/python3 -c 'import os; os.setsid();
  os.execvp("bash", ["bash","scripts/background.sh","start"])'`, sandbox off) → kill the PID, let the watcher relaunch it → 1 copy + LAN ONLINE.
- Merging into main locally never restarts the backend — after a backend push, restart reputation_service yourself.
- Every cat `/action` call needs the cat's `ownerId` (the browser id, `FeeCatsPlatform` adds it) or the internal key — tests too.

## 1 · What this is
FEELESS = a Solana degen trading terminal. One owner, one REAL money card run by ten agents, plus a big site (trade, Fuse, Arena,
chats, FeeCat, Familia). Money rules are strict and tested — read `CLAUDE.md › Money rules` before touching anything that buys or sells.

## 2 · Run / check
| What | Command |
| --- | --- |
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest` — it lacks the babel config) |
| build | `cd frontend && CI=false npx craco build` |
| all gates (pre-push hook) | `bash scripts/gate.sh` |
| restart backend | see "Gate + restart rules" above; then `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1 |
| real card cash | `backend/.venv/bin/python scripts/cash-check.py degen 30` (every task) |
| real card money trail | `.venv/bin/python scripts/fuse-report.py 6` |
| is there an edge? | `.venv/bin/python scripts/edge-audit.py` (run BEFORE advising on real-money buying) |

Services: `server` 5001 · `reputation_service` 5077 · `feecat_service` 5088 · `candles_service` 5099 · frontend 51367 (the owner's own dev
server — attach, never start a second). Push to `main`; the owner's Mac auto-pulls.

## 3 · Where things live (the files that matter most)
| Area | Files |
| --- | --- |
| agents (the real card) | `backend/agents.py` · `office.py` · `office_edge.py` · `trench_kernel/` · `opportunity.py` · `capital.py` |
| keeper (signs, sells, books) | `backend/fuse_wallet.py` · `arena_prime.py` (tier engine) |
| AI | `backend/ai_router.py` (providers, `with_studio`) · `prompt_studio.py` · `model_desk.py` · `ai_rig.py` · `ai_chat.py` (Brain) · `nexa_desk.py` |
| owner's LM Studio | `backend/feeless_mcp.py` (read-only MCP) · `docs/lm_fee_prompt.txt` · `docs/LM_STUDIO_MCP.md` · `docs/FEE_BRAIN.md` |
| big service | `backend/reputation_service.py` (31K lines — grep, never read whole) |
| Familia | `family_city.py` · `family_world.py` · `block_markets.py` → `FamilyWorld` → `FeeCity3D` (`lib/cityEngine.js` draws `lib/cityPlan.js`) · `FamilyBlock3D` · `FamiliaTrade.jsx` · `FamiliaApp.jsx` · `paper_perps.py` · `clmm_range.py` |
| FeeCat | `backend/feecat_service.py` · `feecat_brain.py` · `cat_model.py` · `cat_real.py` (real mode) → `components/feecat/` · `command/CatDesk.jsx` + `CatReal.jsx` |
| UI | `frontend/src/components/command/` (HQ) · `components/HomeEngine.jsx` · `styles/` (map in CLAUDE.md › CSS map) |

## 4 · How to work here (the owner's rules, short)
- Brief with the owner. Verdict, what changed, what was tested, what wasn't.
- Every money change ships with a test that fakes the network. Never hit mainnet or move funds.
- UI = m-* presets, transform / opacity only, day theme + fx-lite + reduced motion + 640px blocks.
- When you ship: tick it off `CLAUDE.md › CURRENT TASKS`, ONE line in `docs/FEELESS_HISTORY.md`, rewrite 🔁 NOW above.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
- Edge audit: still no rule positive on unseen coins — say so before any real-money advice.

## Delivery validation — 2026-10-28

Frontend: 345 suites / 1,637 tests passed; final targeted checks: 243 passed. Backend: 2,265 passed / 26 skipped. Production build passed with installed Node 22.17.1 (Node 18 lacks the crypto global required by current dependencies). Browser: 890×626 landscape, 626×890 upright, shortened 890×500 and 678×466; all five dock tabs and HQ toggle exercised; day/lite checked. Fixture chart values are not live account figures. Physical Safari fullscreen/keyboard and complete site-wide mobile QA remain unverified. Push hook will rerun required gates.
