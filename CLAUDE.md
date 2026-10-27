# FEELESS — working rules (lean). The full feature log lives in `docs/FEELESS_HISTORY.md` — GREP IT, never load it whole.

> 🧭 New session? Read `docs/HANDOFF.md` (map, commands, state) → `## CURRENT TASKS` below → only the history lines your task touches.
> 🧨 Fuse / the real card? Read `docs/DEGEN_PLAYBOOK.md` first.

Degen trading terminal (Solana-first). Every feature ships **one and done**: styled, animated, fast, tested, pushed.

## 🎨 MANDATORY STYLING + ANIMATION — NO BS (owner, 2026-10-21; this outranks speed of delivery)
The owner rejected work that shipped as "dull", "non degen", "emojis sliding around a block". A surface is NOT done until it meets ALL of:
1. **Scratch-built visuals, not emoji props.** Emojis are labels only — never the art. A city has drawn buildings (CSS 3D boxes / SVG /
   canvas / three.js) with lit windows, roofs, streets, MOVING CARS with headlights, people, signs; a card has a drawn face; a chart scene
   has drawn geometry. If the reference is a game (Godfather PSP, Jailblock, Sims, Pump.fun), match its LOOK, not a grid of icons.
2. **Every surface is ALIVE**: at least one ambient layer (light sweep, drifting glow, particles, traffic, weather), real-number
   animation (values tick / flash / count up on change, bars fill), and an entrance (stagger via `--i`). transform/opacity only;
   pause off-screen (`lib/fxPause.js`), still under `body.fx-lite` + `prefers-reduced-motion`.
3. **Degen meta, unique per page**: its own palette + backdrop + type (FEELESS green is home / trade; Familia = noir gold + city night;
   FeeCat = violet night; Launch = the official logo green on near-black — owner 2026-10-22, amber dusk read as mud). Glass panels with an inner highlight, neon edges, glow on the hot number, segmented
   controls, no flat boxes-in-boxes, no bare paragraph walls — meters, rings, bars and charts instead of text.
4. **A twist, never a copy**: when the owner names a reference ("dev/null", "Pump", "X"), take the IDEA and make a FEELESS version
   (our data, our language: germ floor, gun line, rep, rug, MP) — never a clone of the reference's UI.
5. **Every interactive element**: hover + active + focus-visible, a `data-tip` explaining it, ≥ 32px hit area, never covered by a layer.
6. **Prove it**: open it in the Browser pane, screenshot it, and look at it as the owner would before saying done. If it looks like a
   prototype, it is not done.
7. Day theme, 360 px phone, fx-lite, reduced motion — every new surface.

## How to work (save usage)
- Be brief with the owner. Report what changed, what was tested, what wasn't. No essays.
- Stay on the task asked. No side quests; note unrelated issues in one line.
- Read only what you need (grep first, then targeted reads). Batch independent commands.
- Every request gets FINISHED, in priority order — never a half-organized or half-styled surface when a new request lands. Every
  handoff you write repeats: conserve usage · finish everything by priority · never dead-style (`docs/HANDOFF.md` top box).
- NEVER DEAD STYLE: deleting CSS ⇒ first prove no component renders the class (`styles/cssCoverage.test.js` fails on a rendered class with
  no rule; it caught the 2026-10-15 wipe of agentDesk.css). A new panel = styled + a live visual of its real numbers, never bare text.
- Push every finished change to **both** `main` and the session branch. The owner's machine runs
  `scripts/auto-pull.sh` on `main`, so Chrome updates on its own.

## Before every push (all must pass)
1. `cd frontend && CI=true yarn test --watchAll=false` → all green.
2. `cd frontend && CI=false npx craco build` → builds.
3. `PYTHONPATH=backend:. .venv/bin/python -m pytest backend/tests -q` (plain `python` isn't on the owner's Mac) → all green (live-service tests may skip).
4. New mechanic ⇒ new test (fake the network; never hit mainnet or move funds).
5. UI change ⇒ open it (Playwright/Chromium is preinstalled) or say plainly that you didn't.

