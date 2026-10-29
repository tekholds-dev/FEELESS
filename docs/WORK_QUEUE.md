# FEELESS — one work queue

Updated 2026-10-29. This is the canonical task list. Read HANDOFF for the latest result, this file for priorities, and MOBILE_LAYOUT for device rules. Conserve usage; finish the selected scope by priority; never dead-style. Do not work through this entire backlog unless asked.

Status: **OPEN** = work requested; **VERIFY** = implemented claims need evidence or older docs conflict; **OWNER** = key, account, signature, decision or real-device check; **LATER** = unapproved idea / audit-dependent work. No item here authorizes a trade or a payment.

## Current delivery

- Agents Duo viewport/layout refinement: full-height landscape chart, portrait chart/dock, safe-area padding, Safari visual viewport tracking, preserved navigation through HQ controls, independently scrolling desk. All five dock tabs remain.
- Desktop and ordinary folded portrait retain their normal cockpit. Shared Trench Trade and trading logic are unchanged.
- OWNER: verify on the physical Duo in Safari, with browser chrome shown/hidden, fullscreen/home-screen mode, rotation and keyboard. Desktop viewport checks cannot certify physical Safari behavior.
- Device rules and exact supplied sizes: [MOBILE_LAYOUT.md](MOBILE_LAYOUT.md).

## Real card auto-halt — 2026-10-29

DONE + live: a gas-sized SOL gap (reserve ran dry) no longer halts the real card; booked as card fees (P&L unchanged). OWNER: top up ~0.02 SOL gas to the Fuse wallet.

## Focused HQ fixes — 2026-10-28

Three bounded H01 fixes: placeholder legs no longer hide Fill seat (pending buys still reserve capacity); RoadMeter handles partial snapshots and clamps progress; failed Agents stream reads always release the watchdog timer. Includes the earlier paused-buy status correction. Broader H01 and A01 remain OPEN. Validation: all three focused HQ regressions passed; shared-intake backend 12 passed; LiveTank 4 passed after fixing the header. Broad run: backend 2,265 passed/26 skipped; frontend 1,640 passed/1 failed (the intake header, corrected and rechecked). Production build pending. No browser/real-device verification this session. No trades or wallet settings changed. Shared-intake follow-up: source-order deduped discovery snapshot now feeds the visible tank and then the agents; verdicts are attached after discovery. Existing agent eligibility, bounded review scheduling and execution checks remain. Removed three redundant browser feed polls. Backend restart/deployment remains required to expose the new snapshot; do not claim it is live until checked.

Conserve usage · finish the selected work by priority · never dead-style.

## 🌙 OVERNIGHT LIST 2026-10-29 — the 15 easiest (self-contained: no keys, no trades, no signatures, no real-money rule changes)
Each loop iteration: ① cash check (card books vs wallet, halt, pending) → ② the next OPEN item → finish it styled + tested + pushed (gate green) →
③ mark it DONE here with one line of proof. Never loosen buy rules, never move funds, never restart reputation_service with an order pending.
| ID | Status | Task |
|---|---|---|
| E00 | DONE | Creator-only 🪟 NEXA tab in HQ › Agents (desktop deck, lazy) + its own NEXA dock tab on the Duo floor = FeeCatDesk (Fee's book, record, creator wallet bar, NEXA's desk). Harness 890×626 ✓, tests ✓. |
| E01 | DONE | Edge audit run 2026-10-29: agents entered 0/3,000 calls; 12 rules positive on unseen coins (best 5m +5–15% & buyers ≥65%: +19.4%, n 63) → HANDOFF top. |
| E02 | DONE | Sweep 2026-10-29: Home · Trenches · FEEd · Pump radar · Radar at 360 / 466 / 890 → page width = viewport on all, 0 overflowing elements. |
| E03 | VERIFY | (sweep 2026-10-29: no page side-scroll at 360 / 890 — clipped-control review still to do) |
| E04 | VERIFY | (sweep 2026-10-29: no page side-scroll at 360 / 890 — clipped-control review still to do) |
| E05 | VERIFY | (sweep 2026-10-29: no page side-scroll at 360 / 890 — clipped-control review still to do) |
| E06 | VERIFY | (sweep 2026-10-29: no page side-scroll at 360 / 890 — clipped-control review still to do) |
| E07 | VERIFY | (sweep 2026-10-29: no page side-scroll at 360 / 890 — clipped-control review still to do) |
| E08 | DONE | Agents floor rail seats show each coin's image (useLiveTokenMarkets, one batched read, only while the floor is open; letters as fallback). Tests ✓. |
| E09 | OPEN | Trade tape on the Trenches floor gets the per-trade stream (a new fill appears without waiting for the 15 s tape read). |
| E10 | OPEN | Settings › Look: an "ECO ON · this phone stays cool" chip with what eco changes. |
| E11 | OPEN | HQ Numbers / Traffic: hide '—' rows when every value is missing (one "no data yet" line instead). |
| E12 | OPEN | HQ Lag catcher: show the page-watcher's latest layout issues as a short live list. |
| E13 | OPEN | FEEd: the FEELESS chip shows FEELESS posts on the same timeline (rooms stay one tap away). |
| E14 | OPEN | CSS budgets: lower `terminal.css`'s KB budget to its new size after the deletions (cssHygiene). |
| E15 | OPEN | MOBILE_LAYOUT matrix: record which pages passed the Duo-floor contract (proof = sizes checked). |

