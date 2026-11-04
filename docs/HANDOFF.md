# HANDOFF — THE ONE PAGE every Claude works from (any account, any session)

Owner, 2026-11-04: "always should be one MD". This file is the handoff AND the only task list (`## TASKS`, at the end). **Rewrite 🔁 NOW in place every session; a finished row leaves the list**
→ one line in `docs/FEELESS_HISTORY.md` (archive: grep, never load). Never start a second list.

Read this (2 min) → `CLAUDE.md` (lean rules + 🎨 MANDATORY STYLING) → `## TASKS` below (open rows) → `docs/DECISIONS.md` (before any money / custody work) → only the history lines your task touches
(`grep -n "<topic>" docs/FEELESS_HISTORY.md`).

> ⚡ EVERY SESSION (owner, 2026-10-15 — repeat in anything you hand off):
> 1. **Conserve usage.** grep first, read only the lines you need, batch commands, no essays, no re-reading files you just edited.
> 2. **Finish everything, in priority order.** When a new request lands mid-task, finish or hand off the current one — never leave a
>    surface half-organized or half-styled. FULLY redo what is asked (owner: "not half do, not some side shit").
> 3. **Never dead-style.** Before deleting CSS, confirm no component renders the class; every new box needs its rules in a sheet and a
>    LIVE visual (meters, bars, animation on real numbers), never bare text. `styles/cssCoverage.test.js` fails on an unstyled class.

## 🔁 NOW (rewrite this section in place every session) — 2026-11-04, production upgrade in progress
> **Owner flow (2026-11-03):** keep working through the Supreme Intelligence list, stop for owner review after every 5–10 major tasks. Reference free sources before building. SI23–SI30 are in `HANDOFF.md` (A, B and C pushed, fixtures only for the visuals). SI31 paid PoW only with the owner's OK. Fixture FPS: `/dev/cats?general&wallet` in headless Chrome (`channel='chrome'`); a backgrounded pane reads 1 fps.
> **Next (owner: chop this list down, stop and ask for more):** SI31 needs the owner's OK and closes the most at once. CH04 needs a stream key. Check the watcher before any restart: `bash scripts/background.sh status`; on 2026-11-04 it was NOT running and a kill left candles down. Watch real runs in Chrome through the Claude in Chrome extension: `localhost:51367/terminal/feecat/agents` → Happy Assistant; never restart `feecat_service` while a folder is open. New limits: change one and `test_pop.py` fails until `pow_kernel.VERSION` and the pin move on purpose. Fixtures: `/dev/cats?general&wallet`; a window fading in can screenshot blank, so wait 3 s.

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
- When you ship: its row leaves `## TASKS`, ONE line in `docs/FEELESS_HISTORY.md`, rewrite 🔁 NOW above.
- 🎨 Styling is MANDATORY (`CLAUDE.md › MANDATORY STYLING + ANIMATION`): drawn, alive, unique per page, a twist never a copy, screenshot it.
- Commit before long tasks (the update script auto-stashes uncommitted work). `git fetch` + rebase before pushing.
- Edge audit 2026-11-04: 31 of 1,066 rules positive on unseen coins, agents entered 0 of 3,000 calls. Many rules tested means chance winners: say so before any real-money advice.

## TASKS
Status: **OPEN** = requested; **VERIFY** = built, needs a real run or the owner's check; **OWNER** = key, account, signature or decision; **LATER** = needs a lawyer or audit first. Nothing here authorizes a trade or a payment.

**Perps (owner 2026-11-04):** no cheap venue with our keys, so agents only propose perps; the owner tests them by hand on the Crypto.com app. No agent perps sender gets built (FC04 closed).

### Supreme Intelligence upgrade — owner request 2026-11-03

Objective: improve the existing autonomous, model-replaceable research system through verified evidence and measured outcomes. Preserve independent two-mind/four-coin PoW, guarded trading and a model-free Colony. The owner subsequently authorized tested production pushes to main and the 51367 checkout, without stopping their running command. No request here authorizes a trade, treasury transfer or CAPTCHA bypass.

The owner's complete request is preserved in [SUPREME_INTELLIGENCE_REQUEST.md](SUPREME_INTELLIGENCE_REQUEST.md); this queue tracks its implementation.

**First ten, in implementation order (this pass):**

