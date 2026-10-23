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
**Updated 2026-10-23 · Opus 5.5** — the open list is `CLAUDE.md › 📋 CURRENT TASKS` (open items only, priority order). Nothing open lives here.

Start of every task: `backend/.venv/bin/python scripts/cash-check.py degen 30` (≈ 1 min, sandbox off; 4 steps: cash · coins · swaps · P&L $).
Last run 2026-10-23: card COVERED · coins atom for atom · 30 / 30 swaps match · 145 / 145 sells reconcile in $ (realized −$1.81, fees $0.34 apart).

Branch: everything lives on `main` (pushed; the owner's Mac auto-pulls; the old `night-1022` branch is fully merged). Gate + push from
`.claude/worktrees/gate` (`git checkout -q --detach <sha>` there, then `git push origin <sha>:main` — the pre-push hook runs the full gate on that
snapshot, ~5 min; keep editing in the main tree meanwhile). Services restarted after the real-cats push (keep-alive PID 55631, LAN ONLINE):
reputation (paper perps, points → MP, /internal/notify) + feecat (real mode, owner-only /action) — both live-checked (403 without owner / key).

### Where the 2026-10-23 work lives (all on main; details: grep the history)
- 🧭 `docs/DECISIONS.md` — the owner's go on every open decision: paper perps + venue handoff · real cats = the wallet signs (option A) · one
  points currency (1 pt → 100 MP, ≤ 1,000 / week) · no pooled custody · block readers only after a real-account check. A lawyer should read it.
- 💵 Real cats: `cat_real.py` + `CatReal.jsx` on a cat's desk (`CatDesk.jsx`) — proposals → ✍ Sign it → prefilled swap → wallet signs. `/dev/cats`.
- 📉 Paper perps: `paper_perps.py` + `PaperPerps.jsx` in the Perps building, `GET/POST /familia/paper-perps`. `/dev/perps`.
- 🌹 La Familia = its own app (`FamiliaApp.jsx`, /familia/*, installable) · rooms over the city (`lib/familiaRoom`, `FamiliaTrade.jsx`) ·
  YOUR MONEY tower (`my_money.py`, `/dev/money`) · town signs (`town_live.py`) · the Streets (`StreetChat.jsx`, `street_chat.py`, `/dev/street`).
- 🚀 Launch drawn (`LaunchViz.jsx`, `/dev/launch`) · 💸 stake picker (`lib/earnStake`, `EarnStake.jsx`) · 🏠 house fees in HQ › Core (`/dev/fees`).
- 🪟 NEXA: trench-law prompts + curve stage · site read (`site_probe.py`) · 🩺 stall watchdog (`model_desk.stall_of`) · 📒 `cash-check.py` step 4.
- Owner confirmed: 🐆 Sicario's seat board is fixed.

### Gate + restart rules learned the hard way
- jest `--maxWorkers=4`; NEVER run tests while a gate runs; harden timing tests (poll, never a tight wall clock) — read the stack first.
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
