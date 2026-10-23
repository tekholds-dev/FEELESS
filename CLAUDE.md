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
- Uploads: no sign-in needed, so 20/hour per IP; GIFs skip the canvas crop (keeps animation), 6 MB cap; stills 2 MB.

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


## 📋 CURRENT TASKS (one list, priority order — update every session; finished items → docs/FEELESS_HISTORY.md, old lists archived there 2026-10-22)
Rules for all: research the best web3 / degen sites first, then a FEELESS twist · every page complete top to bottom · real money = the wallet
signs, FEELESS never holds keys · conserve usage · finish by priority · never dead-style.

DONE 2026-10-22 late night (owner to look at): 🚚 Opus round landed on main (range errands · New-agent door · Pump intake · NEXA cover) ·
💵 `scripts/cash-check.py` = fast real-card cash proof (wallet covers cash, coins atom for atom, last N swaps matched to the chain) · 🏁 duo
seat never "running $?" after a close (SOLD phase, closed trade stays in the seat with its cash back) · 🎛 SEAT DECK (6 live tiles) beside the hex.

DONE (latest, owner to look at — 2026-10-22 evening): 🎛 Brain chat line → model settings for real ("ossy context 16k, temp 0.6" → ✅ → applied /
LM Studio reload) + Brain › Models = ONE LM Studio Load + Inference view (LOADED vs WANTED, ⚡ Reload) + Brain fixed at 360 px · 💬 THE STREETS city
chat (`StreetChat`) · 👑 creator's family on any linked / HQ wallet (`_seat_of`) + 👑 OVERWATCH (HQ › Familia + city WATCH door) · 💤 THE NIGHT
VAULT (9th Avenue building, `sleep_money.py`) · 🏠 HQ one-stop tools + 📒 Books · 🏷 THE REALTOR · 🐛 Family Fuse cards (linked wallets + Prime cards).
Earlier: Fee City 2× + FEELESS AVENUE · Pool Hall charts · Jupiter Lend deposit-here · defence · chat themes · Rep radar · online status.

DONE 2026-10-22 night (owner to look at): 🧪 TRENCH THEORY (`trench_theory.py`, docs/TRENCH_THEORY.md — 7 measured laws ride on every coin case) ·
🪟 NEXA's full read fixed (it was cut off at 100 tokens → parse failed; lean tagged read, no persona) · 💸 rep market pays a lone right call (house
seed) · 🔑 Familia sign-in in one signature (no more "not signed in") · 🛡 raids ≤ 3 per family per 12 h both ways · 📈 TRADE CENTER · 🗼 TT TRENCH
TOWERS (intake list, floating coins, why it pumped, theory) · ⚖ Courthouse top catches · 🐱 FeeCat tower (live + your cats + create) · 💸 MONEY MENU
(12 doors under every room) · 🎯 v3 RANGE TUNER (exact IL) · 📺 BILLBOARDS (5,000 MP / 24 h, slideshow) · 📉 PERPS DESK (Hyperliquid data → Jupiter /
Drift / Hyperliquid) · 🏗 under construction when funds run out · 🏛 CITY HALLS (Pump / Raydium / Bonk / Docks) · 🎲 rep market inside the city ·
gate pinned to Node ≥ 18.