## Owner requests 2026-10-29 (late) — NEXT, in this order
1. **A06 Agents PICK from the one intake** (owner: "sort through the new intake to PICK a coin, not block coins on the intake"; "they act scared to enter"):
   OSSY / G4 + agents read the NSFA 1 / 5 / 15-min survival + enter at the germ floor on a CONFIRMED coin; drop the "ten agents" desk; AI prompts get research
   to write better winning prompts. Real-money buying ⇒ run `scripts/edge-audit.py` first and keep the buy guards (memory: big-picture-before-features, new-buy-doors-need-guards).
2. **FC01 FeeCat two-option build** — option 1 TRADING cat (≤ 2 models, trench / perps on FEELESS only, like familiars.family); option 2 GENERAL cat (≤ 2 models working
   together in a personal wallet-brain chat: research, crawl sites, Polymarket etc. via user sign-ins, a small browser window showing what it does). Each user can hold up to
   3 cats; the owner's cat (NEXA) shows on the wallet's public FeeCat tab; a pop-out to watch the trading or assistant cat. ⚠ OWNER DECISION before code: option 2 creates a
   wallet + one-time recovery phrase = CUSTODY (DECISIONS #2 is option A "your wallet signs"; counsel). Fee per top-up shown up front.
3. **L02 Price-gap boost** (lootcollector.online idea): detect price gaps across pools/venues as an add-on to AutoCompound / pools / Night Vault to speed up daily earnings.
4. **M02 Every page fits every device** (mobile / fold / desktop) against `MOBILE_LAYOUT.md › Duo floors`; no dead styles, no bulky one-off CSS.
⚠ OWNER: HQ › Fees shows the swap fee at **1500 bps (15 %)** — confirm intended (the cat funding receipt reads it live).

## Build next — latest owner priorities

| ID | Status | Specific remaining work / done when |
|---|---|---|
| M01 | VERIFY | 2026-10-29: phone eco (no overheating), site-wide sticky fix, Agents floor on Duo/fold/phone (MOBILE_LAYOUT › Duo floors). Still to sweep against the contract: Fuse, Launch, Radar, FeeCat, Familia, Perps pages + modals. OWNER: physical Safari. |
| F01 | VERIFY | FEEd v5 shipped 2026-10-29 (`FeedX.jsx`, `feed.css`, `feedPro.css`): 600px column, sticky glass header (For you/Following/Calls/Heat/Graveyard + 🔖, sliding underline), swipe source chips, composer with live CA coin card, ↑N new pill, post cards with live coin chip (→ Trenches floor) + call receipt, threads on a connector line, rail (search · pulse · trending · callers · who to follow · sites), mini-nav ≥1250, phone ✎ sheet + folding header, Duo split. Browser-checked desktop/360/Duo-wide/day/pop-out. Remaining: owner look on real phone/Duo; coin chips/receipts only seen via the composer (no coin posts in the live feed today). |
| G01 | OPEN | Strike Zone: real CC0 gun models and camo/PBR assets; replace placeholders, preserve gameplay. |
| T01 | OPEN | HQ Telegram center: bot rooms, alerts/trading/community/security, Mini App setup; FeeCat-art idle RPG and slot game hub. |
| C01 | OPEN | Familia desktop/mobile pass using shared room, vitals, panel and sheet templates. Every building opens a real function with live vitals. |
| A01 | OPEN | Fix-agent: Lag catcher + Support issue → investigation → branch fix → before/after visual preview → owner review. |
| D01 | OWNER | Public hosting, domain, HTTPS, production configuration and provider keys. Validate deployed endpoints. |
| H01 | OPEN | DONE 2026-10-29: fixture-backed deck harness (`/dev/hq?deck=<tab>` — whole HQ, fake session, empty admin reads); missing-data handling (16 of 32 tabs crashed HQ on an empty reply → every read goes through `lib/shape.shaped`, `HqDeckMissing.test.jsx` mounts all 32 tabs on `{}`); per-tab `TabGuard` (a crash shows a Retry card, HQ keeps working); Fuse overview concise (1.9 → 1.4 screens). OPEN: unread folding + '—' cells + ≤1 screen per tab need the owner's screenshots / live data to target; "Fuse family view renders oddly" not reproduced on fixtures. |

## Product and engineering backlog

| ID | Status | Specific remaining work |
|---|---|---|
| L01 | OPEN | AutoRange: Orca as third venue, DLMM positions wider than 69 bins, compound LP fees; reconcile older tight-range/re-center requests against shipped Meteora/Raydium implementation. |
| P01 | OPEN | Perps: limit orders, owner fee controls, Coinbase Advanced door; additional venues only through approved eligibility flow. |
| B01 | OPEN | Brokers: Kraken/Coinbase own-key doors, YOUR MONEY totals, options; broker perps only when supported. |
| R01 | OPEN | RepMarket user sign-in/key and deposit flow; verify the permitted product/API before implementation. |
| K01 | OPEN | One user key vault in Familia; one owner provider-readiness card in HQ Core. |
| A02 | OPEN | NSFA: at most five learning agents, ledger-based sizing/generation vitals; user Fuse dashboard with two charts, up to three agents and intake levels. Reconcile existing work first. |
| A03 | VERIFY | Same-coin shadow ledger and fresh edge audit; repeat after ~50 newer model trades; diagnose G4 uptime. No claim of profitable unseen performance. |
| A04 | OPEN | Cat learning/accept-loop parity with NEXA; G4 Models layout; trench theory only after shadow testing; launch-a-cat violet visual pass. |
| A05 | VERIFY | Fresh Pump intake coverage, especially 0–15 minute coins. |
| LA01 | OPEN | Launch: coin-first flow plus pools switch, Range Lab before signing, selected-venue configuration and arbitrary supported quote pairing. |
| C02 | OPEN | Familia: live building P&L, real-money/MP errands, rank/badge pools, custom backdrops; drag within 3D block, new islands/bridges/lots/kiosks and saved family layout. |
| C03 | OPEN | Block readers: Meteora DLMM, marginfi, Save, PumpSwap LP, Phoenix; construction state when funds removed; opt-in member positions. Verify each against an actual account. |
| C04 | OPEN | Night Vault: DCA/limit orders, compound LP fees, retire old MP drag-errands/catalog; outer-city markets, held/launched coin buildings, in-city raids, MP buildings/ladders, MOBhouse and for-sale island. |
| C05 | OPEN | Leverage: complete position-row handling and one-transaction loops. Verify existing close flow with owner-authorized use. |
| C06 | OPEN | Provider fee configuration for perps/LP/run/leverage/launch; no invented referral fields. Zora execution needs a supported venue. |
| Q01 | OPEN | Measure city FPS, instancing/LOD and load tests; move remaining stores to a database and support multiple workers. |
| Q02 | OPEN | One service supervisor; split reputation_service safely; retained guards against name collisions and data mutation in tests. |
| Q03 | OPEN | Site-wide text-wall/visual pass, FeeCat stage/tabs and perf, lore/launch flows, 3D roadmap/whitepaper; faster model reads. |
| Q04 | OPEN | Fee-Back eligibility, valuation/reference timestamp, settlement, rounding/distribution policy and audited payouts. Treasury buy/burn executor. |
| Q05 | VERIFY | Broader chain/indexer coverage, independent risk signals and moderation/identity claims from the old PRD; validate against newer implementation before rebuilding. |
| Q06 | OPEN | Feature-level geo/KYC switches guided by the existing decisions and counsel. |
| Q07 | VERIFY | Final site-wide click-through only after the relevant builds: day/night, 360px, lite/reduced motion, every step and empty state. |

## Owner prerequisites and verification

- Physical Safari/Duo review (M01); first funded wallet-signing checks belong to the owner.
- AutoRange $25 open/re-center/close; Jupiter perps open with TP/SL, partial close and TP move; broker paper key then authorized real link; Kalshi production metadata/order check; $5 bridge round trip and $2 gas fill; leverage open/close; first $5 Run deposit; FeeCat signed proposal. These are recorded requests, not actions performed in this session.
- X client ID/secret and callback domain; public site URL; launch-rule signature; DFlow, SnapTrade and LaunchLab provider keys; Telegram token/group/Mini App URL; Crypto.com Exchange keys; sufficient RPC quota and additional Jupiter read key.
- Contract path: week-long devnet soak with keeper host, external audit, upgrade-authority decision, capped mainnet deployment and launch settings. GO_LIVE is a technical checklist, not evidence these steps passed.
- Counsel review of custody/sign-once agents, legal venue eligibility, on-chain cat/pot programs and real-volume readiness. Preserve the current wallet-signing model until approved changes.
- Clarify older owner questions: remaining Fuse bug reproduction, Fee City fullscreen preference, Desktop-cleanup folder scope.

## Ideas — not approved implementation

Ticket-sized manual picks while record is red; automatic initial-out on winners; 30-minute hand-pick acknowledgement; fed/trending overlap; proven smart-wallet follow; FeeCat + agent pair conversations; better-coin track. Never remove Pump/New-launch tabs based on these old suggestions without a fresh request.

## Conflicts resolved for planning

- Older HANDOFF/CLAUDE statements that “everything is built” conflict with their own open lists. They are not a completion certificate.
- Duo per-tab implementations and the page watcher were subsequently committed. Treat them as mobile verification work, not wholly unbuilt features. Agents still needed this refinement.
- FAMILIA_PLAN is an older specification, not a claim the entire current city is unbuilt. Preserve its detailed requirements; verify gaps against code/history.
- Old PRD claims about unauthenticated chat/local-only features may be stale. Q05 is verification before new work.
- Circle/house-wallet notes differ across REQUIREMENTS, GO_LIVE and DECISIONS. Reconcile owner-only operation versus user custody before implementing; a cap setting alone does not resolve that distinction.

## Source map

CLAUDE's former CURRENT TASKS is preserved below for exact wording and the detailed FEEd specification. Supporting specs remain in HANDOFF, REQUIREMENTS, PERPS, BROKERS, GO_LIVE, FAMILIA_PLAN, REAL_CATS, DECISIONS, COUNSEL_BRIEF, DEGEN_PLAYBOOK, TELEGRAM, memory/PRD. FEELESS_HISTORY is evidence of older work, not a second active queue. Technical architecture/runbooks and .agents memory remain reference material. Update statuses here rather than copying another task list into those files.

<details>
<summary>Original owner request ledger (archived wording; statuses above take precedence)</summary>

## 📋 CURRENT TASKS — OPEN ONLY, priority order (rewrite every session; a finished item leaves this list → one line in
`docs/FEELESS_HISTORY.md`. Everything done up to 2026-10-23 is archived there: grep "📦 TASK LIST 2026-10-23")
Rules for all: research the best web3 / degen sites first, then a FEELESS twist · every page complete top to bottom · real money = the wallet
signs, FEELESS never holds keys · conserve usage · finish by priority · never dead-style.

