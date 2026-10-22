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
   FeeCat = violet night; Launch = amber dusk). Glass panels with an inner highlight, neon edges, glow on the hot number, segmented
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


## 📋 CURRENT TASKS (update this list every session — newest first; finished items move to the history file)
DONE 2026-10-21 (owner to look at): Familia 3D city (`FamilyCity3D`) · FEEd call receipts + Heat / Graveyard + TRENCH WIRE · FeeCat stage
(`FeeCatStage`) · Launch pad hero · Launch a Cat = Create a Cat fields · Fee buys again (Jupiter holder fallback) · HQ buttons never locked ·
NEXA chat ≤ 70 tokens, re-warmed after reads (≈ 6s warm).
OPEN, owner's order (2026-10-21, second list — "do these after"):
1. 🧠 Brain chat must TRULY change model settings (the LM Studio Load / Inference panel: context length, max concurrency, KV cache
   quantization, prompt disk cache, temperature, response length, preset) — a chat line → a proposal → applied (`ai_rig` for what FEELESS
   sends; `lms load …` for this Mac's model when the owner approves the reload; the desktop model only on the owner's explicit approval).
2. 🎨 (PROGRESS BAR DONE 2026-10-21 — `ThinkBar` in AiChat, no HQ-wide bar for /admin/ai/) Redo the Brain + OSSY / G4 UI: cleaner, responsive, meta. NO overlay spinner while a model answers — a real progress bar (the call's
   elapsed vs that model's own average, like Brain › Models). No lag site-wide.
3. 🧹 Clean dead files for real from HQ › Lag catcher › Code health (today it only lists them): a "remove" action must go through the build
   queue / a git commit with tests green — never delete from the UI without the gate.
4. 🗂 HQ tab layout: DONE 2026-10-21 (6 groups ≤ 7 tools, one scrolling tools row, a one-line blurb per group, tips on every tool).
   Still open: Agents tab dead clicks in some areas, Lag catcher + Support visual clean-up, unfinished sub-pages (vault / pool pair builder
   needs a live visual of the user's picks).
5. 🐆 Agents tab "can't click": code verified clickable at 1440 px with live data (2026-10-21). Cause on the owner's Mac = memory: OSSY
   (gpt-oss-20b, 12 GB) + dev server + Chrome → 16.8 GB swap. Options for the owner: fast mode (`bash scripts/serve-fast.sh`, :51368),
   OSSY → qwen3-4b-2507, or OSSY's LM Studio Load: Max Concurrency 1, KV cache quantization ON (halves the KV memory).
6. 💵 REAL-MONEY CATS (Build a Cat shows every model, no paper; creator sets pricing in HQ) — FULL USER PROCESS must be designed before code
   (`docs/REAL_CATS.md`): who holds the funds (user's own wallet signing = not autonomous; a FEELESS-held wallet = custody, against the
   "never hold user keys" rule) → owner decision first. Then: pick models (whole OpenRouter list, pricing per decision) → fund → limits →
   live → pull / withdraw → fees to the creator wallet → receipts. Never ship a half of it.
7. Familia game loop on `family_world.py`: gold shop with owner pricing, raid board polish, room customization, season art.
8. Agents may need a full redo — run `scripts/edge-audit.py` + the real ledger first and lead with the numbers.
9. NEXA runtime work (`nexa_controller.py`, ModelRig NEXA wanted-vs-running) COMMITTED 2026-10-21 on the owner's "finish this work".

OPEN, owner's FIFTH list (2026-10-21, late) — ahead of the fourth list, in this order:
0. 🐆 AGENTS (Sicario's) tab: timeframes, decision seat cards and other clickables "stopped working hours ago". Backend: every /admin call
   answers 200 (checked the logs). Suspect: 31bfd65d (11:18, `symTap` + `agentTips` on the whole cockpit) — needs a look in the owner's
   signed-in HQ (the Browser pane cannot sign in) → reproduce, fix, test every clickable. TOP PRIORITY: it runs real money.
1. 🏙 FEE CITY ×3 BIGGER, and the game lives IN the city (no tab row of lenses, no little boxes):
   a. Ranked · Raids · Errands · Challenges · Crew deck · Rewards · Cartels become places / buildings you walk into in the city.
   b. ~80 % of Fee City's buildings = REAL MARKETS: established + new DeFi (pools, vaults, v2 / v3 / CLMM, lending, perps…) with live
      vitals (TVL, volume, APR, price) drawn on / over the building, a pop-out per market (what it offers, live numbers) and, where it can
      be wired safely, the real action (deposit / swap through our engine, the wallet signs). Top coins held show in the city.
   c. The four outer cities hold real-money markets too (new ideas that bring real money into buildings beyond pools).
   d. Picking a plot: the side panel gets far more vitals. Traffic gets stoplights. No "wand" beams over buildings — a light per activity.
   e. The landing: the loop circle is GONE (2026-10-21, next move = one HUD chip); skyline towers clickable, never clipped (fixed).
2. 🛡 SECURITY: the site and the AI must not hoard data (caps / TTLs on every store, logs and model memory); the HQ Security tab gets real
   web3 defence (signature replay, drainer / phishing detection, approvals, RPC + API abuse, bot / scraper detection) that LEARNS from each
   attack (fingerprint → auto-block rules, honeypots). Hard limit: FEELESS never attacks anyone back — "hack back" is illegal and can hit
   innocent relays; the response is trace, block, rate-limit, tarpit, report (abuse contacts, chain explorers), never firing an attack.

OPEN, owner's FOURTH list (2026-10-21 night) — DO THESE FIRST, in this order. Owner's rule for all of them: RESEARCH the best web3 / degen
sites first (what the greatest do), then build a FEELESS twist — never scratch-built from nothing; every page COMPLETE top to bottom
(every tab, sub-page, chat and click-through under it), never a nice header over basic content.
1. 🏙 FAMILIA, finish the whole thing top to bottom:
   a. The MOB landing (Fee City tab) end to end: the city + real-time data + HOW FAMILIES WORK shown visually (not text), and everything
      below it (the old podium stage, Board, Live, My family, Wars) brought to the city's level. No dead-styled cards.
   b. Fuse Arena: show the REAL Fuse cards (their card face / legs, `CardArt`), ranked brackets + TOP-POT battles ($1K+ once real money is
      live), a battle chat per fight, any player can fuse any player (not only a Don's call-out). The stadium + board look richer: an even
      layout, a chat under the board.
   c. City: plots are hard to click (towers cover neighbours) — bigger hit areas / pick through buildings; Cartel Docks is congested
      (16 cartel towers) — thin it; vitals panel = categories (DONE 2026-10-21: WHO · STRENGTH · MONEY on the stage, not in the 3D).
   d. Family badges / cards / customization: redo from researched references (no "spinning rainbow" upgrades); MOBhouse styles.
   e. ALL of FEE in Familia: $FEE, FeeCat, Fuse, Launch, Fee-Back… each as a fun mechanic in the city, not a link.
2. 🪟 NEXA + 🧠 Brain:
   a. NEXA's chat: narrower, with a vitals column on the LEFT (live log / her read / load), richer read + on-chat load vitals.
   b. NEXA must run a read and TRADE fast (with FeeCat) — no 40 s+ waits on the i5 (prompt cache, smaller reads, stream, a fast path).
   c. FULL LM Studio + llama control in one better view: every Load (context, GPU offload, KV cache quant, flash attention, max concurrency,
      prompt cache, reload) and Inference (temperature, top-p/k, response length, preset) setting, read live + applied (the owner's approval
      for reloads) — replaces the partial Model Rig.
   d. Brain themes + EVERY chat's theme picker (inbox included) redone meta (researched, not the current set).
3. 🪟 Raids: DONE 2026-10-21 — played on the target's 3D block (`RaidStage`: shield halos, crew at the kerb, effects on the struck building,
   action bar keys 1–4, siren beam over raided plots in the city). Next: defenders see the incoming raid on THEIR block in the city view.

OPEN, owner's THIRD list (2026-10-21 evening) — TOP PRIORITY = FAMILIA design + mechanics, then senior code clean-up:
A. 🏙 FAMILIA = a next-level Sim City / Godfather-PSP game (free play AND pay-to-play, fair for both). The city IS the landing page.
   DONE 2026-10-21 (slice 1, points only): Fee City = the landing (`FeeCapital.jsx`: 24 premium plots ×2.5, drawn stadium = Fuse Arena,
   The House, Creator's Mansion, Rug Shield HQ, Launch Pad, Fee Plaza, live billboards, traffic) + 4 outer cities (`cities` in
   family_world: Pump Harbor, Raydium Heights, Bonk Bay, Cartel Docks), city rail + one street chat per city (`city-<key>` rooms, lines
   carry `fam` tag), tap a plot → camera flies in + vitals card, ❓ How it works pins, 🎖 Ranked (rank_of: Street Rat → Kingpin I–III,
   top 25 = Don of Fee City), HQ › Build › 🏙 Familia (live rules + planned $ prices + paid-hit calculator = `paid_hit_payout`),
   `family_fuse_ok` (±1 coin, MP needs 2K). DONE 2026-10-21 slice 2: FAMILY FUSE (`family_fuse.py` + `/familia-fuse/act`): Don /
   Underboss challenge with a card their members built (Fuse designs + Fuse cards), paper or MP (stake held, min from HQ), rival answers
   ±1 coin, the Arena's six duels at true fills, pari-mutuel member-point bids (5 % house), played on the stadium pitch + `FamilyFuseBoard`,
   Fuse tab › Arena strip. NEXT: raids/hits played
   in-city (no 2D cards), MOBhouse styles, building ACTIVE/SHUT by funds, MP-only buildings, launched coins as Fee City buildings,
   then real-money family wallets after the custody pick.
   - FEE CITY (main, biggest, needs an epic name on screen): real bridges, land, atmosphere, the most expensive / profitable real-money
     plots, the creator family's HQ, FEELESS's biggest money-makers shown live as buildings, and a big real-looking STADIUM = FUSE ARENA.
     Plus 4 smaller cities, ONE chat box per city. Every plot / building: lore, hover, click → zoom to it with live vitals + P&L on top.
   - No 2D cards for hits / raids / bounties / alliances: they happen IN the city (chess / card play like Godfather PSP, harder + more
     fun than Loaded Lion). Ranked like Call of Duty: one ladder for family-wallet $ rank, one for MP rank.
   - Family wallet on creation: $25 = $5 to FEE + $20 into the new family wallet. Paid hits / raids / turf shakedowns pay from it; payout
     = a small % of the target's wallet scaled by power gap (a $5 hit on a 10× bigger family ≈ $0.0001; equal-rank families ≈ $0.05–0.10
     cap). Needs a custody decision (Circle / program-owned) — see `docs/REAL_CATS.md` pattern; never ship half.
   - Plots/buildings can be plugged to real pools / vaults (v2 / v3 / newest staking / compounding); ACTIVE or SHUT DOWN by funding;
     members add their own money → auto-calc share, or pool it to strengthen the family. Buy buildings with MP too (expensive, MP only
     makes MP). Coins launched on FEELESS appear in Fee City. Expansions. 2 families per wallet (owner sets the limit + every fee).
   - FAMILY FUSE: Fuse Arena battles (paper or SOL/USD) only in the stadium + in the Fuse tab; coin counts must match (same, +1 or −1);
     spectators bid; MP Family Fuse needs 2,000 MP.
   - Town looks: 3 atmospheres + 4 paid / ranked; MOBhouse = the private family chat (sewing shop → mansion → Tesla-style lot), with
     vitals side panel. Chat badges per family, bounty + alliance with real mechanics. MP / season points boost things site-wide.
   - HQ › 🏙 Familia owner control center (creator wallet only): pricing, limits, fees for every hit / raid / pool / expansion.
B. 🧹 Senior code clean-up: dead files removable from Code health through the gate; fewer lines; Lag catcher + Support clean.
C. Pages called out as below bar: Rep (fake "3D", left-boxed, slang with no real vitals) · FEEd (needs a real dev/null × X FEELESS twist,
   pop-out, live vitals) · MOB · Launch click-through pages (the hero alone isn't the page) · Trade › Gas (meta upgrade of SmolRefuel) ·
   FeeCat lore + other tabs (only the top was redone) · Roadmap / whitepaper as a real 3D view (text in a dropdown) · profile settings
   (online status etc.) · NEXA chat too wide, model-loading vitals · OSSY / G4 duo chats · Agents need a clean new build (no strat fits all).
D. FeeCat idea: a trading cat + an AI agent that pair and talk (Pinata-agents style, our twist); merge "Create a Cat" vs "Launch a Cat".
E. Lag catcher › a "build a better coin" track: BTC-like fundamentals for FEELESS coins / pools.