DONE 2026-10-22 late (owner's block-page screenshot "all requests never started"): 🧰 FAMILY DECK under the block (10 tools: Trade Center ·
Trench Towers · Pools · Night Vault · Perps · Pump board · Cats · Rep market · Books · Members) · 🗼 desk picks hovering over the block · 🏆 Fuse
Arena BEST SETTINGS (styles + what the top quarter shares) · 🐱 FeeCat's Combo on every Pool Hub (50/30/20 cash / SOL / fees, true math) · 📈 Trade
Center REAL RECORD (each lane's closed lots) · 🪑 G4 proof bench · theory shadow-tested on the real card (docs/TRENCH_THEORY.md) · /dev/block.
✅ OWNER DECIDED "15 minutes not 30": agent bails of a red real coin wait 15 min from the buy (`AGENT_MIN_HOLD`; stops / rugs / green sales
never wait) + REAL_MIN_HOLD 15. 🐛 Familia crash ("reading 'call'" at Lazy) fixed: FamilyDeck imports FamilyHQ / CityAvenue / PoolHub statically.

P0 — OWNER 2026-10-22 LATEST-LATEST (his words: "Familia Fee City has REAL buildings = you can really do EVERYTHING from everywhere in
families; buildings represent realtime data"; hardest → easiest):
0. ✋ YOUR TRADES STAY (owner: "any trade I submit on the Agent / Sicario's tab should STAY"): FIXED 2026-10-22 — the rug shield sold the
   owner's $MOON pick twice on Jupiter's ONE-SIDED depth ($13.9K vs DexScreener $29.7K); now it never judges a Jupiter reading and a hand pick
   only WARNS unless its pool falls under a quarter (`arena_prime.owner_pick`, `RUG_PICK_LIQ`, `LIQ_SRC`). AUDITED: stop / trail / early cut /
   trench drop / rotation / lock-bank / initial-out already skip picks; instant-loss + the tape's flow exit / rug radar / climax trim now skip
   them too (⚠ warning every 10 min, `flow.flow_exits` `mine`). The owner's own lines + the −45 % line are the only auto-sells of a hand pick.
P. ✅ SHIPPED 2026-10-22 (Brain › 🎭 Prompts, `prompt_studio.py`, `ai_router.with_studio`, /admin/ai/prompts; preview /dev/brain). + ✅ 🤖 AUTO-TUNE
   switch per model (last 10 trades red = losing on average AND < 40 % won → AUTO-TUNED applied on the AI round; any applied set gets 6 h
   first; `_studio_auto`) + 🏆 MINDSET LADDER (each trade credited to the mindset on when it opened; proven ≥ 5 trades rank by avg %).
   Was: 🧠 PROMPT STUDIO for every model (owner, 2026-10-22): see each model's live CONTEXT + system prompt (G4 · OSSY · NEXA · any LM Studio /
   llama model) and 3 auto-generated prompt sets per model — ELITE (supreme persona), DEGEN TRENCH (germ floor, buyers, fresh-pump laws),
   and a PROGRESSIVE mix ("quick in, patient while in profit, rush when it runs") — one tap APPLIES to LM Studio / llama (rig reload path that
   exists: Brain › Models). AUTO-TUNE: when a model's graded record turns red (proof bench, NEXA's YES grades, duo totals), propose the prompt
   change that fixes its mindset, with the evidence; the owner applies. OSSY / G4 keep taking turns (one trade each, the holder runs it).
M. 🧠 BRAIN › MODELS = LM STUDIO'S OWN PANEL, IN FEELESS (owner, 2026-10-23, hardest → easiest):
   1. Per model the LM Studio tabs — INFO (model, params, format, quant, size, arch, max ctx) · LOAD (context, GPU offload, CPU threads, eval
      batch, flash attention, KV cache, keep in memory, mmap, seed, parallel — the `lms load` reload path that exists) · INFERENCE (preset,
      SYSTEM PROMPT = what FEELESS really sends: seat prompt + the 🎭 applied mindset, temperature, limit response length, context overflow,
      stop strings, SAMPLING top-k / top-p / min-p / repeat penalty, structured output, speculative decoding — all per-request params FEELESS
      sends) · SERVER (port, CORS, JIT load, idle TTL, serve on network — read what LM Studio exposes) · MCP (feeless_mcp tools it can call).
      NEXA (llamafile) gets the same tabs for what llamafile exposes (/props, /slots).
   2. More VITALS for every model: tokens/s, time to first token, queue depth, error rate, context fill, uptime, last reload — live.
   3. Fix the Models tab look in the Brain: the model cards are cut off at the bottom and a second rig panel repeats on the right.
   (The 🎭 mindset is sent by FEELESS inside every API call's system message — LM Studio's own "System Prompt" box only feeds its own chat
   window, so it never shows there; the proof is "✓ IN USE · last call carried it" in Brain › Prompts and 🎭 tags on Models › live calls.)