STANDING RULES (never "done"):
- 🇺🇸 US users: no geo-block loopholes, ever — route them only to venues + in-app deposits allowed for them (the owner's legal exposure).
- Real money = the user's wallet signs; FEELESS never holds keys or pooled funds (`docs/DECISIONS.md`). Every new buy door ships with guards.
- Every building / family idea = a real function on live data, drawn and alive — no dead text.

- 🧹 EVERY PAGE END TO END (owner, 2026-10-23): touching a page = its WHOLE flow (modals, steps, pop-outs, second tabs, empty states) in that
  page's own meta, old bits deleted, tested, screenshotted. Narrow side panels = a summary + ONE button; big tools pop out over the page.
- 🚀 NO RISK NO REWARD (owner): money surfaces lead with the aggressive play (MOON: tight v3 / DLMM bands on the busiest pools; DEGEN: the
  hottest fee pools) with the risk named — SAFE yields are one tap away, never the headline. "Think big, not the same utilities."

P0 — OWNER 2026-10-28 (the "addicted on every tab" list), easiest → hardest. SHIPPED 2026-10-28: SOL fee account self-heal (trades from any
wallet), risk scale 1–4, NSFA 1/5/15 survival watch, OSSY × G4 beside the chart, creator owns every Strike Zone gun, no-spill CSS defaults.
1. 📱📱 DUO / FOLD per tab — SHIPPED 2026-10-28 (Trenches · Pump radar · HQ Agents · Familia · Perps · FEEd; `DuoFloor mode`, `lib/duo.useDuoFloor`,
   `duo.css`). NEXT: Fuse, Launch, Radar, FeeCat the same way once FEEd is redesigned.
2. 📰 FEEd redesign — NEXT (spec ready 2026-10-28, nothing built yet). Today: `FeedX.jsx` (375 lines: FeedPanel on the profile's FEEd tab,
   FeedPopHost pop-out, Timeline / Post / Thread / Composer / FeedPulse / FeedTopCoins) + `feed.css` (223) + `feedPro.css` (68). Owner: "doesn't
   look like a feed, not lively". Build: ONE center column (max ~600 px) with a sticky header = tabs (For you · Following · Calls · 🔥 Heat ·
   Graveyard) + the source chips as ONE swipe row; composer on top (avatar · text · CA paste → live coin card preview); a "↑ N new posts" pill
   that slides in (newSince) instead of jumping the list; post card = avatar · name · rep badge · source · time, text, media / X embed, a
   live COIN CHIP (price + 5m, tap = Trenches floor via openTrenchTrade), a call RECEIPT bar (2× / 5× / 10× since the post), action row with
   animated counts (reply · repost · like · share), threads with the connector line; right rail (desktop) = search, trending coins (live),
   top callers, who to follow; a left mini-nav only ≥ 1250 px. Phone: header collapses on scroll, FAB composer. Duo: timeline | rail at the
   crease (feedPro.css already locks the pop-out). Delete the old fx-* rules the new layout drops (cssHygiene), one keyframe set (fx*),
   fx-lite / reduced motion / day theme / 640 px. Tests: FeedX.test.jsx (tabPosts, newSince, kWord, feedPulse stay).