## Meta styling (no dead UI, ever)
- Trade page = segmented tabs (Swap | Fuse Lab), no market lists under the swap. New page sections go behind a tab, not
  stacked below (less scroll). Feature CSS that would bust meta.css's budget gets its own sheet imported by the component
  (e.g. `styles/fuseLab.css`), still built from m-* tokens.
- "Meta UI" = everything below, on EVERY feature end to end (backend data → frontend surface): m-* presets, live
  numbers, hover/active/focus, animated popovers, day theme, 360px. A backend-only feature isn't done until its UI is meta.
- Palette: black/very dark green surfaces, RICH ROYAL GREEN `#15d16a` accent (rgb 21,209,106; bright variant `#45e486`; the old mint `#19f58f` is retired — owner: "not this green"), `#ff8fa3` danger, `var(--gold)` warn.
  Labels/numbers in `JetBrains Mono`, uppercase micro-labels with letter-spacing.
- Every interactive element has hover, active and focus states. Selected = solid neon fill with dark text.
- Dropdowns, popovers and modals animate in (≤200ms, opacity + small translate/scale) and respect
  `prefers-reduced-motion`.
- Scrollbars: thin neon thumb (`scrollbar-width:thin` + `::-webkit-scrollbar` 6px) or hidden when the
  content fits. Never the default grey bar. Review/confirm dialogs must fit without scrolling.
- Segmented controls instead of loose button rows; settings live behind the ⚙ panel, not on the card.
- Numbers: compact (`$4.4M`, `+12.3%`, huge moves as `12.4x`) and always show the $ value next to SOL.
- Day theme: every new surface gets a `body.theme-day` override.
- Build new UI from the `m-*` presets in `frontend/src/styles/meta.css` (m-card, m-label, m-num, m-chip, m-seg, m-btn,
  m-input, m-toggle, m-note, m-bars, m-kv). Big panels get `m-live` (drifting royal-green aurora + edge scan,
  2 pseudo-layers, never on list rows); primary buy/go buttons get `m-go` (deep→neon gradient, lift on hover). Add a preset there before writing one-off CSS. `styles/cssHygiene.test.js`
  fails on dead class rules and on legacy sheets growing past their KB budget; lower budgets when you delete CSS.

## CSS map (where styles live — keep it organized)
- `meta.css` = m-* presets only (budget-capped). `terminal.css` = legacy terminal (append scoped blocks only when no sheet fits).
- Feature sheets, imported by their component, built from m-* tokens: `fuseLab.css` (Lab, FuseRail `frail-*`, FuseEvolve `fe-*`),
  `fusePage.css` (Fuse 🧬 page `fp-*`, Arena stage `ar-*`, HQ bundle/vault/fuse-fee bits), `pulseBolt.css` (PulseDot), `runners.css` (`rn-*`
  hero/ring/countdown/lanes/CoinRow, fire accent `--rn-fire`), `auras.css`, `command.css` (HQ).
- Each sheet ends with its own `body.fx-lite`, `prefers-reduced-motion` and `body.theme-day` blocks + a 640px media query.
- Motion: one keyframe set per sheet (`fp*`, `rn*`, `fcd*`), transform/opacity only, list stagger via `--i` × 45–60ms.
- Delete a class from JSX ⇒ delete its rule (cssHygiene fails on dead rules).

## One component per job
- Every coin chart is `components/terminal/TrenchChart.jsx` (toolbar, P&L badge, your trades on candles, Quick trade,
  Dip/Rip, rug shield). Trenches and the globe war room both use it; fix or extend it there, never fork a copy.
