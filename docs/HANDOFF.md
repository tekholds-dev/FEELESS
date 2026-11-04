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
> **Next (owner: chop this list down):** 2026-11-04 overnight shipped PP01, MN01. SI50 closed: Fee's learned limits now apply only to Fee, and PoW #15 ran a real buy and sell on Happy ($Donkey, 0.008 SOL, −0.000586 SOL, plus 0.001514 SOL rent, since recovered). SI51 closed: an agent's own wallet closes its empty coin accounts every 10 min (`agent_trade.sweep_rent`; USDC stays open); Happy got 0.012106 SOL back on-chain. SI31 needs the owner's OK and closes the most at once. CH04 needs a stream key. Check the watcher before any restart: `bash scripts/background.sh status`; on 2026-11-04 it was NOT running and a kill left candles down. Watch real runs in Chrome through the Claude in Chrome extension: `localhost:51367/terminal/feecat/agents` → Happy Assistant; never restart `feecat_service` while a folder is open. New limits: change one and `test_pop.py` fails until `pow_kernel.VERSION` and the pin move on purpose. Fixtures: `/dev/cats?general&wallet`; a window fading in can screenshot blank, so wait 3 s.

> **Owner 2026-11-04, latest:** finish the whole MD without asking what's next, FeeCat and agent rows first, Familia last. Folder shapes stay; use the 3dicons packs inside them, never with a white background. New look = glass, live walls (`ShaderWall`), no huge text. Next rows: OSSY01, A04, FC11, FC03 (needs keys), Q03's FeeCat stage and lore, then the backlog by priority. OpenRouter credit (W05) blocks long paid agent calls.

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

**Agents first (owner 2026-11-04, in this order):**