A0. ✅ SHIPPED 2026-10-23 — TRADE IN FAMILIA, NO REDIRECTS: `FamiliaTrade.jsx` — every ⚡ Trade in Familia (Pump Radar, $FEE Bank, Trade Center,
   Trench Towers, Pool Hub, city markets) slides the FAMILIA TRADE DESK over the room (TrenchChart + Quick trade + vitals; wallet signs), the LST
   switch errand opens the swap in the dock, rooms lost their "Full page ↗" jumps, a member's "Full profile ↗" = the case file in place. A guard
   test fails on any openWarRoom / full-page jump in Familia. Still links out: landmark marks (Build a Fuse card · Launch · Rug Shield) and the
   mini deck's Fuse cards — next: embed those too.
T. 🗼 TRENCH TOWERS = ITS OWN ISLAND with ONE huge tower (owner, 2026-10-23): no field of little coin towers and no side windows — one landmark
   tower (live: READY count lit on its floors, the hottest coin on its crown sign); tap it → ONE pop-out = the Trench Towers room (intake list,
   desk read, theory line) where ⚡ Trade opens the Familia trade desk.
A1. 🇺🇸 PERPS FOR US TRADERS (owner, 2026-10-23: "no Drift or Hyperliquid if there's no way in the USA"): ✅ the Perps desk now lists only coins a
   US-legal venue offers and links Kraken Pro (CFTC-regulated perps via Bitnomial, since 2026-06-15) + Coinbase (perpetual-style futures via its
   FCM, BTC / ETH at launch); Hyperliquid = price / funding reference only. IN-APP perps orders for US users = the user's Kraken / Coinbase account
   through their official APIs (OAuth / user keys, never FEELESS custody) — an OWNER + LEGAL decision first (FEELESS would be routing orders on a
   regulated venue). Kalshi's BTC perps are another regulated option. Never wire an offshore venue for US users (rule 1c).
A. 📉 PERPS IN THE POPOUT, NO REDIRECT: the Perps building trades in place — one tap picks the provider (Jupiter Perps · Drift · Hyperliquid…),
   size from $5, long / short, live position + P&L in the building; the wallet signs; guards (memory: new buy doors need guards). ⚠ LEGAL: a
   venue that blocks the user's region stays blocked in-app too (rule 1c — never a geo-block loophole); show which providers serve the user.
B. 💸 POOLS + PERPS MUST EARN: "aint bringing no money" — every real-money building shows what $5 / $100 earns live and deposits in place.
C. 🏙 MY FAMILY TOWN = the main city's engine features (day / night, traffic, weather…) and NO LAG (it "lags so bad") — profile it first.
D. 📦 FAMILIA LOADS AS ITS OWN APP PACKAGE (separate lazy bundle, preloaded on hover) — no lag sitewide.
E. 🪟 City window BIGGER. F. 💬 THE most litty chat on the internet (Familia / street chat). G. Every building + family idea = real function,
   visually advanced, live data, NO dead text.
H. 🐱🚀 REDO the unfinished parts of the FeeCat + Launch tabs / pages: every process step lit-styled (drawn, live, animated), no dead forms.

P0 — OWNER 2026-10-22 LATEST (hardest first; finish in-flight work first, conserve usage, never dead-style)
DONE tonight: 🐛 Familia/route crash (FamilyDeck static imports) · 🕰 15-min agent min hold (`AGENT_MIN_HOLD`) · 🪟🐱 NEXA TRADES AS FEECAT
(owner switch HQ › Fee › NEXA's desk; `nexa_desk.py`: ≤ 3 one-line YES/NO · HOLD/SELL calls per 5 min on MC / age / 5m / 1h / buyers / pool /
top10 → FeeCat buys only her YES through every guard, sells her SELL; user cats stay on the rule engine) · NEXA chat row: models rig in its own
column (was overflowing onto the chat) · 🎨 all 14 chat themes redrawn as drawn scenes (radar, vault, lava lake, synthwave, LED tape…).
OPEN, hardest → easiest:
1. 🏙 FAMILY BLOCK — v1 SHIPPED (block_markets.py + FamilyBlock3D): real market buildings in the Fee City engine, UNDER CONSTRUCTION until a
   real position (JitoSOL/JupSOL/mSOL/INF/JLP balances · Orca/Raydium position NFTs · Kamino vault shares), 4 OPEN PLOTS to add markets, errands
   (build it · better LST → our swap prefilled · check range · size JLP → perps desk), MP game folded into one panel. NEXT: decode Orca / Raydium
   positions → IN / OUT OF RANGE + "tighten / re-center" errand with the numbers; readers for Meteora DLMM (SDK) · marginfi · Save · PumpSwap LP;
   count members' wallets (opt-in); retire family_world's drag-the-pizza ERRANDS UI (MobHome / FamilyWorld) for the block's real errands.
