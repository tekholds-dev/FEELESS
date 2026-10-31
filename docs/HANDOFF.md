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
> **WORK RULE (owner):** ask the owner before EVERY task, do one task, show the proof, and move on only after he verifies it. Never chain tasks.
> **State (2026-10-31, desk v4):** Fee (leader) runs `nvidia/nemotron-3.5-super-vl:free` + `nemotron-3-ultra-550b-a55b:free` (Flint free was 503 "no upstreams", Step-5 is paid + our OpenRouter has ~60 tokens) · 🔑 API keys = a file-cabinet slot (`ApiSlot` → `ApiDrawer`), drawers slide out (`ck-pull`) · wizard step 1 = glass minds (`MindGlass`: in/out per 1M, $ a step, its task, full-task total), model release age (`ageOf`), HIGH/LOW USE on every how-they-work option · leaderboard = browser-window cards · visitor desk = fixed theater (`useTheater`, no page scroll) + mind rails + stored-drawer pop (`/api/cats/{id}/live` now carries `lastStored`) · trader demo = FEELESS BTC chart → perps (A) + BTC narrative (B), `record-agent-demo.py trade` · 📰 traders may browse coins + narrative only (`cat_policy.RESEARCH_*`, `task.research`) — backend + test, NO trader UI yet · now-line caret removed.
> **State (2026-10-31, pass + treasury):** creator + HQ admins run 5 agents (`agent_max`), users 2 · a user's general agent starts at $7 = $5 model credit + $2 fee (`cat_fund.START_CREDIT_USD`, one signed split) and calls OpenRouter FIRST (`ownerStaff` false; staff keep cheapest-first) — FEELESS's OpenRouter account has $0 credits + no provisioning key (owner to buy credits) · 🎫 Agent Pass (`agent_pass.py`, `lib/metaplexCore.coreMintPass`, `/api/reputation/agent-pass/*`): Core NFT to the owner, fee wallet = update authority, 10% royalty, mint fee HQ › Fees (0 = 2× Solana's cost, live 0.0056 SOL); BLOCKED until PUBLIC_SITE_URL (https) is set · 🏦 Treasury (`agent_treasury.py`, `/api/cats/{id}/treasury`): reads pump.fun + PumpSwap creator vaults live (proven: 1.78 SOL on a real creator), split presets; claim + payout NOT built (owner live test) · fixed: reputation read agents through the public view (funding broke) — now `x-feeless-internal` · gaps 30 tokens, AutoRange 30 pools + safe/mid/risky.
> **State (2026-10-31, desk v3):** owner desk = 2 big windows in the demo's chrome (16:10, A's caption bottom-left, B's bottom-right) → chat + THE FILE CABINET beside it (`AgentLog cabinet=[…]`: Credentials · Storage · Earn · Main cloud · log drawers; sign-in card opens 🔐) · visitors get a no-scroll view (`PublicMinds` + public `/api/cats/{id}/live`: host + step kind only) · Live Activity + Leaderboard open with LIVE NOW (`/api/cats/live-now`) · demos replay REAL HD recordings (`scripts/record-agent-demo.py`: a/b plan, c/d two jobs, t/u real charts; bot-checked sites are skipped) with side prints · coin / make-money asks get ≤3 questions first (`clarify.py`) · Steel live view HD + page-only. Dropbox keys set; GOOGLE_OAUTH_* NOT set. Earlier: P1–P5 (signed-wallet owner lock ≤24 h, per-agent vault `~/.feeless-vault/master.key` — back it up, Earn Mode planner, Launch › Pools tabs). Harness `/dev/cats?general` · `&visitor` · `?demo=plan|jobs|discuss`.
> **State (2026-10-31, CLAWBACK):** pushed FC07.1 (paper test staff-only) · Emergent packages removed · general agents = real credit only (free $10 healed on 5088 start) · agents' own wallets can never launch a coin / make an agent on FEELESS · ☁ agent storage + chat ＋ upload + ⬇ agent picture. NEXT: B1 per-tab polish, B3 FC03 drawer keys. Gate green (test_ai_play timing flake under load).

**Verify in this order, one at a time, with the owner:**
| # | Task | Status |
| --- | --- | --- |
| 1 | Ask Happy Assistant "what is 2 + 2?" in chat. Label 💳 = wallet paid, 🛟 = backup answered (then read `/tmp/feeless-feecat.log`, `[agent pay]`) | Built. Never paid live |
| 2 | Add about $3 SOL (split 100% wallet), send `buy 0.01 SOL of $JUP`, approve it | Built. Never run live |
| 3 | Send `sell all $JUP` | Built. Never run live |
| 4 | Withdraw to the owner's wallet | Built. Never run live |
| 5 | First non-staff agent: confirm flat fees land in the fee wallet; open HQ › Fees › Agents on screen | Fakes only, UI not viewed |
| 6 | Venice fallback (W06): needs the $5 top-up flow | Not built. Login tested live |
| 7 | Model share of the split arrives as USDC (today the agent swaps its own SOL) | Not built |
| 8 | Agents-tab fps recheck with the pane in view | Measured once at 41 fps |
| 9 | Then the rest of the queue: LAG01 chart overlays · MAC01 Spotlight · OSSY01 · SEC01 | Open |

**How agent money works:** funding = one amount, split by `creditUsd`, one signed tx (`cat_fund.plan`, `FundCat`). Creator credit is free and is only a FEELESS number. Model calls go: agent wallet USDC to SingIt per call (`agent_pay.py`, `_wallet_call`, `_thinking_money` swaps about 0.012 SOL when USDC is under $0.30) → OpenRouter (balance $0, its crypto API is gone: 410) → Groq free backup. Each agent stops at $0.10. Flat fees: `agentTradeFeeUsd`, `agentOtherFeeUsd`, `/internal/agent-fee`; staff pay $0.
**Accounts:** FEELESS Circle = sidecar 5111, never for users. Family + agent Circle = sidecar 5112 (`CIRCLE_TENANT=agent`), auto-started by reputation; never mix them. Crossmint is unused (api-key signers off). The engine's old store copy can't wipe owner data (`keep_owned`, `OWNER_KEYS`).

**Owner to-dos:** back up `~/.circle-agent/` and find the FEELESS Circle recovery file (`~/.circle` is empty) · rotate `CIRCLE_AGENT_API_KEY` only if he chooses (it was printed in a session log) · per-user Circle wallets still wait on counsel (DECISIONS #2) · Spotlight Privacy for the project folder.

**Presets:**
| What | Value |
| --- | --- |
| Push | `git push origin main`: the pre-push hook runs `scripts/gate.sh` once, path-aware. Never `--no-verify`, never edit during a gate |
| Restart | `kill $(lsof -ti tcp:<port> -sTCP:LISTEN)`, keep-alive relaunches in about 10 to 25 s (5001 · 5077 · 5088 · 5099). Check no pending book first |
| Never | move real funds yourself · run a paid call without the owner · kill the owner's processes · overlap gates · print `.env` lines (mask by NAME only) |
| Browser | open the pane only to look, then close it. A hidden pane reads 1 fps: never trust that number |
| Test harness | `/dev/cats?general&wallet` |

**FeeCat map:** wizard `command/LaunchCat.jsx` · desk `CatDesk.jsx` · funding, PIN, withdraw `CatReal.jsx` · workbench chat `CatWorkbench.jsx` · log `CatCockpit.jsx` · Fee's tools `FeeCatDesk.jsx`, `ProfileFeeCat.jsx` · one Fee door `FeeCatsPlatform.jsx › FeeDesk`.

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