| ID | Status | Deliverable |
|---|---|---|
| AG06 | VERIFY | PoP now reads sites in each mind's own window before it calls (coinglass, hyperliquid and others), each mind sees only its own read, and the folder shows what it opened. New PoB: `file a bid` or Bids › File a bid. Minds read sites, call a market blind, agree, then 50 free chips go on it and the market's result grades the folder. Tested with a fake browser and fake minds only; not run live (paid model and browser calls). |
| AG08 | VERIFY | `watch a wallet` files as a folder (PoW › 👁 Wallet watches): each address, the lines about it, Solscan link, one chain check (on chain / no history / not checked). Parser and check tested on fakes. Not run live (paid browser and model calls). |
| AG10 | VERIFY + OWNER | `build a project …` writes several static files, filed in Creations with a .zip and a sandboxed preview. A real free Groq call made 3 files and the parser took them; its script ran in a test iframe ($100 bill → $115.00). The chat-to-Creations path is fakes only and the Creations row is not seen on screen. A real dev server (node, packages) still needs a sandbox host and key, such as E2B. |
| SD01 | VERIFY | 🌐 Site door in every proof folder (`SiteDoor.jsx`, `site_scan.py`): type a site, Open + sign in by hand, Scan. A fetch reads terms, fees and help pages; a wall or no terms goes to its browser. Files a manual: meters, snapshot, Do / Don't / Withdraw / Fees / Bots / Regions / Risk / Pages, every line tied to the site's own sentence and source. Read + signed in earns `file a pump pow`, `file a polymarket bid` etc: its windows go there first, read only. Live on Happy's desk, signed in: Polymarket read 6 of 6 pages, real snapshot, worded by its model for $0.0022, CAUTION (bots banned). pump.fun stayed behind Cloudflare even with its saved sign-in: NOT READ, no command. Both manuals are still on Happy. Not run: a fresh hand sign-in, Open + sign in inside the folder, a site command through a real proof. Live finding fixed: "scanning" ended before the manual was saved, so the page missed it; fix is tested, not re-run live. |
| OD01 | VERIFY | 👑 Owner tab = two live monitors. FEE opens the same desktop agents get plus Lane, Brain, Prompts, Wallet + style. AGENTS opens Colony, Honeypot, PoW folders, Agent slots, Performance. Seen live on the owner's page, every app opened with content. Fee's Performance chart is empty because she files no proofs; her glass shows her paper record. |
| PF01G | VERIFY | 🫧 Every desktop has a see-through performance glass; tap it for a chart with crosshair, per-proof bars, table view. PoW SOL, PoP paper %, PoB chips are never added together. Chart seen only as the agents list live; the crosshair chart is tests and code, no real data shown yet on screen. |
| TU01 | VERIFY (owner testing) | 💸 `top up pump`, `top up pump $1.50`, `add $2 to pump`. It reads your deposit address in its signed-in window, or you paste it. Yes / No / amount in chat or card. One SOL transfer from its own Circle wallet, $0.50 to $25, keeps gas. A page-read address needs its last 4 typed. Manual shows LOADED: the address's on-chain balance. Fakes only: no real send, no real address read. It cannot use the site's own deposit flow, only an on-chain address. |
| IC01 | VERIFY | 🧊 3dicons V1 + social, white cut out, 1 MB total, on our own origin. 1,019 rendered symbols and 200 line icons swapped outside Familia. Small controls (close, menu, arrows, checks, copy, refresh) stay line icons. Emoji inside strings (button words from data, chat lines, the "Fuse 🧬" nav titles) are not swapped. 15 pages, signed out, headless, dev build: 60 fps, no broken icon, no console error. Signed-in pages and phone not swept. |
| PB01 | VERIFY | 🏈 `file a pob best NFL picks`, or type a topic in Bids. Each mind opens major sites for that topic (ESPN, NFL, CBS, Action Network, Covers, Kalshi, Polymarket), one snapshot per site, then calls up to 3 picks blind. The folder shows picks, what both agree on, snapshots; the owner marks it right or wrong. Nothing staked. Fakes only, not run live (paid calls). |
| DK01 | VERIFY | 🖥 Wallet + Limits moved from tabs onto the desktop. 12-step first-time tour pointing at the real icons, replay in Manual. Lamp over monitors. 3 new live backdrops in the desk's skin picker. Manual: PoB, Sites, Funding, Mail tabs. Shared glass for every folder window. Tour, lamp, Wallet seen live, night, desktop. New Manual tabs, Limits layout, PoB topic folder, live backdrops, day theme and phone not seen on screen. Wallet is still about 2,400 px tall inside its window, and Jobs and Files only got the shared glass. |
| BC01 | VERIFY (owner) | 🔥 Bot check after sign-in. Measured on Happy's real pump.fun save: all 15 cookies including `cf_clearance` load, and every NEW window is still walled (Kernel and Steel, routed or plain, 4 of 4). Cloudflare ties it to the browser that passed. Fix: save keeps that window open (`_WARM`, 14 min, Steel's 15-min cap), the scan and the first agent window on that site work inside it, unrouted. Open + sign in reopens the same window. After it ends, a new window hits the check again and hands it to the person. Never stealth or a solver. Tested with fakes; needs the owner's real sign-in + save. |
| TY01 | VERIFY | ⌨ Type-and-paste bar above every sign-in window (`signin_type`, `type_into`): Send, Paste, Hide, Tab, Enter, Delete, Its email, Newest code. Live on a real Steel window (httpbin form): email landed in the box, Tab moved on, next word landed. Never stored or logged. Not run on pump.fun. |
| ST01 | VERIFY (owner, real money) | 🛒 Trades on its own site account (`agent_site_trade.py`): `buy $1 of $BONK on pump`, `sell all $BONK on pump`. Owner's typed words only. Asks yes/no, or "No question" in the manual. Buys: $0.50 to $25, $50 and 6 a day, pool $10K, age 10 min, not up 300% in 1 h. Its window presses the site's own button once. Receipt from the chain when its site wallet is known, else UNVERIFIED. An order never resumes after a restart. Fakes only. NOT wired into the PoW loop yet: PoW still buys through FEELESS, wire after the first real $1 works. |
| PL01 | VERIFY | 🔁 Proof Loop (`proof_loop.py`): PoW drops a coin with the fingerprint of a past loss (source, pool, cap, direction; only ever trades less) and studies its last 5. PoB keeps one series per topic and tells both minds what they called and how you marked it. PoP studies its last 5. Fakes only. Bids on our board and PoP need real runs to show the loop chip. |
| PF02 | VERIFY | 🏆 Proofs folder on every desktop (`ProofsFolder.jsx`): results ring, 3D chart, loop orbit, PoI timeline with the decisions and snapshots at the time. Seen live on fixtures, night, desktop. Not seen on a signed-in agent, phone or day. |
| RW01 | VERIFY | 🎁 Rewards page `/terminal/rewards`, the sidebar's MOB & Rewards landing (`RewardsDash.jsx`): points, level, streak, claim all, The Hunt (closest badges), deposit to family bank (the shop's real `mp` items), trophy wall, shop, top points. Every button is an existing server route. Seen on fixtures at `/dev/rewards`, night, desktop. Not seen signed in, phone or day. |
| CH02 | VERIFY | 💬 Your question now shows the moment you send it (it was saved only when the task ended, 34 s later on the owner's 2+2). The chat box keeps 120 px beside any card. Fakes only: send one real ask to confirm. |
| SC01 | VERIFY | 🔒 Security audit 2026-11-04. Sound already: no plaintext cookies, passwords or keys in the store (checked on the real file), sign-ins sealed per agent, master key outside the repo at 0600, every door asks the wallet's signed session. Closed: public PoW/PoB snapshots (owner-only when signed-in or PoB, sealed on disk), public monitors showing a signed-in page, plain http (https only now), posting by any job (content only). Sealing is per AGENT, control is per WALLET: a key made only from a wallet adds nothing, addresses are public, and one from a wallet signature would stop agents working while you are away. Not done: an outside pen test. Terms text is a draft: have a lawyer read it. |
| PS01 | VERIFY | 🚀 Priority Setup (`agent_setup.py`, `SetupDeck.jsx`): 9-10 slides in Manual, auto-opened with a lit count on the Desktop buttons and the Manual icon. Use → email → sites by use → fund → limits → colony share (5-25%, signed; old 30% pays 25%) → posting → site trades → security → terms. Terms & security folder on every desktop. Seen on fixtures. Sign-in slide and colony signature not run live. |
| FD01 | VERIFY | 🧱 Folders measured in the harness: PoP 52→91%, Bids 64→93%, Jobs, Sources 14→94%, Mail 6→94%, Files 55→93%, Commands 19→93%, Wallet 2,141 px→847 px. Clickable vitals wall (`VitalsWall`), long boxes scroll inside themselves, cabinet drawers in a grid. Manual has a monitor beside each tab, its own data or marked EXAMPLE. Not seen on phone or day, or with a signed-in agent. |
| LP01 | VERIFY | 💡 Lamp rebuilt: bright tube, two cones, hot core. On while its windows work, a burst of static every 5, 23 and 45 s, a last burst then out when they finish. Seen on with fixtures; going out is tests only. |
| SR01 | OPEN · OWNER | 📚 Sources found, not wired: AgentMail (3 free inboxes per its docs, sturdier than mail.tm), Postiz / Blotato / Zernio / Ayrshare (post through official APIs), MoonPay Agents, Onramper. Each needs an owner account + key. |
| AG11 | OWNER | 🎨 Creations drawer works. `make an image of …` is built with fakes, but the one real call was refused: OpenRouter needs at least $1.00 in the account for image output. Top it up at openrouter.ai/credits, then it can be tested and added to the command list. |
| AG12 | VERIFY | The command list now differs: a trader is offered proofs, watch a wallet and free reads; a General agent is offered image, page and post, and the free reads. Either still does what it is told. Word-matching tests only. |

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

### Owner batch 2026-11-04, overnight

| ID | Status | Deliverable |
|---|---|---|
| PP01 | VERIFY | `file a perp` / `propose a perp`. Each mind reads 2 of 8 free sources, never its partner's or its own last ones, measured against the Coinbase chart (`pop_sources.py`), with its own sealed fingerprint (`{cat}:pop`). Real proposal: Deribit + Bitstamp vs dYdX + Coinpaprika, $0.008, one mind passed so nothing opened. Real chart, sources and fingerprint seen in the owner's browser. A trade or card has not appeared live yet. Sources are API reads, not browser windows. |
| MN01 | VERIFY | Desktop Manual folder (`AgentManual.jsx`): step-through tutorial, trader vs general board, drawn PoW / PoP / fingerprint flows, live limits, code map. Tutorial and board checked at 360 px day on fixtures, flows at 1280 px; the rest by tests. |

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
| C12 | OPEN | Alliances: create from a reply, ≤ 10 members; after X days (owner to set X) an alliance can found a FEELESS Union; all alliance + union info lives in Support. |
| FC06 | OWNER | Agents' EARLY calls (OSSY / G4; NEXA retired): call a coin while it falls toward the germ floor or just as it breaks out, not only at the floor. Real-money buy-rule change ⇒ edge-audit it first, owner approves. Today the desk models read a TEXT chart snapshot (`ai_snapshot.py`), never an image; OSSY (gpt-oss-20b) is text-only; G4 (Gemma, LAN) can take a chart IMAGE → add a rendered 1m chart PNG to G4's ask. OWNER 2026-10-30: YES — they need the image snapshot (add to the desk workflow). |
| P11 | OWNER | Lag 2026-10-30: reputation loop blocked 68 % of 24 min (Lag catcher) while the Mac swapped 13 of 14 GB (24 GB RAM: LM Studio gpt-oss-20b 12 GB generating, ChatGPT/Codex, two dev servers, 6 stale preview servers from old sessions on :51412 :51433 :51437 :51399 :51411 :51431). Fixed in code: `reap_orphans` off the loop. Owner: close what isn't needed / move OSSY to the LAN box. |
| LAG01 | VERIFY | Measured 2026-11-04, dev build, load 3–5: `reputation_service` idles at 5.8% CPU (was ~24%). 9 main pages over 25 s, headless Chrome, signed out: 60 fps, no long tasks (a planted 200 ms stall was caught, so the measure works). Not measured: signed-in desks and a real window. Tell me if a page still feels slow. |
| MAC01 | OWNER | Checked 2026-11-04: 210 GB disk free, swap 4.2 of 5.1 GB. Ours is small: rebuildable `frontend/node_modules/.cache` 1.8 GB, 3 worktrees 314 MB (nothing deleted). Left for you: Spotlight privacy for the project; the watcher keeps restarting LM Studio (3 times in 16 min this morning), likely the swap; `scripts/trim-mongo-caches.py` is untracked and not run. |
| OSSY01 | OPEN | OSSY prompt cost (NEXA retired) (~300 tokens a call): trim the system prompt + case text, cache static parts, measure tokens before/after. |
| SEC01 | OPEN · AFTER the owner buys his first general agent (owner 2026-10-30) | FULL SECURITY HARDENING, front to back: prove nothing in the frontend bundle reaches backend secrets (no keys/tokens in JS, every write endpoint signed + owner-checked, CORS/CSP/headers, rate limits, SSRF + path guards, dependency audit), confirm encryption at rest (Fernet vault, BROKER_SECRET_KEY rotation) and in transit (TLS). Add 3 free defensive services layered so an attack only gets slower with no sure outcome (e.g. Cloudflare free WAF + bot fight + rate limiting, Cloudflare Turnstile on sign-ups, GitHub Dependabot/CodeQL secret + code scanning) — defensive only, no counter-attacks. Report findings + fixes. |
| FC09 | VERIFY | Agents read one go-to list (`agent_mail.SOURCES`): own mailbox first, then Tuta / GMX, Catbox / Filebase, GitHub, Bluesky / Mastodon. Human checks stay human. Prompt and tests only; no real sign-up run. |
| FC11 | OPEN | Hive crawl engine (owner said GO 2026-10-31). OWNER: save X once in an agent's signed-in sites so traders can read X searches. |
| FC13 | OWNER | Dropbox: the app was made team-scoped; make a new Scoped access app and add the redirect `http://localhost:51367/api/cats/cloud/callback`. Pump.fun wallet launch stays your wallet's signature, never an agent's. |
| FC14 | OPEN + OWNER | Colony money, not built: sending payouts (approval flow + legal check), pool deposits, on-chain staking. Accruals and the ledger exist; nothing is sent. Your call whether to start. |
| FC15 | VERIFY + OPEN | 📧 Desktop › Mail: Make its email (mail.tm, password sealed), inbox as plain text, codes pulled out; agents read it with tool `inbox`. mail.tm's public domain list answered live; no mailbox was made because making accounts is the owner's click. Open: cheap clouds an owner can buy with crypto. |
| W05 | OWNER · BLOCKS PAID AGENT CALLS (checked 2026-11-04) | The FEELESS OpenRouter key can afford only 271 tokens (real 402). Add credit at openrouter.ai/settings/credits. Guards live: credit sales stop under $5 on OpenRouter (`cat_fund.credit_open`, `_openrouter_left`), the owner gets one alert a day, each agent stops at $0.10 of its own credit (`launch_cat.CREDIT_RESERVE`). FEELESS model credit is a ledger number and does not top up OpenRouter. Design gap: paid model credit lands in the FEELESS fee wallet, nothing moves it to OpenRouter. Then re-run the 2 + 2 test ask and the small real trade round trip. |
| W02 | OPEN · FIRST | ✅ 2026-10-30 part: a real RECOVERY PIN (`backend/cat_recovery.py`) rebinds an agent to a new browser, hash only, never moves money. A user-held signer below is still open. OWNER 2026-10-30: "FEELESS provides a TRUE SECURE encrypted generated key for each user (I keep the root key safe)". Today an agent wallet = Crossmint smart wallet, admin signer = our API key → NO user-held key exists (the old random 'recoveryKey' was fake and is removed; SafeKeeping tells the truth). Build: per-user signer the USER holds — options: Crossmint delegated / passkey signer on the smart wallet (no custody change), or Turnkey / Privy embedded wallets with export (user can export their key). Avoid FEELESS generating + storing raw private keys (custody, DECISIONS #2 counsel). Wire: create → user signer → export screen ("save it, only chance") + confirm box (built: SafeKeeping) → withdraw signed by it. |
| V01 | OWNER | Backdrops: ocean.mp4 is in (Mixkit 25163). Mixkit blocked the other 3 automated downloads → save by hand from mixkit.co (Download, 720p) into frontend/public/backdrops/: forest.mp4 = 25158, peaks.mp4 = 4396, aurora.mp4 = 4038 (see LICENSE.txt). Until then those scenes are drawn. |
| C13 | OWNER | "Circle wallet to FEE": confirm = a Circle developer wallet for Fee (the leader cat, creator-owned, like the Crossmint agent wallet) — needs a Circle API key; per-USER Circle accounts stay blocked on counsel (DECISIONS #2). |

### Build next — latest owner priorities

| ID | Status | Specific remaining work / done when |
|---|---|---|
| M01 | OWNER | Real device check on Safari and the Duo. Automated 2026-11-04: 20 pages at 360, 466, 678, 890, 1440 px: no sideways scroll, no crash, no dead route. Popups: 16 pages at 360 and 466 px, first 22 buttons each, writes blocked; fixed the shared dialog (taller than a phone) and the desk picker (clipped). |
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
| L01 | OPEN | AutoRange: Orca as third venue(ONLY USA ALLOWED), DLMM positions wider than 69 bins, compound LP fees; reconcile older tight-range/re-center requests against shipped Meteora/Raydium implementation. |
| P01 | OPEN | Perps: limit orders, owner fee controls, Coinbase Advanced door; additional venues only through approved eligibility flow. |
| B01 | OPEN | Brokers: Kraken/Coinbase own-key doors, YOUR MONEY totals, options; broker perps only when supported. |
| R01 | OPEN | RepMarket user sign-in/key and deposit flow; verify the permitted product/API before implementation. |
| K01 | OPEN | One user key vault in Familia. (The owner card shipped: HQ › Fees › Needs a human.) |
| A02 | OPEN | NSFA: at most five learning agents, ledger-based sizing/generation vitals; user Fuse dashboard with two charts, up to three agents and intake levels. Reconcile existing work first. |
| A03 | VERIFY | Same-coin shadow ledger and fresh edge audit; repeat after ~50 newer model trades; diagnose G4 uptime. No claim of profitable unseen performance. |
| A04 | OPEN | Cat learning/accept-loop parity with NEXA; G4 Models layout; trench theory only after shadow testing; launch-a-cat violet visual pass. |
| LA01 | OPEN | Launch: selected-venue configuration and any supported quote pair. (The coin/pools switch and Range Lab before signing shipped in LaunchModes.) |
| C02 | OPEN | Familia: live building P&L, real-money/MP errands, rank/badge pools, custom backdrops; drag within 3D block, new islands/bridges/lots/kiosks and saved family layout. |
| C03 | OPEN | Block readers: Meteora DLMM, marginfi, Save, PumpSwap LP, Phoenix; construction state when funds removed; opt-in member positions. Verify each against an actual account. |
| C04 | OPEN | Night Vault: DCA/limit orders, compound LP fees, retire old MP drag-errands/catalog; outer-city markets, held/launched coin buildings, in-city raids, MP buildings/ladders, MOBhouse and for-sale island. |
| C05 | OPEN | Leverage: complete position-row handling and one-transaction loops. Verify existing close flow with owner-authorized use. |
| C06 | OPEN | Provider fee configuration for perps/LP/run/leverage/launch; no invented referral fields. Zora execution needs a supported venue. |
| Q01 | OPEN | Measure city FPS, instancing/LOD and load tests; move remaining stores to a database and support multiple workers. |
| Q02 | OPEN | Split `reputation_service` safely (the supervisor part shipped: `start-backend.sh` starts the watcher). |
| Q03 | OPEN | Whitepaper done (9,855 → 2,603 px). Familia side wall trimmed. Trench report posts cut to a one-line header plus short rows (code only, not seen live; the next post shows it). Still to do: FeeCat stage/tabs and perf, lore/launch flows, 3D roadmap, faster model reads. HQ and Familia still need a signed-in measure. |
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
- Stronger agents (2026-11-04): each mind keeps a track record per topic, and the next proof goes to the mind that is best at it. Colony-wide loss shapes: an agent that shares its winnings also gets the fingerprints other agents lost on. Size only by a mind's record on unseen coins, and only ever down. A weekly self-review that drops the sources and steps that did not pay.

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
| Q23 | OPEN | Price-gap engine: a live drawn view before buying, then the buyer's own running engine. Ships with buy guards. |
| Q25 | OWNER | Charts-first is live on Fee's and trader desks. No cat shows on a profile today, so "FeeCat on a profile is a pop-out" needs your reference: which profile, and what you tap. |
| Q29 | OWNER | HQ › Fees showed the swap fee at 1500 bps (15%) on 2026-10-29: confirm that is intended. |
| CH05 | OWNER | Move agents and the real card onto true candles after a shadow test. They still read filled bars. |

**Standing rules:** US users only reach venues allowed for them. The user's wallet signs real money; FEELESS holds no keys or pooled funds. Every new buy door ships with guards. Touching a page means its whole flow. Money surfaces lead with the aggressive play and name the risk.

**Lawyer first:** a perps partner API, on-chain cat or pot programs, do-anything agents, real volume (`docs/COUNSEL_BRIEF.md`).