3. 🎯 Strike Zone real art: CC0 gun models (Quaternius guns, Kenney Blaster Kit) + CC0 camo / PBR textures (ambientCG, Poly Haven) — skins = camos.
4. 📲 HQ › TELEGRAM CENTER: create + run bot rooms (sniper alerts · trading · member fun · security), Mini App setup in one card, and the FEELESS
   game hub — an idle RPG (Capybara-Go-like loop) + a Boinkers-style slot, built on the REAL FeeCat art, owner controls all of it in one place.
5. 🏙 FAMILIA desktop + mobile pass + PRESET TEMPLATES (one room / vitals / panel / sheet template set, rooms built from it — fewer one-off sheets).
6. 🛠 FIX-AGENT: Lag catcher + Support errors → a model investigates, fixes on a branch, and shows a BEFORE / AFTER visual preview (screenshots /
   a live preview window), the owner approves — never just a diff.
7. 🚀 DEPLOY: a public host + domain + the 🔑 keys (HANDOFF table). Render plugin needs /mcp sign-in.

P0 — OWNER-ONLY (2026-10-26 final): everything the owner asked is built; the open items need a human key / sign-up / signature — `docs/HANDOFF.md` › 🔑 table.
P0 — OWNER 2026-10-26 (the "finish it" list; shipped this day → history "2026-10-26") — open, priority order:
a. 🤖 AUTORANGE: real opens / re-centers / closes SHIPPED 2026-10-26 (all four simulated clean on mainnet) — NEXT: the owner's first real $25 open +
   re-center read back · Orca Whirlpool as a 3rd venue · DLMM bands wider than 69 bins (extended positions). ⚖ OWNER DECISION: "sign once, the AIs
   trade" = custody (DECISIONS #2 rejected B) — needs the owner + a lawyer; until then cats propose, the wallet signs.
   FeeCat page: lag fixed (chat window 40 + shared slow clock) — NEXT: the stage + her tabs as live visuals, measure again with /perf. 📉 PERPS: the owner's first real Jupiter open after the 250× / pay-with / landing-card fix (read the LANDED card + positions) · Coinbase Advanced
   (US perp-style futures, CDP JWT keys) as a 3rd key door · Kalshi still waits on `DFLOW_API_KEY`.
