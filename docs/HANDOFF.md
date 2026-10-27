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
**Updated 2026-10-26 (final) · Opus 5.5.** The owner's build list is shipped; what is left needs a HUMAN (a key, a sign-up, a signature) — table 2.

| Live | Where |
| --- | --- |
| 🚀 Launch: where-it-launches first (pump.fun = 2 steps, its own terms · FEELESS rail = SOL/$FEE pair · LaunchLab faint until its key), live pump.fun launch floor, form on the page, no review button | `MetaLaunchSetup`, `LaunchLab.LaunchFloor`, `LaunchModes` |
| ✅ HQ › Launch › Ready board (every way to launch: READY / exactly what's missing / one button) | `LaunchRailAdmin.ReadyBoard` |
| 🤖 AutoRange REAL (Meteora DLMM + Raydium CLMM open · close · re-center, simulated on mainnet, wallet signs) + phone ping when a move is due | `lib/rangeExec.js`, `AutoRangeDesk`, `/familia-pools/autorange/arm` |
| 🫧 Live intake tank, 5 levels (NEW · GERM · DESK · TRENDING · TOP NEW) on Trenches + Pump Radar · 🗼 Trench Towers live cards · 🧬 Fuse wallet glass | `LiveTank`, `TrenchTowers`, `FuseWalletGlass` |
| 📉 Perps: 250×, pay with USDC/SOL, landing card, provider-themed station, Crypto.com spot + perps keys | `docs/PERPS.md`, `brokers.cdc_*` |
| 🛟 Support: Ideas + 👍/👎/💬 · FEEd: X-style rows, ops pings out of the feed, Sign in with X · whitepaper = system cards · Settings: Small/Medium/Large, chart themes, Day/Night, Lite | `SupportHub`, `FeedX`, `FeelessUniverse`, `CommandDocuments` |
| 📱 Phones: clipboard on iPhone, wallet stays connected, no focus-zoom, Duo/foldable splits, trench chart fits + one swipe row of chart buttons | `lib/clipboard.js`, `lib/duo.js`, `styles/duo.css` |

| 🔑 ONLY THE OWNER CAN DO THESE (everything else is built) | |
| --- | --- |
| `X_CLIENT_ID` (+ `X_CLIENT_SECRET`) from an X developer app; callback `PUBLIC_SITE_URL/api/reputation/x/oauth/callback` | Sign in with X |
| `PUBLIC_SITE_URL` (a public https domain) | FEELESS-rail + House launches, X sign-in |
| Sign the one-time FEELESS launch rules (HQ › Launch › Ready board) | FEELESS-rail coins |
| `DFLOW_API_KEY` · `SNAPTRADE_*` · a Raydium LaunchLab provider key | Kalshi · any broker · LaunchLab |
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