| ID | Status | Deliverable |
|---|---|---|

**Second batch requested, in this order (2026-11-03):**

| ID | Status | Deliverable and current evidence |
|---|---|---|

**Next ten, in order (2026-11-03; corrections are at the end of the request doc):**

| ID | Status | Deliverable |
|---|---|---|
| SI31 | OWNER OK | **One paid PoW + one paid PoP.** Also proves FC12 (sign-in, hand-off, sealed download, Stop). Everything else in Supreme Intelligence and today's PoP work is built and tested on fakes; this one run proves it live: SI01–21, 25, 29, 30, 34, 36, 37, 40, 41, 42, 44, 45, 46, 48, PF01, B02. Full text of each is in history. |

**Owner cleanup 2026-11-03 (no duplicate designs; snapshots):**

| ID | Status | Deliverable |
|---|---|---|


**Mechanics pass 2026-11-04 (each built backend first, then its screen):**

| ID | Status | Deliverable |
|---|---|---|

**Live PoW #14 debug + pPoP, 2026-11-04 (watched on the owner's signed-in page):**

| ID | Status | Deliverable |
|---|---|---|

### Owner batch 2026-11-04, second pass (charts, cleanup)

| ID | Status | Deliverable |
|---|---|---|
| CH04 | OWNER | **Live ticks are limited by the key.** `PRICE_STREAM_WS_URL` (Helius) answers 429, so the stream falls back to the public node + one Alchemy fill a second (`stream_lanes`). Measured on $GATO: 3 to 6 prices in 45 s. Per-trade needs a stream key with quota; the keeper's Helius key is not used for this. Drawing is not the limit: 60 fps, 0 long tasks (headless, dev build). No 30 fps easing: it would draw prices that never traded. |

**Owner batch 2026-11-04 (PoP folders, Bids, charts, backend):**

| ID | Status | Deliverable |
|---|---|---|

**Found in PoW #14, not changed (trading decisions, owner's call):** it picked $ANONVOYAGE with 0 verified facts and one snapshot, because its research hit a wall, and would have bought anyway. A pick with no verified facts should probably not buy. The chat says 0.01 SOL while the wallet cap sends 0.008. A dropped buy closes the folder and never re-buys. The agents list still shows an old `BUY $FLOAT · 1 to sign`.

**Still open from the full request:** FEE CAT Command Center rebuild; persistent shadow proposals beyond completed trade intervals; out-of-sample method comparison/combination and rollback; model-assisted memory migration and strategy comparison; unified kernel resource limits; real browser duration, evidence completeness, FPS and challenge-recovery baselines; authorized cross-worker sessions; transferred/distributed Colony reconciliation; versioned contracts and safe legacy encryption migration; responsive command-center redesign. The plaintext legacy agent store is restricted to owner-only file permissions; full encryption requires updating its many cross-service readers safely. Do not mark these complete from synthetic tests or visual labels alone.

**Security audit finding:** new per-agent PoW archive entries and saved site session contexts use the existing per-agent Fernet seal. Legacy archive entries and the main agent state file remain plaintext on disk; a careful, versioned migration with backups is still required before claiming full at-rest encryption. Public archive replies now omit private plans, browser steps and exact page excerpts. No claim of complete encryption is made for this pass.