b. 🗳 REPMARKET ← Polymarket: one-time sign-in / API key per user (Polymarket US is the US-legal door — check its API first), USD in, saved per user.
c. 🔑 ONE KEY VAULT: users = one Familia spot for every key (Alpaca · Crypto.com · Polymarket · DFlow proof) · owner = HQ › Core "needs a human"
   list (DFlow, SnapTrade, RPC quota, Jupiter key 4) in one card.
d. 🧠 NSFA agents: ≤ 5 real agents that learn per coin from the ledger's faults (owner's + the 3 AIs'), size by what went wrong before, never
   ban — retune; live "generation" vitals on the agents tab · user FUSE DASHBOARD (half of HQ Agents: 2 charts, up to 3 agents, intake tank levels).
e. 🚀 LAUNCH: coin first + a POOLS switch (Range Lab before signing), pair with any coin (SOL / FEELESS first), pick platforms (Pump · Raydium) then
   their real configs — no dropdown walls.
f. 🏙 FAMILIA: glass live P&L on any building holding a coin / perp · Trench towers = live vitals · errands = real money + MP game (raids by MP or
   family cash) · MP / points from every real-money $ → rank + badge pools · other families' backdrops (big holders upload).
g. 🖥 HQ: every tab like Agents (fewer tabs up front · hide '—' cells · fold unread; needs a fixture-backed `/dev/hq?deck=` harness) · Fuse tab de-cluttered · fee tab = every real-money fee (swap · trench · perps · pools · launch) set by the owner · Fuse family view at
   the page bottom renders oddly (owner screenshot) · every HQ tab ≤ 1 screen.
