# HANDOFF — THE ONE PAGE every Claude works from (any account, any session)

Owner, 2026-10-23: "the handoff should be ONE — it is where all Claudes are working from". So: **rewrite the 🔁 NOW section in place at the
end of every session — never stack a new dated handoff on top.** Finished work → one line in `docs/FEELESS_HISTORY.md` (the end); the
open list → `CLAUDE.md › 📋 CURRENT TASKS`. Old stacked handoffs live in `docs/FEELESS_HISTORY.md › 📦 ARCHIVED HANDOFFS` (grep, never load).

Read this (2 min) → `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING + 📋 CURRENT TASKS) → only the history lines your task touches
(`grep -n "<topic>" docs/FEELESS_HISTORY.md`).

> ⚡ EVERY SESSION (owner, 2026-10-15 — repeat in anything you hand off):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. FULLY redo what is asked (owner: "not half do, not some side shit").
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 🔁 NOW (rewrite this section in place every session)
**Updated 2026-10-23 late · Opus 5.5 (ultracode round)**

Start of every task: `backend/.venv/bin/python scripts/cash-check.py degen 30` (≈ 1 min, sandbox off). 2026-10-23 01:11: card 0.008513 SOL
COVERED · coins atom for atom · 30/30 swaps match · 0 gap. Gas reserve 0.0074 vs 0.019 target (not card money — owner tops it up).

Branch: everything lives on `main` (pushed; the owner's Mac auto-pulls). Worktrees `night-1022`, `cat-program-*`, `cool-murdock-*`,
`loving-pare-*` are old — nothing on them that main lacks unless a line below says so. Gate in `.claude/worktrees/gate` (memory: gate-under-load).

### Shipped this session (2026-10-23, Opus 5.5 ultracode) — owner to look at
- 🌆 FEE CITY BREATHES (`lib/cityPlan.js`): duplicates are ROOMS of one building (`in:` — Ladder in the Podium, Precinct + Cartels in the War
  Room, Gym / Cards / Jobs in your HQ, Runners in Pump Radar, Watchtower in the Courthouse, Fuel in the $FEE Bank, Newsstand in the Wire; the
  pop-out shows a room strip, `roomsOf`), market islands keep their top 4, empty cells are PARKS, bigger cells + wider water (~47 → 18 buildings).
- 🗼 TT = ONE drawn landmark tower (`cityEngine.ttTower`): lit floors = intake coins (READY white-hot), hottest coin on the crown, searchlight.
- 🏘 TOWN PICKER on the block: `block_markets.TOWN / town_set`, `/familia-block/act` tadd / tdel, `TownPicker` + the tool pop-out over the 3D block
  (`deckBody`), preview `/dev/block?town=tt,perps,pools`. NEEDS the reputation restart to serve `town` (done at the end of this session if noted below).
- 🐱 FEECAT TERMINAL REDONE: `FeeCatShell` (violet nav for all 5 pages + Fee live + your cat), `FeeCatBrainPage`, `CatBuilder` (drawn gear /
  patterns / eyes in `Panther`, `lib/myCat`), agents = 4 tabs, `lib/feeLeader` one shared poll. Coats = 25 (`catCoats.jsx`, `catByName` for old names).
- 🟢 OFFICIAL GREEN SWEEP: green-tinted near-black surfaces → neutral near-black, grey-green lines / text → neutral (101 sheets), meta tokens.
  Re-run safely: the sweep keeps neon greens, golds, reds, blues and light colours (Familia / FeeCat / Launch / chat themes excluded).
- 🎭 PROMPT STUDIO ↔ LM STUDIO: `lms_preset.py` writes "FEELESS LIVE · OSSY" (what FEELESS really sends) into ~/.lmstudio/config-presets; the
  owner's "FEELESS FEE Master" stays untouched and only feeds LM Studio's chat window. AUTO-TUNE is ON by default for G4 + OSSY (`auto_on`).

- 🤖 AGENT DESK (`CatDesk.jsx`, violet: stage, meter tiles incl. today's loss vs cap, P/L curve, lit positions → war room, limits as meters) +
  🚀 LAUNCH-A-CAT violet (`BrainSocket`: your cat + wired brain orbs, lit step rail, sealed brief). Fixed: the agent page crashed on held coins.
- ⚡ LAG (C): city engine no longer walks the whole scene per frame (sign list, camera-gated), idle ambient ~30 fps; block page's 1 s re-render
  isolated (`StreetGame`). Real fps NOT measured (browser pane hidden). 📦 D: Familia = its own lazy chunk (`lib/familiaLoad`, `CrewCard.jsx`
  light pieces), terminal page JS 2,708 → 2,426 KB. E (bigger city window) was already done (88vh).
- NEXT: F (littest chat) · G · H Launch page redo · B pools/perps earn · town building live numbers on signs · F0.1 perps = owner + legal.

### Still live from the day before (grep the history for details)
Brain › Models (`ModelDesk.jsx`, `model_desk.py`) · Prompt Studio (`prompt_studio.py`, `ai_router.with_studio`) · OSSY × G4 strict turns ·
trade inside Familia (`FamiliaTrade.jsx`; a guard test fails on any jump out) · US-legal Perps desk · owner picks stay (`arena_prime.owner_pick`) ·
the block = real markets (`block_markets.py`) · `scripts/cash-check.py` · `scripts/mindset-probe.py`.

### Open after this session (owner's order lives in CLAUDE.md › CURRENT TASKS — these are the specifics)
1. 🤖 AGENTS HUB (users' cats): vitals, cost, P&L, model + context, credit + refill. Real-money agents = owner custody + pricing (docs/REAL_CATS.md).
2. ⚙ FEES in one HQ Core panel — still hard-coded: FeeCat `FEE_PER_SIDE` 1 %, `MAX_CREATOR_BPS`, `FEECAT_RATE`.
3. 🪟 NEXA one-line desk prompts in the trench style (`nexa_desk.ASK_BUY / ASK_HOLD`).
4. 📒 Card P&L vs fills reconcile in $ (SOL side proven by cash-check).
5. Block readers (Meteora DLMM · marginfi · Save · PumpSwap LP) · NEXA site age + snapshot · perps in the pop-out (legal first).

### ✂ Cut list (owner to OK each)
Fake model rows in `/api/cats/brains` · family_world drag-the-pizza ERRANDS + MP build catalog · 4 ways to start services → ONE supervisor ·
cat `/action` with no owner check · split the 31K-line `reputation_service.py` (new helpers: `_fblock_`-style prefixes; `test_no_name_collisions.py`).

### Gate + restart rules learned the hard way
- jest `--maxWorkers=4`; NEVER run tests while a gate runs; harden timing tests (poll, never a tight wall clock) — read the stack first.
- Restart backend: no `pending` in fuse_wallet.db books → start the watcher FROM CLAUDE (`/usr/bin/python3 -c 'import os; os.setsid();
  os.execvp("bash", ["bash","scripts/background.sh","start"])'`, sandbox off) → kill the PID, let the watcher relaunch it → 1 copy + LAN ONLINE.
- Merging into main locally never restarts the backend — after a backend push, restart reputation_service yourself.

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
| Familia | `family_city.py` · `family_world.py` · `block_markets.py` → `FamilyWorld` → `FeeCity3D` (`lib/cityEngine.js` draws `lib/cityPlan.js`) · `FamilyBlock3D` · `FamiliaTrade.jsx` |
| FeeCat | `backend/feecat_service.py` · `feecat_brain.py` · `cat_model.py` → `components/feecat/` |
| UI | `frontend/src/components/command/` (HQ) · `components/HomeEngine.jsx` · `styles/` (map in CLAUDE.md › CSS map) |

## 4 · How to work here (the owner's rules, short)
- Brief with the owner. Verdict, what changed, what was tested, what wasn't.
- Every money change ships with a test that fakes the network. Never hit mainnet or move funds.
- UI = m-* presets, transform / opacity only, day theme + fx-lite + reduced motion + 640px blocks.
- When you ship: tick it off `CLAUDE.md › CURRENT TASKS`, ONE line in `docs/FEELESS_HISTORY.md`, rewrite 🔁 NOW above.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
- Edge audit: still no rule positive on unseen coins — say so before any real-money advice.