### Owner requests 2026-10-30 — queued (FeeCat tabs came first and shipped; see HANDOFF 🔁 NOW)
| ID | Status | Task |
|---|---|---|
| FC03 | OPEN · OWNER FIRST (2026-11-02: only Happy has a key saved — Helius; no Birdeye / X / Telegram keys exist, so those reads can't be proven) | Wire the stored drawer keys into the brain (Birdeye holders, Helius RPC, X chatter, Telegram calls, signal webhook) — each read guarded + faked in tests. |
| C11 | OPEN | ALL site chats look like FeeCat's "her calls" bubbles: real bubbles, proper name / time / alignment (own messages right), one shared bubble component. |
| C12 | OPEN | Alliances: create from a reply, ≤ 10 members; after X days (owner to set X) an alliance can found a FEELESS Union; all alliance + union info lives in Support. |
| FC06 | OWNER | Agents' EARLY calls (NEXA / OSSY / G4): call a coin while it falls toward the germ floor or just as it breaks out, not only at the floor. Real-money buy-rule change ⇒ edge-audit it first, owner approves. Today the desk models read a TEXT chart snapshot (`ai_snapshot.py`), never an image; OSSY (gpt-oss-20b) is text-only; G4 (Gemma, LAN) can take a chart IMAGE → add a rendered 1m chart PNG to G4's ask. OWNER 2026-10-30: YES — they need the image snapshot (add to the desk workflow). |
| P11 | OWNER | Lag 2026-10-30: reputation loop blocked 68 % of 24 min (Lag catcher) while the Mac swapped 13 of 14 GB (24 GB RAM: LM Studio gpt-oss-20b 12 GB generating, ChatGPT/Codex, two dev servers, 6 stale preview servers from old sessions on :51412 :51433 :51437 :51399 :51411 :51431). Fixed in code: `reap_orphans` off the loop. Owner: close what isn't needed / move OSSY to the LAN box. |
| LAG01 | OPEN · NEXT SESSION FIRST (owner 2026-10-30) | ✅ FeeCat tabs 40 → 57-60 fps (`body.fcx-on`: one still sky, no stacked backdrops). ✅ 2026-10-30 done: PriceChart no longer rebuilds on each candle poll (setData in place, `chartShape` decides a rebuild); desk video + scrim on one sticky screen, covered ambient layers rest (`body.has-desk-video`), desk cards contained: video drops 41% → 8%. STILL OPEN: chart overlay jobs force ~3 s of layout per 27 s on a 2-chart desk (dev build, Mac load 30+) — `lib/chartFrame.js` jobs next. Lag + code cleanup for good: profile `reputation_service` (~24 % CPU idle) — it runs 28 `while True` loops (fast ones sleep 0.25–2 s: lines ~1292, 2883, 7071, 16626, 29777); ask the owner to OK `.venv/bin/pip install py-spy`, then `py-spy top` it and fix its hot pollers; re-measure every page (long-task observer + frame timing) and fix any >50 ms task; delete dead code/CSS with proof (cssCoverage / cssHygiene). |
| MAC01 | OPEN · after LAG01 | Mac storage + CPU burn: Spotlight on the project (owner toggles Privacy), swap ~6 GB, stale worktrees / caches — clean only what is ours, list the rest for the owner. |
| OSSY01 | OPEN · after MAC01 | OSSY / NEXA prompt cost (~300 tokens a call): trim the system prompt + case text, cache static parts, measure tokens before/after. |
| SEC01 | OPEN · AFTER the owner buys his first general agent (owner 2026-10-30) | FULL SECURITY HARDENING, front to back: prove nothing in the frontend bundle reaches backend secrets (no keys/tokens in JS, every write endpoint signed + owner-checked, CORS/CSP/headers, rate limits, SSRF + path guards, dependency audit), confirm encryption at rest (Fernet vault, BROKER_SECRET_KEY rotation) and in transit (TLS). Add 3 free defensive services layered so an attack only gets slower with no sure outcome (e.g. Cloudflare free WAF + bot fight + rate limiting, Cloudflare Turnstile on sign-ups, GitHub Dependabot/CodeQL secret + code scanning) — defensive only, no counter-attacks. Report findings + fixes. |
| FC07 | OPEN · step 1/5 shipped, owner testing (2026-10-31) | FINISH FEECAT TABS/PAGES 100%, one step at a time with the owner: ✅ 1 tab copy + paper leftovers (paper test = STAFF ONLY: UI `isStaff` + server 403 on a brainless cat without a staff session) · 2 per-tab polish 360/466/890 day+night (known: 🗑 overlaps the P&L number on My agents cards; long names truncate) · 3 FC03 drawer keys → brain · 4 real-money run (HANDOFF 1-4, owner present) (FC04 closed: agents only propose perps.) |
| FC09 | OPEN · NEXT | Agents' go-to sources for sign-ups (email providers that allow automated sign-up, storage, socials) + try every LEGITIMATE path before handing a step to the human. Never bypass CAPTCHAs / ID checks (safety rule) — those stay human steps. |
| FC11 | OPEN | Hive crawl engine (owner said GO 2026-10-31). OWNER: save X once in an agent's signed-in sites so traders can read X searches. |
| FC13 | OWNER | Dropbox: the app was made team-scoped; make a new Scoped access app and add the redirect `http://localhost:51367/api/cats/cloud/callback`. Pump.fun wallet launch stays your wallet's signature, never an agent's. |
| FC14 | OPEN + OWNER | Colony money, not built: sending payouts (approval flow + legal check), pool deposits, on-chain staking. Accruals and the ledger exist; nothing is sent. Your call whether to start. |
| FC15 | OPEN | Agent storage: cheap clouds an owner can buy with crypto; agents get their own email from the desktop. The rest of this row shipped (Colony, PoW v2, desktop apps); the full-site audit is Q07. |
| W05 | OWNER · BLOCKS EVERY AGENT ANSWER (2026-10-30) | Guard live: credit sales stop under $5 on OpenRouter (`cat_fund.credit_open`, `_openrouter_left`), the owner gets one alert a day, each agent stops at $0.10 of its own credit (`launch_cat.CREDIT_RESERVE`). OpenRouter account has $0 credit: every model call returns 402. FEELESS model credit is a ledger number and does not top up OpenRouter. Owner adds credit at openrouter.ai/settings/credits. Then re-run the 2 + 2 test ask, then the small real trade round trip. Design gap: paid model credit lands in the FEELESS fee wallet, nothing moves it to OpenRouter. |
| W02 | OPEN · FIRST | ✅ 2026-10-30 part: a real RECOVERY PIN (`backend/cat_recovery.py`) rebinds an agent to a new browser, hash only, never moves money. A user-held signer below is still open. OWNER 2026-10-30: "FEELESS provides a TRUE SECURE encrypted generated key for each user (I keep the root key safe)". Today an agent wallet = Crossmint smart wallet, admin signer = our API key → NO user-held key exists (the old random 'recoveryKey' was fake and is removed; SafeKeeping tells the truth). Build: per-user signer the USER holds — options: Crossmint delegated / passkey signer on the smart wallet (no custody change), or Turnkey / Privy embedded wallets with export (user can export their key). Avoid FEELESS generating + storing raw private keys (custody, DECISIONS #2 counsel). Wire: create → user signer → export screen ("save it, only chance") + confirm box (built: SafeKeeping) → withdraw signed by it. |
| V01 | OWNER | Backdrops: ocean.mp4 is in (Mixkit 25163). Mixkit blocked the other 3 automated downloads → save by hand from mixkit.co (Download, 720p) into frontend/public/backdrops/: forest.mp4 = 25158, peaks.mp4 = 4396, aurora.mp4 = 4038 (see LICENSE.txt). Until then those scenes are drawn. |
| C13 | OWNER | "Circle wallet to FEE": confirm = a Circle developer wallet for Fee (the leader cat, creator-owned, like the Crossmint agent wallet) — needs a Circle API key; per-USER Circle accounts stay blocked on counsel (DECISIONS #2). |

### Build next — latest owner priorities

| ID | Status | Specific remaining work / done when |
|---|---|---|
| M01 | VERIFY | 2026-10-29: phone eco (no overheating), site-wide sticky fix, Agents floor on Duo/fold/phone (MOBILE_LAYOUT › Duo floors). Still to sweep against the contract: Fuse, Launch, Radar, FeeCat, Familia, Perps pages + modals. OWNER: physical Safari. |
| F01 | VERIFY | FEEd v5 shipped 2026-10-29 (`FeedX.jsx`, `feed.css`, `feedPro.css`): 600px column, sticky glass header (For you/Following/Calls/Heat/Graveyard + 🔖, sliding underline), swipe source chips, composer with live CA coin card, ↑N new pill, post cards with live coin chip (→ Trenches floor) + call receipt, threads on a connector line, rail (search · pulse · trending · callers · who to follow · sites), mini-nav ≥1250, phone ✎ sheet + folding header, Duo split. Browser-checked desktop/360/Duo-wide/day/pop-out. Remaining: owner look on real phone/Duo; coin chips/receipts only seen via the composer (no coin posts in the live feed today). |
| G01 | OPEN | Strike Zone: real CC0 gun models and camo/PBR assets; replace placeholders, preserve gameplay. |
| T01 | OPEN | HQ Telegram center: bot rooms, alerts/trading/community/security, Mini App setup; FeeCat-art idle RPG and slot game hub. |
| C01 | OPEN | Familia desktop/mobile pass using shared room, vitals, panel and sheet templates. Every building opens a real function with live vitals. |
| A01 | OPEN | Fix-agent: Lag catcher + Support issue → investigation → branch fix → before/after visual preview → owner review. |
| D01 | OWNER | Public hosting, domain, HTTPS, production configuration and provider keys. Validate deployed endpoints. |
| H01 | OWNER | HQ tabs: unread folding, hidden '—' cells and one screen per tab need your screenshots of what bothers you. Harness and crash guards are done. |

### Product and engineering backlog

| ID | Status | Specific remaining work |
|---|---|---|
| L01 | OPEN | AutoRange: Orca as third venue, DLMM positions wider than 69 bins, compound LP fees; reconcile older tight-range/re-center requests against shipped Meteora/Raydium implementation. |
| P01 | OPEN | Perps: limit orders, owner fee controls, Coinbase Advanced door; additional venues only through approved eligibility flow. |
| B01 | OPEN | Brokers: Kraken/Coinbase own-key doors, YOUR MONEY totals, options; broker perps only when supported. |
| R01 | OPEN | RepMarket user sign-in/key and deposit flow; verify the permitted product/API before implementation. |
| K01 | OPEN | One user key vault in Familia. (The owner card shipped: HQ › Fees › Needs a human.) |
| A02 | OPEN | NSFA: at most five learning agents, ledger-based sizing/generation vitals; user Fuse dashboard with two charts, up to three agents and intake levels. Reconcile existing work first. |
| A03 | VERIFY | Same-coin shadow ledger and fresh edge audit; repeat after ~50 newer model trades; diagnose G4 uptime. No claim of profitable unseen performance. |
| A04 | OPEN | Cat learning/accept-loop parity with NEXA; G4 Models layout; trench theory only after shadow testing; launch-a-cat violet visual pass. |
| LA01 | OPEN | Launch: coin-first flow plus pools switch, Range Lab before signing, selected-venue configuration and arbitrary supported quote pairing. |
| C02 | OPEN | Familia: live building P&L, real-money/MP errands, rank/badge pools, custom backdrops; drag within 3D block, new islands/bridges/lots/kiosks and saved family layout. |
| C03 | OPEN | Block readers: Meteora DLMM, marginfi, Save, PumpSwap LP, Phoenix; construction state when funds removed; opt-in member positions. Verify each against an actual account. |
| C04 | OPEN | Night Vault: DCA/limit orders, compound LP fees, retire old MP drag-errands/catalog; outer-city markets, held/launched coin buildings, in-city raids, MP buildings/ladders, MOBhouse and for-sale island. |
| C05 | OPEN | Leverage: complete position-row handling and one-transaction loops. Verify existing close flow with owner-authorized use. |
| C06 | OPEN | Provider fee configuration for perps/LP/run/leverage/launch; no invented referral fields. Zora execution needs a supported venue. |
| Q01 | OPEN | Measure city FPS, instancing/LOD and load tests; move remaining stores to a database and support multiple workers. |
| Q02 | OPEN | Split `reputation_service` safely (the supervisor part shipped: `start-backend.sh` starts the watcher). |
| Q03 | OPEN | Site-wide text-wall/visual pass, FeeCat stage/tabs and perf, lore/launch flows, 3D roadmap/whitepaper; faster model reads. |
| Q04 | OPEN | Fee-Back eligibility, valuation/reference timestamp, settlement, rounding/distribution policy and audited payouts. Treasury buy/burn executor. |
| Q05 | VERIFY | Broader chain/indexer coverage, independent risk signals and moderation/identity claims from the old PRD; validate against newer implementation before rebuilding. |
| Q06 | OPEN | Feature-level geo/KYC switches guided by the existing decisions and counsel. |
| Q07 | VERIFY | Final site-wide click-through only after the relevant builds: day/night, 360px, lite/reduced motion, every step and empty state. |

### Owner prerequisites and verification

- Physical Safari/Duo review (M01); first funded wallet-signing checks belong to the owner.
- AutoRange $25 open/re-center/close; Jupiter perps open with TP/SL, partial close and TP move; broker paper key then authorized real link; Kalshi production metadata/order check; $5 bridge round trip and $2 gas fill; leverage open/close; first $5 Run deposit; FeeCat signed proposal. These are recorded requests, not actions performed in this session.
- X client ID/secret and callback domain; public site URL; launch-rule signature; DFlow, SnapTrade and LaunchLab provider keys; Telegram token/group/Mini App URL; Crypto.com Exchange keys; sufficient RPC quota and additional Jupiter read key.
- Contract path: week-long devnet soak with keeper host, external audit, upgrade-authority decision, capped mainnet deployment and launch settings. GO_LIVE is a technical checklist, not evidence these steps passed.
- Counsel review of custody/sign-once agents, legal venue eligibility, on-chain cat/pot programs and real-volume readiness. Preserve the current wallet-signing model until approved changes.
- Clarify older owner questions: remaining Fuse bug reproduction, Fee City fullscreen preference, Desktop-cleanup folder scope.

### Ideas — not approved implementation

Ticket-sized manual picks while record is red; automatic initial-out on winners; 30-minute hand-pick acknowledgement; fed/trending overlap; proven smart-wallet follow; FeeCat + agent pair conversations; better-coin track. Never remove Pump/New-launch tabs based on these old suggestions without a fresh request.

### Conflicts resolved for planning

- Older HANDOFF/CLAUDE statements that “everything is built” conflict with their own open lists. They are not a completion certificate.
- Duo per-tab implementations and the page watcher were subsequently committed. Treat them as mobile verification work, not wholly unbuilt features. Agents still needed this refinement.
- FAMILIA_PLAN is an older specification, not a claim the entire current city is unbuilt. Preserve its detailed requirements; verify gaps against code/history.
- Old PRD claims about unauthenticated chat/local-only features may be stale. Q05 is verification before new work.
- Circle/house-wallet notes differ across REQUIREMENTS, GO_LIVE and DECISIONS. Reconcile owner-only operation versus user custody before implementing; a cap setting alone does not resolve that distinction.

### Source map

CLAUDE's former CURRENT TASKS is preserved below for exact wording and the detailed FEEd specification. Supporting specs remain in HANDOFF, REQUIREMENTS, PERPS, BROKERS, GO_LIVE, FAMILIA_PLAN, REAL_CATS, DECISIONS, COUNSEL_BRIEF, DEGEN_PLAYBOOK, TELEGRAM, memory/PRD. FEELESS_HISTORY is evidence of older work, not a second active queue. Technical architecture/runbooks and .agents memory remain reference material. Update statuses here rather than copying another task list into those files.

<details>
<summary>Original owner request ledger (archived wording; statuses above take precedence)</summary>

### Old asks still open (from the 2026-10-29 lists; finished ones and repeats went to history)

| ID | Status | Ask |
|---|---|---|
| Q21 | OPEN | Trading agent desk: decision bubbles float on each chart, no full-width rows. |
| Q22 | OPEN | Fee's wall takes the Fee's calls design; remove the separate calls panel. |
| Q23 | OPEN | Price-gap engine: a live drawn view before buying, then the buyer's own running engine. Ships with buy guards. |
| Q24 | OPEN | No paper for users anywhere except the Fuse Arena: list what remains, then remove it. |
| Q25 | OPEN | FeeCat pages: charts first, minds under them, tighter layout; FeeCat on a profile is a pop-out. |
| Q26 | OPEN | Pools one stop: AutoRange + price gaps; Night Vault moves into Pools for Family and Launch. |
| Q27 | OPEN | First-visit tutorials for Family, Fuse, Trench, FeeCat. |
| Q28 | OPEN | Family command center: owner sets any cost (for example 5 MP for a city lot). |
| Q29 | OWNER | HQ › Fees showed the swap fee at 1500 bps (15%) on 2026-10-29: confirm that is intended. |
| SEC02 | OPEN | Forged sign-ups made before the push fix are not found or removed. From the write-route review: `reactions` trusts the voter name, `edge/observe` trusts the client's score and price. |
| CH05 | OWNER | Move agents and the real card onto true candles after a shadow test. They still read filled bars. |

**Standing rules:** US users only reach venues allowed for them. The user's wallet signs real money; FEELESS holds no keys or pooled funds. Every new buy door ships with guards. Touching a page means its whole flow. Money surfaces lead with the aggressive play and name the risk.

**Lawyer first:** a perps partner API, on-chain cat or pot programs, do-anything agents, real volume (`docs/COUNSEL_BRIEF.md`).