h. 📱 Trenches + Pump radar mobile flow redo (one-thumb). Duo FLOOR shipped 2026-10-27 (DuoFloor.jsx) — NEXT: Perps desk + Pump radar as Duo split apps the same way.
i. ✅ the full click-through (P0 #6 below) + a page watcher (overflow / overlap detector in the Lag catcher).

P0 — OWNER 2026-10-23 (late night) · finished today → `docs/FEELESS_HISTORY.md` (grep "2026-10-23 late night")
0. 🔥📉 PERPS / OPTIONS — ONE PAGE: `docs/PERPS.md` (venues truth, the desk, endpoints, guards, tests, open items). Owner 2026-10-23: "all
   mechanics a real perps desk has, only realtime vitals, true chart data ALWAYS, live TP / SL before the trade on the chart, from $1".
   SHIPPED late night: the FEELESS PERPS terminal (true Coinbase candles + live prints, draggable TP / SL, Jupiter oracle + basis, spread, borrow,
   crowding; TP / SL ride the open; positions with live P&L, TP / SL move / cancel / add, close 25–100 %) + the Kalshi (US-legal, $1) trade path.
   US venue truth (re-checked): gTrade (incl. Solana) / Aster / Hyperliquid / Drift bar US persons in their terms — owner asked "any chain,
   500× with $1"; DECISION PENDING: wire gTrade behind a non-US attestation (default) or lift the rule (DECISIONS #9). + 🌊 LIVE FLOW shipped. NEXT: ① 🔑 OWNER: DFlow production key → `DFLOW_API_KEY` (Kalshi trading
   turns on) · ② first real Jupiter open with TP / SL + a 50 % close · ③ limit orders · ④ the owner's fee on opens (`*-with-fee`, HQ › Core).
   Also open from this ask: pools make visual sense from any $ typed · every Familia money surface relevant + vitals.
0a. 🏦 THE BROKERAGE (owner 2026-10-24, DECISIONS #9, `docs/BROKERS.md`): your own broker (Webull · Coinbase · Kraken · Alpaca · E*TRADE via
   SnapTrade) linked to the Familia wallet — live accounts + positions, BUY / SELL stocks · ETFs · crypto from $1. LIVE for every user TODAY via
   their own FREE Alpaca keys (BYOK, $0 to start, no owner setup); "any broker" still waits on the owner's SnapTrade keys. NEXT: a real PAPER
   key end to end; Kraken / Coinbase own-key doors the same way. Familia is NOT "done": every item below stays open.
0b. ⛽🌉 GAS + BRIDGE — SHIPPED 2026-10-23 (grep the history "🌉 BRIDGE"; `lifi.verify_svm`, `lib/bridgeExec.js`, `BridgeDesk.jsx`, /dev/bridge ·
   /dev/gas). NEXT: the owner's first real bridge ($5 USDC Solana → Base and back) + a $2 gas fill read back on its tank · Zora coins: LI.FI dropped
   Zora, so EVM swaps on Zora coins fail too (no Zora venue yet) · 💰 the owner sets their own fee on every Familia money action (perps, LP joins,
   $5 run, leverage) from HQ › Core — check each provider's referral / fee field first (Jupiter swap fee already rides on the route) · 📊 the START
   COMPOUNDING desk = vitals, not row walls.
1. ⚡ REAL LEVERAGE — SHIPPED 2026-10-23 (Coinbase / Kraken API orders dropped: "too many steps"): Jupiter Lend Borrow from the user's own
   wallet (DECISIONS #7, `lend_borrow.py`, `RealLeverage.jsx` in the Perps desk + MoneyDesk MOON). Open SIMULATED clean on mainnet through
   FEELESS. NEXT: the owner's first real open ($25 SOL 1.5×) + close end to end (close = sell to repay → repay-all/withdraw-all, built but
   never landed) · read Jupiter's `/borrow/positions` row shape off that first position (`lend_borrow.positions` keeps only vaultId + nftId
   today) · one-tap loops to 3–4× via Jupiter's flashloan (`@jup-ag/lend/flashloan`: borrow → swap → operate → payback in ONE tx).