1b. 🌆 FEE CITY = SIMCITY SCALE (owner): the capital BIGGER, and ~80 % of the city REAL-MONEY buildings (pools, vaults, lend, perps, LSTs, the
   desk) SPREAD across districts — not packed on one island; family blocks as their own islands off the capital.
1c. 🇺🇸 US users: NO geo-block loopholes (rule, owner's legal exposure). Route them to venues + in-app deposits allowed for them instead.
00. 🔝 OWNER LAST (2026-10-22 night): NEXA FALLBACK — FeeCat's engine covers when NEXA doesn't answer (today she blocks every buy) +
   next-gen one-line desk prompts in her trench style · AGENTS HUB with vitals / cost / P&L / context / refill · FAST real-card cash audit +
   prove card P&L is real · all FEELESS fees set from HQ › Core · declutter HQ › Fuse. Branch `night-1022` holds 4 ungated commits (HANDOFF).
0. 🐱 USER CAT AGENTS (owner, 2026-10-22 late; HARDEST, real money): users pick 1–2 cat AI agents — (a) DO-ANYTHING agents that act through
   FEELESS with their own wallet funds on the user's request (trade, Polymarket-style markets where legal, tasks), or (b) one of 2 TRADE-ONLY
   agents with lit features. The user sees their cat's BRAIN and talks to it; agents are PAID (pricing + custody = owner decision first,
   docs/REAL_CATS.md; every real-money action needs guards + the wallet signs). NEXA / OSSY / G4 stay OWNER-ONLY for now.
0b. 🐱 FEECAT TERMINAL: every tab + click-through correct; "Create a cat" ≠ "Build a cat" (two different flows); lit restyle, clean look.
0c. 👑 Creator wallet unlocks EVERY feature everywhere (`_is_staff` front + back) — audit each gate. 0d. 🔥 More Pump coins on the intake.
1d. ✂ CUT (Claude's audit 2026-10-22, owner to OK): the fake model catalog in /api/cats/brains (Claude / GPT / Grok rows that only run the rule
   engine) · family_world's drag-the-pizza ERRANDS + the MP store build catalog (the block is real markets now) · 4 ways to start services
   (run-feeless.sh / start-backend.sh / background.sh / keep-alive — two watchers were running at once tonight) → ONE supervisor · cat /action
   endpoints with no owner check (paper, still wrong) · split reputation_service.py (31K lines; tonight a new helper silently replaced a cache —
   guarded now by tests/test_no_name_collisions.py).
1e. 🏆 ELITE adds: CLMM range reads → exact "out of range by X %, re-center to A–B" errands · NEXA's FeeCat record vs the rule engine → she earns
   real money only after beating it in shadow · one "YOUR MONEY" tower in the capital (every proved position, live) · compliant US routing.
2. 🌐 NEXA discovery: a site's AGE (RDAP / WHOIS) + a page SNAPSHOT (title, headings, tech fingerprint, template match) → "real tech vs another
   same-utility site" verdict into her discovery base; one-line packet like her desk calls.