- Under the chart: `TradeTape` (live swaps, whales = ≥$1K and ≥5× median, 🔎 opens any wallet's case file). Room chart
  cards size by a `--chart-h` token per layout; nothing inside may be clipped in any layout or the floating window.
- Coins you hold: `lib/myHoldings.js` (`useHeld`, `HeldChip`), one shared poller of `/api/reputation/pnl/{address}`.
- One alert stream: every phone alert also goes to the wallet inbox via `notify(..., push=False)` with
  `meta.claim` + `meta.source`; push subscriptions carry `prefs.address`. Inbox lenses: All / Trading / Social.
- Swaps never auto-quote: the user picks coins + amount, then clicks Get quote (an open quote still refreshes every 10s).

## Speed (no lag)
- No request waterfalls: run independent lookups with `asyncio.gather` / parallel fetches.
- Hot JSON stores load via `_cached_json` / `_json_load` (parsed once per file version).
- Shared pollers for anything shown on many cards (`lib/pumpPulse.js`, `lib/snipersOut.js`), never one per card.
- Debounce typing (≤300ms); prefetch what the next click needs (quotes are pre-simulated).
- One pooled `httpx.AsyncClient` per service for outbound calls.
- Animate only transform/opacity. Never animate a custom property (`--ang` repaints every frame), never
  `backdrop-filter` over animated layers, no `filter: blur()` on moving layers. Heavy FX must die under `body.fx-lite`.
- Lag catcher (HQ › Lag catcher) is the source of truth: fix its list before adding features. Full list: `docs/REQUIREMENTS.md`.

## Data sources
- **NO GeckoTerminal, sitewide, ever** (backend or frontend). `backend/tests/test_no_geckoterminal.py` enforces it.
  Market data = DexScreener + our own indexes (Pump.fun, LetsBONK, LaunchLab, Helius, Alchemy, Jupiter).
- No dead war rooms: `chain_feed` tops up any chain under `THIN_FEED` pools from its own DEXes (`CHAIN_QUOTES` search)
  and its hub token's pools (`NATIVE_POOLS`, DexScreener /token-pairs). Quiet "new" lists add the youngest active pools
  tagged `discovery: 'rising'`; coins hosted on another chain are tagged `via` (Zora → Base). Never pad with unrelated coins.
- Search ranks most trusted first (`rankSearch`/`trustScore` in SearchBox): FEELESS assets, pasted CA, exact $SYMBOL,
  then liquidity/mcap/age/profile; one row per token = its deepest pool.
- Candles (ONGOING PRIORITY): `_sanitize` + `_fill_gaps` (server), `scrubCandles` + the live gap-filler (client): every
  bucket exists, OHLC valid, and every candle OPENS AT THE PREVIOUS CLOSE (continuous; no floating one-price dashes).
  History = first provider with ≥120 bars, else the longest that agrees with the live price. Change only with a test.

## Degen meta playbook (how to build here)
- Ship what a trader feels in 5 seconds: live numbers, their own position, one-tap action, the evidence behind a warning.
- One component per job, reused everywhere (TrenchChart, TradeTape, HeldChip, ChatFx, IntelligenceCard).
- Every surface: works at 360px wide inside a chat, in every war room layout, day + night, fx-lite, reduced motion.
- Chats: per-room animated background (`ChatFx`, picked in ⚙, stored as `themes[room]`) always with the FEE mark.
  Tiers by $FEE held (`/api/reputation/perks` feeUsd): free = Live mood, FEE glow, FEE rain, Plain; $5+ = 4 more; $100+ = 5 more.
  Live mood (`lib/coinMood.js`) is one shared 30s poll per coin: pump / dump / snipers-cleared / calm, soft colours only.
  Bubbles hug the text with a near-opaque fill (never backdrop-filter over the animated layer).
- Chat ⚙ › badges: `POST /api/reputation/profile/featured-badges` changes only featuredBadges (earned, chat-limit capped).
- Radar = Watchlist + Signal alerts (`RadarPage`); `/terminal/alerts` and `?view=signals` open the Signals side.
- Music: link-only adds (title via noembed), plays like YouTube across refreshes (`resumeFrom`: same song, the player's own reported second, still playing / still paused; sound blocked → keeps playing muted, unmutes on the first tap/key),
  queue items removable, 📺 toggles the video (audio keeps playing).
- Trade tape: Helius first; when it fails (quota) the candles service parses swaps from Solana RPC (Alchemy). Rows need a
  real SOL/USD leg (dust spam dropped). Tags from `/api/reputation/intel` via `lib/coinIntel.js` (one fetch/coin/min).

## Staff + safety nets
- `_is_staff(address)` is THE rule for admin/creator wallets (any linked wallet): every badge, perk, chat background,
  color, Fee Reserve room and top perk tier unlock automatically. Never hand-roll `in _admin_wallets()` checks.
- `test_no_undefined_names.py` (pyflakes) fails the suite on any undefined name — when deleting code "up to the next
  def", re-read what sat between (a dropped constant once crashed Pump Pulse 65× before anyone noticed).
- Tests NEVER touch real data: `tests/conftest.py` sandboxes every backend `Path` under `backend/data` per test — including modules first imported inside a test (meta-path hook; a lazy `importorskip` once overwrote runners.json). (A test
  once wrote 22 fake $2 fees into the real fee ledger.) Fee totals self-heal from the ledger (`_fee_totals_heal`).
- Auto fx-lite is temporary (`auto@<ms>`, 6h, off after 3 smooth minutes); user-chosen lite stays. Tilt is cheap and
  stays on in lite.
- FeeCat: `feecat_brain.discipline` = 9 lives (loss −1, win +1 in 24h, 0 = nap) + tilt/cold pauses + expectancy sizing.
  It may only ever make her trade LESS. `/api/cats/{id}/profile` returns it live; FeeCat HQ strip shows it.
- `openWarRoom(pair)` opens any coin's war room in the terminal (one lazy `WarRoomHost`).
- Uploads: no sign-in needed, so 20/hour per IP; GIFs skip the canvas crop (keeps animation), 40 MB cap; stills 15 MB (owner 2026-10-26).

## Money rules (trading)
- 🔒 P&L NEVER includes fees, anywhere (live trades, Fuse cards, Arena/Prime, FeeCat): cost = money that REACHED THE POOL
  (`trade_fills.position` → `investedPoolUsd` / `realizedPoolUsd`; client `pnlSummary` uses them), fees live on the receipt
  (`feesUsd`, FeeCat `feesSol`). Value = on-chain balance × Jupiter live price. Phantom's chart price can lag ~0.5%.
- Engine: Jupiter Swap API primary (FEELESS fee into our SOL/USDC token accounts, capped priority,
  our broadcast). Ultra only as engine or opt-in fallback. Fallback off + Swap API down ⇒ trading pauses.
- Nothing trades fee-free except **buying** $FEE / FEECAT / rFEE. Coin→coin with no SOL/USDC side is refused.
- The wallet signs everything; the server verifies the signed message equals the quoted one; no resubmits.
- Only show or sign an order that matches the coins, side and amount on screen.

## Layout
- Helius key: `HELIUS_API_KEY` or `HELIUS_RPC_URL` (SOLANA_RPC_URL may point at another RPC).
- Backend services (restart all after backend changes: `bash scripts/start-backend.sh`):
  `server` 5001 (market + trading), `reputation_service` 5077 (social, fees, admin), `feecat_service` 5088, `candles_service` 5099.
- Frontend: CRA + craco on 51367. Styles mostly in `frontend/src/styles/terminal.css` (append scoped blocks).
- HQ settings that matter at scale (keys, engine, fees) must be visible in its **Core** group.


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
g. 🖥 HQ: Fuse tab de-cluttered · fee tab = every real-money fee (swap · trench · perps · pools · launch) set by the owner · Fuse family view at
   the page bottom renders oddly (owner screenshot) · every HQ tab ≤ 1 screen.
h. 📱 Trenches + Pump radar mobile flow redo (one-thumb), Duo per-tab features beyond the split layouts (lib/duo.js is the hook).
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