2. 💵 FEE REAL: the 👛 FEE'S WALLET pill (stage + HQ) is where to link / budget / go real — owner signs one small proposal end to end, report.
3. 🏝 Town next: ✋ ARRANGE now drags lots + 🏗 BUILD HERE on a picked open lot (shipped 2026-10-23) · NEXT: drag inside the 3D block itself ·
   each town building's real tool done in place. Islands cost 3,000 MP (creator free) — tune with the owner.
4. 💵 THE $5 RUN (shipped 2026-10-23, `FiveRun.jsx` in the Night Vault · GET /familia-pools/run): NEXT = the owner's first $5 deposit lands and
   the ticker reads it · a real "compound my LP fees" errand (claim → put into the run) · retire the MP drag errands UI (P2 #2) — NEXT MOVE + EARN
   already point at the run.
5. 💸 EVERY FAMILIA REAL-MONEY BUILDING (owner 2026-10-24, screenshots: "not a damn popout… no real money live animation vitals"): a click = a clean
   summary + ONE button that pops the big window; every room shows live ticking vitals, no row walls. DONE 2026-10-24: pool + market buildings
   (lend / stake / perps / DEX / coin: vitals + $100 ticker + ONE button), Pool Hall combo, Night Vault picks, MY POOLS + YOUR MONEY earning
   tickers (`EarnTicker`), Trade Center flash. NEXT: screenshot-verify the market panel + YOUR MONEY with a real wallet; the money desk itself.
   📊 Every page end to end: text walls → visuals (HQ Agents + FeeCat tabs first); 80 % ACTIVE money = `cityPlan.activeMoney` (keep ≥ 0.8
   in `cityPlan.test.js`; outer cities next).
6. ✅ LAST, ONLY WHEN EVERY ITEM ABOVE AND BELOW IS DONE (owner, 2026-10-23): click through EVERY tab / page / pop-out / modal / step of the
   site (day + night, 360 px, fx-lite) — nothing unreadable, nothing unwired, every button does its thing; fix what fails; screenshot proof.

 (owner 2026-10-23: "I tightened a v3 pool with $100 and made $120 — no redirects"), hardest → easiest
1. 🔌 IN-PLACE LP — SHIPPED 2026-10-23: join (`lib/lpBuilder.js`), one-tap ZAP (swap half via the FEELESS engine `lib/swapEngine.js` → join),
   YOUR POSITIONS live (`lib/lpPositions.js`: worth now, unclaimed fees, in range) as towers on your family block + in the money desk, with
   claim / remove / close in place (`components/LpPositions.jsx`) — join, claim, remove, close each SIMULATED clean on mainnet for real
   wallets. NEXT: Raydium CLMM + Orca Whirlpool + Meteora DLMM TIGHT ranges (install their SDKs; simulate each the same way) · re-center when
   out of range · auto-compound (claim → re-join) as a Night Vault errand.
3. 🏝 FAMILY TOWN EXPANDS: more islands joined by bridges, pick your own lots, MOVE buildings, add little stands (kiosks / food stalls / signs),
   a "MY POOLS" combo building (every LP / stake / lend position together, live) — the layout stored server-side per family.
4. 🏦 BLOCK READERS (DECISIONS #5: each checked against a real on-chain account): Meteora DLMM · marginfi · Save · PumpSwap LP · Phoenix
   (`block_markets.WHY_NONE`). Then: a building assigned to a position goes under construction when its balance is pulled · members' wallets
   on the block (opt-in). (Orca / Raydium range reads + re-center errands: `clmm_range.py`.)
5. 💤 NIGHT VAULT DCA / LIMIT ORDERS: Jupiter Recurring + Trigger (build → verify like `lend_earn.verify` → wallet signs; allowlist + guards).
6. ⚡ SCALE FOR THOUSANDS: measure the metro's fps (trims merged + a car budget shipped 2026-10-23, unmeasured) · instancing / LOD · load tests.
7. 🏙 CITY LEFTOVERS: outer cities' real-money markets · HELD + FEELESS-launched coins as buildings · raids played in-city · MP-only buildings ·
   $ / MP ladders · MOBhouse customization · a 3D for-sale island.
0. 🚨 RPC QUOTA: the relay answered again late 2026-10-23 (getLatestBlockhash + simulate OK) but Helius ("max usage reached") AND Alchemy ("Monthly capacity limit exceeded") were both out on 2026-10-23 evening — every
   wallet-signed action through `/api/reputation/rpc` (swaps, Jupiter Lend, LP joins, launches) and maybe the keeper depend on them. Owner: top up
   / upgrade one, or add a third RPC to the relay's fallback list.
9. 🔑 Jupiter keys: the READ key (+ key 2) sat at their rate limit (429) on 2026-10-23 — Lend builds fall through every key
   (`jup_keys.lend_keys`) and the agents' intake now falls back to DexScreener (it had starved to 5 rows / pass); the owner adds a 4th key
   (portal.jup.ag → `JUPITER_READ_KEY`) so charts / prices stop starving too.
8. 🌍 A geo / KYC switch per feature (today there is none — COUNSEL_BRIEF §0) so a feature counsel restricts can be closed to US users.

P1 — AGENTS + AI
1. 🏆 NEXA auto-trading real money (no per-trade signature) only after a SAME-COIN shadow ledger shows her beating the rules after a 3% round trip.
   ⚔ The duel meter on her desk (`CatBrainSwitch.duel`, YES-right vs closed-trade wins) is the first cut. 2026-10-23: NEXA 43% · −1.55% typical; edge-audit GATE HOLD.
   OSSY / G4 audit 2026-10-23: 179 closed trades 23 % win, Σ −358 % — bad entries are the leak (grep history "MODELS AUDIT"); PARABOLIC + far-from-germ
   spikes now refused. NEXT: re-run the audit after ~50 new model trades; G4 "did not answer" often (desktop LM Studio) — check its uptime.
2a. 🧠 Learning / accept loops of the cats on par with NEXA's desk (owner ask 2026-10-23, not started: audit `feecat_brain` learn + `_learn` vs nexa.py grading).
2. 🧠 G4: the Models tab beside NEXA's chat (layout) · wire the trench theory into the deterministic agents only after a shadow test.
3. 🔥 More Pump coins on the intake (revived 2026-10-23 late night: 24 unique mints/min, 66 rows/pass) — next: watch the 0–15 m fresh bucket fill.
4. 🐱 Launch-a-cat AI flow restyled in the violet meta (like CatDesk / CatReal).

P2 — CLEAN-UP (the 2026-10-22 cut list; owner's go 2026-10-23: "do all decisions")
2. ✂ family_world's drag-the-pizza ERRANDS UI (MobHome / FamilyWorld) + the MP store build catalog → retired for the block's real errands.
3. ✂ 4 ways to start services (run-feeless.sh / start-backend.sh / background.sh / keep-alive) → ONE supervisor.
4. ✂ Split `reputation_service.py` (31K lines; `tests/test_no_name_collisions.py` guards new helpers meanwhile).

P3 — PAGES + HQ BELOW THE BAR
1. 📊 Text walls → live visuals (meters, rings, ticking numbers) + dead styles out on every page — HQ's Agents + FeeCat tabs first.
2. Launch click-through pages · FeeCat lore + its other tabs · Roadmap / whitepaper as a 3D view · OSSY / G4 duo chats · NEXA reads + trades
   fast (no 40 s waits on the i5).
3. HQ: Lag catcher + Support clean-up · vault / pool pair builder live visual · Agents rebuild only after `scripts/edge-audit.py` numbers.

LATER — a lawyer / audit first (`docs/DECISIONS.md`): a perps venue's official partner API (OAuth on the user's own account) · real cats
option C (an on-chain cat program) · do-anything agents · an on-chain pot program (family pot / top-pot Fuse).

WAITING ON THE OWNER
- 🐛 Fuse card bug: is the fix found in code the bug you saw? (if not: repro steps first)
- ❓ Fee City full-screen by default?
- 🗂 Desktop clean-up: which folders (never images)?
- ⚖ A lawyer's read of `docs/DECISIONS.md` before real volume — hand them `docs/COUNSEL_BRIEF.md` (the questions, the facts they'll ask for).

IDEAS: FeeCat + AI agent pair that talk · "build a better coin" track in Lag catcher.

NOTE: merging into main LOCALLY never restarts the backend — after a backend push, restart reputation_service via the watcher
(memory: restart-from-claude-tree).

</details>

## Delivery validation — 2026-10-28

Frontend: 345 suites / 1,637 tests passed; final targeted checks: 243 passed. Backend: 2,265 passed / 26 skipped. Production build passed with installed Node 22.17.1 (Node 18 lacks the crypto global required by current dependencies). Browser: 890×626 landscape, 626×890 upright, shortened 890×500 and 678×466; all five dock tabs and HQ toggle exercised; day/lite checked. Fixture chart values are not live account figures. Physical Safari fullscreen/keyboard and complete site-wide mobile QA remain unverified. Push hook will rerun required gates.
