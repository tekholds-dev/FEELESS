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
**Updated 2026-10-23 ~09:00 · Opus 5.5**

Start of every task: `backend/.venv/bin/python scripts/cash-check.py degen 30` (≈ 1 min, sandbox off) — now 4 steps (cash · coins · swaps ·
P&L $). 2026-10-23 03:58: card COVERED · coins atom for atom · swaps match · 144 / 144 sells reconcile in $ (realized −$2.11, fees $0.35 apart).

Branch: everything lives on `main` (pushed; the owner's Mac auto-pulls). Gate + push from `.claude/worktrees/gate` (`git checkout --detach <sha>`
there, then `git push origin <sha>:main` — the pre-push hook runs the full gate on that snapshot, ~5 min; keep editing in the main tree meanwhile;
grep `Test Suites:` too — a suite that fails to RUN never shows in `Tests:`). Services restarted ~04:55 via the watcher (keep-alive PID 55631;
LAN ONLINE): reputation (house fees, staff gates, NEXA site read + trench prompts) + feecat (tunable `feePerSidePct`).

### Shipped this session (2026-10-23 late → dawn) — owner to look at
- 💬 THE STREETS go lit (`StreetChat.jsx`, `street_chat.py`): receipt mini charts, 📟 HITS tape, street HEAT → drawn scene, 🐢 Don slow mode
  (enforced on POST /chat), reaction bursts, coins trade in place. /dev/street?heat=0-3.
- 🏘 TOWN SIGNS live (`town_live.py`, GET /familia-town/live, `lib/townLive`). 🏟 Wars quiet front (`QuietFront`) + 🌹 drawn empty rooms (`FamEmpty`).
- 🚀 LAUNCH drawn (`LaunchViz.jsx`): stage + rocket riding your steps, step rings, coin face, fee ring ($ per $10K), sniper decay, lit inputs /
  review. /dev/launch.
- 💸 STAKE picker ($5 · $100 · $1K, `lib/earnStake`): Pool Hall rows a day + a year; Perps money read + P&L fan (`EarnStake.jsx`).
- 🌹 LA FAMILIA = ITS OWN APP: /familia/* (`FamiliaApp.jsx`): own bar + nav (deep links), pulse, wallet, phone dock; sidebar 'La Familia 🌹'.
- 🏠 HOUSE FEES in HQ › Core (`/admin/fees/house`, `HousePricing`): Fuse creator cap · FeeCat paper fee (pushed to her) · MP → FEECAT. /dev/fees.
- 🪟 NEXA: trench-law desk prompts + curve stage per coin · 🌐 site read (`site_probe.py`: RDAP age + page snapshot → REAL TECH / TEMPLATE,
  SSRF-guarded fetch, ≤ 2 per hourly full read, filed under the coin's mint).
- 👑 0c: feature gates use `_is_staff` (guard `test_staff_unlocks.py`) · 📒 `cash-check.py` step 4 · ⚛ HQ › Fuse rail 13 → 11 stops.
- Verified (no change needed): all 14 chat themes draw; NEURAL covers the whole Brain drawer; Night Vault at 360 px day theme.
- Then (2026-10-23 morning): 🏙 Familia's last link-outs are ROOMS (`lib/familiaRoom` — Fuse cards · Launch · Rug Shield over the city) · 💵 YOUR
  MONEY tower on the Avenue (`my_money.py`, GET /familia/my-money; value + 24 h move, never a fee-tainted P&L; /dev/money) · 💬 street typing
  presence + per-call threads · 🩺 stall watchdog (alerts; never reloads) · 🟢 38 inline grey-greens → neutral · 🖱 dead clicks fixed + a
  covered-button audit (clean) · 📲 La Familia installable. Services restarted ~08:55 (reputation: my-money, typing, watchdog).

### Still live from the day before (grep the history for details)
Brain › Models (`ModelDesk.jsx`, `model_desk.py`) · Prompt Studio (`prompt_studio.py`, `ai_router.with_studio`) · OSSY × G4 strict turns ·
trade inside Familia (`FamiliaTrade.jsx`; a guard test fails on any jump out) · US-legal Perps desk · owner picks stay (`arena_prime.owner_pick`) ·
the block = real markets (`block_markets.py`) · `scripts/cash-check.py` · `scripts/mindset-probe.py`.

### Open after this session (owner's order lives in CLAUDE.md › CURRENT TASKS — these are the specifics)
DONE since the last list: 🤖 agents hub (CatDesk + BrainPanel: credit tank, spend, owed, model fees, top-up) · ⚙ house fees in HQ › Core
(`/admin/fees/house`: Fuse creator cap, FeeCat paper fee — pushed to feecat_service — and the MP → FEECAT rate) · 🪟 NEXA desk prompts carry the
trench laws + each coin's curve stage · 📒 card P&L in $: `cash-check.py` step 4 replays the card's fills with the book's average cost (144 / 144
sells match; drained-pool write-offs counted) · 👑 0c: feature gates use `_is_staff` (guard test).
1. Block readers still unwired: Meteora DLMM (PositionV2 accounts by owner) · marginfi · Save · PumpSwap LP — verify each layout against a real
   account before shipping (wrong range facts on real money are worse than "no reader yet").
2. NEXA discovery: site age (RDAP / WHOIS) + page snapshot → "real tech vs same-utility clone" verdict.
3. Perps in the pop-out / in-app orders = owner + legal first (F0.1, A, A1).
4. G: keep hunting dead text in Familia rooms (Wars done) · Familia PWA icon / install prompt.

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