3. 🎨 Site palette (owner AGAIN 2026-10-22 late, Launch-page screenshot: "better official site green than this shitty green all over the site"):
   retire the muddy / olive / brown-green panels + backdrops ("color of manure") → the OFFICIAL FEELESS green of the logo (#15d16a / #45e486
   neon on near-black, no olive tint in surfaces) — token sweep sitewide (meta.css m-* tokens first, then each sheet's hard-coded greens), Launch first.
4. 📊 Text walls → realtime visuals (meters, rings, ticking numbers) + dead styles out — every page, starting with HQ (Agents + FeeCat tabs).
5. Screenshot each chat theme in the Brain drawer + a room; confirm the theme layer covers the whole drawer (NEURAL default).
6. Restart reputation + feecat services (from Claude's watcher) so tonight's backend is live; confirm NEXA's desk calls land.

P0 — still open from the night list, in order
1. 🧠 G4: 🪑 PROOF BENCH DONE 2026-10-22 (its last 209 FAVOR calls = −0.4 % median, 43 % up → OSSY opens real seats until G4's record turns).
   Still: stalls (read HQ › Brain › Models live numbers first, then a stall watchdog). Models tab BESIDE NEXA's chat (layout). Wire the trench theory into the deterministic agents only after a shadow test.
2. 🐆 Sicario's seat board: DONE 2026-10-22 (the odd 3rd seat spans its row, hunting seat shows TURN / READY / REFUSED) — owner to confirm it was the screenshot's issue.
3. 💎 ONE points system (season pts + MP + rep-market chips) usable everywhere (badge pools boost…) — an ECONOMY decision for the owner first
   (rates, what converts to what). Real-USD rep market / Polymarket = owner + legal decision (prediction markets are regulated).
4. 🏦 A building ASSIGNED to a real position (pool / vault) that goes under construction when the wallet's on-chain balance is pulled — needs
   per-protocol balance reads (LP / receipt mints); MP-funded blocks already do it.
5. Perps orders IN-APP (not just routed): each venue's SDK + guards (memory: new buy doors need guards) — owner's call. No geo-block loopholes, ever.
6. 🗂 Desktop clean-up — confirm the folder list with the owner first (never images).
NOTE: merging into main LOCALLY means auto-pull never restarts the backend — after a backend push, restart reputation_service via the watcher
(memory: restart-from-claude-tree).

P1 — FAMILIA = the one-stop shop in web3 (what is left)
1. ❓ OWNER: city full-screen by default? (Realtor shipped as the clutter-free buy space; a dedicated for-sale ISLAND in 3D is still open.)
2. 💤 Night Vault next: DCA / limit orders (Jupiter Recurring + Trigger APIs: build → verify programs like `lend_earn.verify` → wallet signs; an
   allowlist of blue chips only — memory: new buy doors need guards) · in-app Kamino Multiply / vault deposits need Kamino's SDK (owner's call).
3. 🐛 Fuse card bug: the fix above is the one found in code — owner to confirm it was the bug they saw (if not: repro steps first).
4. ⚡ Scale for thousands: shared pollers, 3D perf (instancing, LOD), load tests on familia-world / familia/street.
5. ✅ Check day theme + 360 px: Avenue rooms (Night Vault included), Overwatch, Realtor (Street chat + Brain done at 360).
6. 💬 Street chat next: per-street pinned call, slow-mode for Dons, coin-card mini charts.
7. City leftovers: outer cities' real-money markets · in-city swap · HELD coins + FEELESS-launched coins as buildings · ALL of FEE as city mechanics ·
   raids / hits played in-city · MP-only buildings + gold shop · $ and MP ladders · badge / card / MOBhouse customization.

P2 — PAGES BELOW BAR: Launch click-through pages · FeeCat lore + other tabs · Roadmap / whitepaper as a 3D view · OSSY / G4 duo chats ·
   NEXA reads + trades fast (no 40 s waits on the i5).
P3 — AI / BRAIN: ✅ done 2026-10-22 (chat line → rig proposals, LM Studio rig view, Brain 360 px). Next only if asked: OSSY / G4 duo chat look.
P4 — HQ: Agents dead clicks (read HQ › Bugs "[dead click]" first; on the owner's Mac it was memory) · Lag catcher + Support clean-up · vault /
   pool pair builder live visual · Agents rebuild only after `scripts/edge-audit.py` numbers.
P5 — OWNER DECISIONS (blocking): CUSTODY pick for family wallets, real-money cats, top-pot Fuse ($1K+) — `docs/REAL_CATS.md` · LP SDK deposits.
P6 — IDEAS: FeeCat + AI agent pair that talk · "build a better coin" track in Lag catcher.
