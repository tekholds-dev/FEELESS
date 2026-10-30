# HANDOFF — THE ONE PAGE every Claude works from (any account, any session)

Owner, 2026-10-23: "the handoff should be ONE — it is where all Claudes are working from". So: **rewrite the 🔁 NOW section in place at the
end of every session — never stack a new dated handoff on top.** Finished work → one line in `docs/FEELESS_HISTORY.md` (the end); the
open list → `docs/WORK_QUEUE.md` (the single task list). Old stacked handoffs live in `docs/FEELESS_HISTORY.md › 📦 ARCHIVED HANDOFFS` (grep, never load).

Read this (2 min) → `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING) → `docs/WORK_QUEUE.md` (open rows) → `docs/DECISIONS.md` (before any money / custody work) → only the history lines your task touches
(`grep -n "<topic>" docs/FEELESS_HISTORY.md`).

> ⚡ EVERY SESSION (owner, 2026-10-15 — repeat in anything you hand off):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. FULLY redo what is asked (owner: "not half do, not some side shit").
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 🔁 NOW (rewrite this section in place every session) — 2026-10-30, end of session
> **State:** FeeCat is DONE and the owner is buying his first REAL general agent. Last push `38dd3547` (gate green), FeeCat service restarted.
> **Next session, in this order (owner):** ① LAG + code cleanup for good ② Mac storage / CPU burn ③ OSSY prompt cost (~300 tokens a call — trim)
> ④ SEC01 security hardening (after his agent is bought) ⑤ every other open row in `docs/WORK_QUEUE.md`. One task at a time, verified on screen.

**Presets the next Claude needs (no hunting):**
| What | Value |
| --- | --- |
| Push | `git push origin main` — the pre-push hook runs `scripts/gate.sh` ONCE (never run it by hand first). Gate is path-aware: docs → nothing, backend → pytest `-n 4 --dist loadfile`, frontend → pytest + jest (4 workers) + build. `GATE_ALL=1` forces all. A lone 60 s jest timeout = Mac load → re-push. |
| Restart FeeCat | `kill $(lsof -ti tcp:5088 -sTCP:LISTEN)` — the keep-alive watcher relaunches it in ~10 s (check `curl :5088/api/cats/leader` = 200). Same pattern for 5001 / 5077 / 5099. |
| Never | edit files while a gate runs (it tests the working tree) · `--no-verify` · kill the owner's processes · overlap two gates · change system settings |
| Agent models (general, $2–3) | Mind A **openai/gpt-6.1-terra** (~$0.08/task, lead) + Mind B **anthropic/claude-haiku-5.5** (~$0.008) · cap $0.25/task. Smarter: gpt-6.1-sol + claude-sonnet-5.5 (~$0.32, cap $1). |
| Live switches | `GENERAL_CAT_LIVE=1`, `OPENROUTER_API_KEY`, `CROSSMINT_API_KEY`, `CIRCLE_API_KEY`, `STEEL_API_KEY` set in `backend/.env`; `LOCAL_LLM_MODEL=qwen/qwen3.5-9b` (LM Studio = NEXA/OSSY). |
| Browser checks | open the built-in pane only to look, then CLOSE it — a live FeeCat tab burns CPU in the Claude app. |

**FeeCat map (where each piece lives):** wizard `command/LaunchCat.jsx` (`ModelBrowser` + `ModelPop` = the one model list everywhere · `briefFor`
generator · `COLLAB` per mode · `HOUSE` shown read-only — the real rules are server-side in `backend/cat_agent.py ACT_SYS` + `cat_policy.py`) ·
agent desk `CatDesk.jsx` (one 1110 px column; `ModelSwitch` with keep / 🧠 sort / fresh memory → `feecat_service._sort_cloud`) · live windows
`AgentLive.jsx` (4:3, ≤ 504 px, `coinVitals` strip) · demo `AgentDemo.jsx` (`DEMO_MODE`) · cockpit + 🗄 file-cabinet log `CatCockpit.jsx`
(`AgentLog`, `safeLine` masks secrets, `SceneVideo` pauses on scroll) · general workbench `CatWorkbench.jsx` (stream-safe `Blurred` logins,
per-mind ☁ clouds `brainsCfg.minds`, `handoff` action) · funding `CatReal.jsx` (`FundCat` reads `feeless.fundIntent.<id>`; recovery box after the
first payment) · Fee's models `FeeModels.jsx` (your model LEADS, NEXA helps). Lag fixes: `feeWall.css` contain + content-visibility.

**Agent wallets (2026-10-30):** Funding is ONE amount split by `creditUsd` (`FundCat` slider, `cat_fund.plan`): one transaction pays its wallet and model credit; a creator's credit is free. A general agent with a wallet goes real on funding (`ensure_real`): orders, typed in the order box or chat ("buy 0.05 SOL of $X"), become proposals sent from its wallet. It trades SOL pairs only: USDC is not spent by orders, and web tasks never spend the wallet. separate Circle account, sidecar 5112 (`CIRCLE_TENANT=agent`), never the FEELESS account on 5111. `agentWallet.circleAcct = agent`. Withdraw pays only `agentWallet.owner`. No real funding or withdrawal has run yet: test small first. DECISIONS #2 counsel note on per-user Circle still stands: owner's call.

**One Fee (2026-10-30):** every door (LIVE DESK for the creator, My agents banner, profile banner, leaderboard) opens `FeeCatsPlatform › CatDetail` → `CatDesk` + `Tools` (NEXA desk, visitors view, her book). Her engine / limits / retire stay server-only, so `CatDesk runs` hides them on Fee. **Account prompt:** `docs/CLAUDE_ACCOUNT_PROMPT.md`. Saved to `~/.claude/CLAUDE.md`.

**Agent money + limits (2026-10-30):** `cat_fund.py` pays SOL or USDC, into its wallet or model credit (`purpose`); free credit only for paper cats or creators (`free_credit_ok`). `FundPick` chooses before the wallet exists. `SpendLimits` (`cat.limits` + `taskCap`, enforced in `_work_start` + `cat_agent._ask`). `split_jobs`: one job = one owner + one supporter, never twice.

**Lag leads for ①:** **Measure only with the pane shown and Mac load low** (hidden pane = 1 fps; dev server rebuild + Spotlight hit load 94). Video backdrop drops fixed 41% → 8%, chart rebuild-on-poll fixed. Next: `lib/chartFrame.js` overlay jobs force layout (~3 s per 27 s). `reputation_service` idles at ~24 % CPU (profile it first: `py-spy top --pid $(lsof -ti tcp:5077 -sTCP:LISTEN)` if installed,
else time its pollers); Live desk was fixed (full layout 339 → 13 ms) — re-measure Her Brain / Lore / Arena / trade pages the same way
(long-task observer + rAF frame timing). Mac: Spotlight `mds_stores` up to 86 % → owner must add the project folder in System Settings ›
Spotlight › Privacy; ~6 GB swap (Chrome + LM Studio + Claude). `frontend/.env.development` turns the dev ESLint pass off (local only).

## 1 · What this is
FEELESS = a Solana degen trading terminal. One owner, one REAL money card run by ten agents, plus a big site (trade, Fuse, Arena,
chats, FeeCat, Familia). Money rules are strict and tested — read `CLAUDE.md › Money rules` before touching anything that buys or sells.

## 2 · Run / check
| What | Command |
| --- | --- |
| backend tests | `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` |
| frontend tests | `cd frontend && CI=true yarn test --watchAll=false` (never bare `npx jest` — it lacks the babel config) |
| build | `cd frontend && CI=false npx craco build` |
| all gates | run by the pre-push hook on `git push origin main` (path-aware; `GATE_ALL=1` forces all) |
| restart a service | `kill $(lsof -ti tcp:<port> -sTCP:LISTEN)` → the keep-alive relaunches it; then `pgrep -f "uvicorn reputation_service" \| wc -l` must be 1 |
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
- When you ship: tick its row in `docs/WORK_QUEUE.md`, ONE line in `docs/FEELESS_HISTORY.md`, rewrite 🔁 NOW above.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
- Edge audit: still no rule positive on unseen coins — say so before any real-money advice.
