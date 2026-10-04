# FEELESS — working rules

Degen trading terminal (Solana-first). Every feature ships **one and done**: styled, fast, tested, pushed.

## How to work (save usage)
- Be brief with the owner. Report what changed, what was tested, what wasn't. No essays.
- Stay on the task asked. No side quests; note unrelated issues in one line.
- Read only what you need (grep first, then targeted reads). Batch independent commands.
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
- Palette: black/very dark green surfaces, live royal green `#19f58f` accent (matches the logo), `#ff8fa3` danger, `var(--gold)` warn.
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
- Music: link-only adds (title via noembed), last song restored on refresh but autoplays only on the day's first load,
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

## FUSE (fused pools)
- `backend/fuse.py` (pure, tested) + `/api/reputation/fuses*`: baskets of 2–6 live pools with weights; index = 100 at
  launch; A–F score with reasons; pool picker drops parked/fake pools (no volume or liquidity > 2,000× volume).
- Fuse in = one normal wallet-signed swap per leg (no new money path). A Fuse buy counts only if the signature is the
  buyer's confirmed FEELESS trade; the creator's cut (≤50% of that FEELESS fee) is tracked earned/paid/owed.
- Fuse Lab (`FuseLab.jsx`) starts in HQ › Fuse (`<FuseLab call>`: 6 pools, auto|manual weights, publish as a Fuse) and
  reaches traders as Trade › ⚛️ Fuse Lab tab (`TradeTabs`, `?tab=fuse`; 3 pools). Caps are HARDCODED server-side
  (`fuse.USER_MAX_LEGS`=3 / `MAX_LEGS`=6). Pools: `/fuses/discover` (popular/yield/deep/new); preview: `POST /fuses/preview`
  (`fuse.preview`: split, $/day, blended APR, grade, 24h backtest, size guard >1% of pool liquidity).
- 🧬 Fuse Evolution (HQ, `FuseEvolve` → `POST /admin/fuses/evolve` → `fuse.evolve`): genetic search over baskets of
  the chain's best ~40 live pools. Genes = strategy (`fuse.STYLES` yield/momentum/steady/degen), pools 2–6, generations,
  budget ($5/$20/$100). Fitness = grade + APR + momentum + calm − size-impact − duplicate coin − fee drag (network fees on
  tiny buys). Elitism (best never drops), seeded, tested vs brute force. Champion → "Load into Lab" → one-click Fuse in.
  Ranking only: never claims profit, never trades by itself.
- Fuse HQ (`backend/fuse_hq.py`, pure + tested; `FuseHQ.jsx` in HQ, `FusePnl` on Trade › Fuse Lab):
  real Fuse P&L (`POST /fuses/position` counts a leg only if its sig is YOUR confirmed FEELESS buy; cost/tokens from that
  record), paper Arena (champion → $5 for 24h, settles once; style is *proven* after 3 settled runs with avg > 0),
  Bloodline (saved champions seed gen 0), Health (published Fuse vs fresh champion → BEATEN ≥10%).
  Traders get ONE button: `POST /fuses/best3` ($5/$20/$100) breeds with the arena's proven style (else yield), cached 2 min.
- Chat: `/fuse [name]` posts `⚛️ fuse:<id>`; `FuseChatCard` (≤340px, shared `lib/fuseFeed.js` poll) → amount → FuseGo.
- HQ › Fuse = `FuseDeck`: KPI ribbon (real P&L, 24h outlook from the ARENA only — `fuse_hq.outlook`, never a
  promised return), left rail (Breed & fuse | HQ · P&L | Published | Vault, each with a one-line explainer), one panel at a
  time). Admin fuses up to 10 pools (`fuse.MAX_LEGS`; `fuse.min_share` keeps big-fuse weights distinct). Champions render
  as `FuseCard` (MetaCard: drag tilt + ⟲ flip, back = why it won) with the admin `FuseExplainer` pipeline; traders get the plain-words `FuseExplainer` (APR est. = LP fee rate, not
  paid to holders; fee drag on tiny buys). Explain every money mechanic on the surface that uses it.
- Prebuilt rail (`FuseRail`, `GET /fuses/prebuilt`): best basket per strategy bred from `_fuse_candidates()` (5 min cache),
  flip cards + arena record + "Use this"; traders 3 pools, HQ 3/5/8/10. Shown in BOTH the trader Lab and HQ Lab.
- Fuse chat: ONE room `fuse-lab` (`FuseSide`, beside the Lab; stacks under 980px via container query) ⇄ Holders board
  (`GET /fuses/holders`, verified positions, P&L %), transform slide between panes.
- Receipt: `FuseGo` shows BEFORE (per leg pay/get/FEELESS fee/network/impact, total cost %) and AFTER (`POST /fuses/receipt`
  = `fuse_hq.receipt`: quoted vs exact fills, slippage). Never scrollIntoView inside clipped cards (scrolls the card).
- Hourly loop `_fuse_autopilot_tick`: settles 24h arena runs, enters each strategy's champion once/hour (`auto: True`),
  then `_shield_alerts` → admin inbox once per newly flagged bot. Published Fuses rank by `fuse_hq.trust_rank`.
- Hover explainers: `[data-tip]` inside `.fe` / `.frail` (CSS tooltip, focus too). Explain every gene/control there.
- Card backs = money math (`cardMath`): per leg weight %, $ slice of the budget, its 24h move in % and $, total, fee drag,
  "$B → $end". Always labelled a replay of the last 24h, never a forecast.
- Basket limits (`fuse_hq.clean_guard/guard_check`, `POST /fuses/guard`, 60s `_fuse_guard_tick`): TP / SL / trailing on a
  position; free to set, fees only on the actual Unfuse; fires once → inbox + phone with `?unfuse=<id>` (opens the exit).
  FEELESS never signs for the user.
- Fuse cards NFT (HQ › NFTs, `FuseCardMint`): Metaplex Core collection once, 1/1 card per published Fuse
  (`/fuse-card/{fid}.json|svg`, `fuse_hq.card_meta/card_svg`); creator cut is paid to the card's on-chain holder
  (`_fuse_pay_to` via DAS getAsset, 5 min cache).
- Creator season (Trade › Fuse side panel › 🏅 Creators, `GET /fuses/creators`, `fuse_hq.creator_board`): weekly, ranked by
  buyers' real P&L; own buys excluded, ≥2 buyers to rank.
- Tooltips sitewide: `data-tip="…"` + `lib/tipLayer.js` (one fixed bubble on body, never clipped). Don't build CSS ::after tips.
- Find my best 3 deals a card per budget ($5/$20/$100); the Lab's "Your Fuse" shows a live FuseCard of the picks.
- Never label pool fee APR as the holder's earnings: Fuse holders earn price moves only ("24H REPLAY $"); APR is "POOL APR".
  Fuse vs Vault with live numbers = `VaultMath` (`GET /fuses/yield-math`, APR capped 400% like the engine).
- FeeCat Fuse: NOT built on purpose — only after a strategy beats holding SOL in the arena over weeks.
- One-click Fuse in (`FuseGo` + `lib/fuseGo.js`): quote+simulate every leg in parallel (refresh 10s), review must match
  (`orderMatches`), ONE `signAllTransactions`, then `/execute` each leg. Same trading path as Quick trade — no new money path.
- Built and paid out in HQ › ⚛️ Fuse. System map: `docs/ARCHITECTURE.md`.
- FUSE Vault (one contract, ≤3 v2/v3 pools, SOL in → shares, fees in SOL to Trading & fees › Vault fee wallet):
  engine `backend/fuse_vault.py` (spec, tested) ⇄ program `contracts/fuse_vault` (Anchor; math.rs mirrors it —
  change both together). v0.1 = custody/shares/fees/admin on LOCALNET ONLY; pool adapters + audit before any
  deploy. v0.1 NAV = SOL held in the `vault_sol` PDA (no external value reporting; adapters deferred). Tests: `cargo test`
  + `anchor test` on a local validator (see its README). Never deploy or fund it without the owner; no instruction may
  set a position value that wasn't deployed.

## Badges + quest engine
- `backend/quests.py` (pure, tested): 40 animated badges = FEELESS set (`q-*`, everyone) + Fee Reserve set (`frsv-*`, every
  task needs $FEE held). Each badge = tasks on metrics computed only from FEELESS records (verified trades, chat, calls,
  invites, follows, points, check-ins, $FEE held) — nothing self-reported. Daily + weekly quests reset 00:00 UTC / Monday.
- Endpoints: `GET /api/reputation/quests/{address}` (60s cache; rarity 10 min), `POST /quests/checkin` (chat session),
  admin `GET|POST /admin/quests` (edit name/tier/tasks/on-off, add badges, validated) and `POST /admin/quests/grant`.
- Earned quest badges join `wallet_badges` (chat chips + profiles) with their art. HQ › Badges › Quest engine edits all.
- Tool quests: case files opened + war room trades via `POST /quests/event` (war room trade must be one of your verified
  FEELESS trades; case files once per wallet per day, ≤30/day); alerts counted from your push watchlist.
- Perks (`quests.PERKS`, editable per badge in HQ): fee discount (best of tier/promo/badge, read from cache so quotes
  never wait, noted on the quote) and chat backgrounds. Only add perk kinds that something actually honours.
- Season: `QUESTS_PATH.season`, PAUSED until launch (no leaderboard, no trophies). Unpause in HQ › Badges on launch
  day; "Award week's top 3" writes `kind: 'quest'` trophies once per week.
- Coin logos sitewide = `tokenImageUrls(pair)` (DexScreener image → DS CDN → FEELESS `/token-logo` cache) via `TokenAvatar`;
  MetaCard `card.art` may be that array (crest falls through on error, then the glyph). Fuse cards show the top-weighted coin.
- MetaCard: never make absolute FX layers (`mc-sweep`, `mc-glow`) relative — they'd push the card's rows down.
- Unfuse: `unfuseOrders` (min(bought, held) → SOL) → `FuseGo side="sell"` (one approval) → `POST /fuses/position/close`
  (closed only by YOUR verified sells; realized $ from those records).
- Card auras: 15 live effects OUTSIDE the card (`card.aura`, `CARD_AURAS`/`Aura`/`AuraPicker` in MetaCard, `styles/auras.css`,
  backend `badge_cards.AURAS` validates). Picked in Card Studio (badge/season/week cards), Quest engine (quest badges — shown
  only when earned) and NFTs › Fuse cards (`POST /admin/fuses/{fid}/aura`). Particles: transform/opacity only, `--i` index
  for stagger, frozen under fx-lite / reduced motion. New aura ⇒ add to all three lists + CSS + test.
- MetaCard sizes: md is THE layout; sm/xs are the same card scaled with CSS `zoom` (never re-flow or hide its parts).
- Every badge renders as a `MetaCard` via `QuestBadgeCard` (art in the crest circle, alive when earned, back = tasks +
  perks). Chat chips show only the circle. Profiles showcase featured (else 3 rarest) quest badges as cards.
- Quest data is shared: `useQuests` (Badges tab, Trenches `QuestNudge`, `ReserveProgress` on $FEE + Fee Reserve, Season
  board in Leaderboard). Don't add a second fetch for it.
- No new tabs for features: Radar (Signals + Watching, held-coin signals first), Leaderboard (?lens=season|callers|wars|crew),
  Pump radar = `PumpHub` lenses Radar | Discover (`/terminal/discover` → Discover lens; particles in front, fx-lite off),
  plus its 🎯 Snipers out view.
- Badge editions: first 100 real earners of a badge are numbered forever (`quest_editions.json`), shown as #007 / 100. Fee-Back has the hover fee report (fees, fee-back paid/owed, % back, XP/rep/points).
- Art lives in `public/assets/badges/{feeless,frsv}/<id>.{jpg,gif}`: show the ~35KB .jpg poster; play the .gif only on
  hover/focus or in the detail view (`BadgeArt`). Never autoplay a grid of GIFs.

## Money rules (trading)
- 🔒 P&L NEVER includes fees, anywhere (live trades, Fuse cards, Arena/Prime, FeeCat): cost = money that REACHED THE POOL
  (`trade_fills.position` → `investedPoolUsd` / `realizedPoolUsd`; client `pnlSummary` uses them), fees live on the receipt
  (`feesUsd`, FeeCat `feesSol`). Value = on-chain balance × Jupiter live price. Phantom's chart price can lag ~0.5%.
- Engine: Jupiter Swap API primary (FEELESS fee into our SOL/USDC token accounts, capped priority,
  our broadcast). Ultra only as engine or opt-in fallback. Fallback off + Swap API down ⇒ trading pauses.
- Nothing trades fee-free except **buying** $FEE / FEECAT / rFEE. Coin→coin with no SOL/USDC side is refused.
- The wallet signs everything; the server verifies the signed message equals the quoted one; no resubmits.
- Only show or sign an order that matches the coins, side and amount on screen.

## 🏃 FUSE RUNNERS (degen engine)
- `backend/runners.py` (pure, tested): coins COME TO IT — every launchpad coin from `/api/market/feed` (trending + new,
  scope=launchpads, pre-bond + graduated, ≤48h) → `candidate()` → hard `GATES` (fail closed: unscanned = out; top10 <30%,
  insiders <15% / bundled <3, dev <10%, creator not flagged, flow 40–85% buys, mcap ≥$8K, vol1h ≥$5K) → `score()` with
  cited parts → lanes `scalp` (pre-bond 50–98% curve: all out at +50%, stop −25), `runner` (⅓ +50 · ⅓ +100 · trail 25 ·
  stop −30), `hold` (stayed 2+ rounds & score ≥70: trail 30 · stop −35). `next_round()` every 15 min keeps the best (streak).
  `play_exits()` + `proof()` = paper results over 24h; the Fuse button lights only at ≥8 rounds, avg >0, ≥50% won.
- Service: `_runner_live()` (30s cache, scans ≤16 busiest with ≤6s wait — never block the board), `_runner_tick()` every
  5 min (price paths) / 15 min (round). `GET /runners`, admin `POST /admin/runners/round`. Never call it "unbeatable".
- Runner add-on: `FusePreview.runners=true` bolts the round's top 2 runners on as a 20% slice (`runners.addon`).
- UI: `RunnersPanel` (HQ › Fuse › 🏃 Runners first; also Trade › 🏃 Runners tab; admin-only "fuse unproven" override),
  `styles/runners.css` (fire accent `--rn-fire`). Lab toggle "🏃 +2 Runners add-on".

## Fuse 🧬 page (BUILT)
- Sidebar `['fuse', 'Fuse 🧬']` (Audiowide via `.nav-fuse`) → `FusePage.jsx` (+ `styles/fusePage.css`), sub-tabs `?tab=`
  home (landing, the default) | lab | runners | arena | cards. Runner picks (≤3, `togglePick`) and "Load" (Featured) carry into the Lab. Trade page shows a
  "Fuse 🧬 →" banner instead of the old Fuse/Runners tabs.
- My cards = `LiveFuseCard` + actions: 💰 take profit (legs + 25/33/50/100%) · 💸 auto-collect · ⚖ rebalance (+ auto-rebalance
  alerts) · ⇄ switch (sell a leg + buy a mint, one approval) · 🎯 limits · ↩ withdraw. Alert links: `?tab=cards&collect=<id>&pct=`,
  `&rebalance=<id>`, `&unfuse=<id>`. Profile shows `FuseReceipts`. HQ: ⭐ Feature in Lab, ⚙ Runner settings, 💸 default.
- 💸 Auto-collect (`fuse_hq.yield_due/collect_pct`, `POST /fuses/auto-yield`, admin `GET|POST /admin/fuses/auto-yield`): when a
  card's HELD value ≥ base × (1 + at%) [default 50, 10–1000] → ONE alert with a pre-filled Collect profit that sells only the
  gain; a partial close re-arms from the new held value. NON-CUSTODIAL: it never sells by itself — the holder approves.

- Runners tab = live discovery (`RunnerPicker` ← `GET /runners/discover`, 20s cache): gated coins only, tagged by source
  (`runners.SOURCES`: 🏟 arena pick · 🔥 lit card · 🚀 pump scan top 8 · 🎯 snipers out 6h · 📣 creators' pick = sharp callers
  ≥3 calls & ≥50% hit, or runner legs of published Fuses). Sorted by source count; 2+ sources glow. Filter chips, ≤3 to card.
- Arena tab (`ArenaBoard`) reuses RunnersPanel's `ProofRing`/`Countdown`/`CoinRow`/`LANES`: round card lights (`is-lit`) when
  `proof.lights`; each newly dealt round under lit proof is saved (`runners.lit_card`, ≤30, 72h price watch) → lit-cards list
  with `card_result` % since lit + "Use". Mid-round, ONE failing pick per tick is auto-swapped (`runners.swap_failing`) for
  the best passing runner; swaps are listed with the failed gate and counted honestly in `proof` (swapped-out mult kept).
- Arena tab (`ArenaBoard`) = STAGE first: `GET /fuses/arena` → `mega` = HQ cards flagged 🏟 Show on Arena (FuseBuilder,
  `arena: true`) + runner cards that lit after their rounds (+ the live round as a "proving" card when the stage is empty).
  Each card's `activity` (`fuse_hq.activity`: 24h FEELESS buys, buyers, $ flow, index move → calm/warm/hot/blazing) drives
  HARD-CODED effects (`TIER_FX`: aura + ember count, heat glow, shock ring, page-wide `.ar-sky`); `MegaCard` = FuseCard (tilt/flip).
  Lit/round → runner picks; mega → Lab (users get the top 3). Then `<RunnersPanel />` (old look) + strategies.
- Runners tab: a full card (3 picks) renders as a prebuilt FuseCard (`RunnerCardFull`) → Lab. Lab has a 🏃 Runners lens.
- Leg caps (`fuse_hq.legs_ok`, `legCaps`): traders 3 pools + 3 runners; HQ 12 legs any mix (6/6, 12 runners).
- Bundle pricing (`fuse_hq.bundle_bps`, fee cfg `bundle`, HQ › Fees › 6, `POST /admin/fees/bundle`, public `GET /fees/pricing`):
  a card bought all at once (FuseGo sends `bundle`=legs on /quote) pays a flat $/coin (default $0.10), ≤ maxPct of a leg; legs
  > maxLegUsd pay the normal %. Staff (HQ) bundles pay 0 FEELESS fee. Live "⚛️ Fuse fees" tile (`GET /admin/fuses/fees`).
- Card rules (`fuse_hq.CARD_RULES/clean_rules`, HQ › Fuse › 🃏 Card rules, `GET|POST /admin/fuses/rules`, public `/fuses/rules`):
  auto-profit LEVELS traders pick (no free typing), counted from the confirmed buy + its FEELESS fee and fired only when up
  after exit fees (`exit_fee_usd`); per-card mode 🔒 hold / ⇄ swap (`POST /fuses/mode`; swap = `swap_suggest` → one alert per
  weak leg with a pre-filled switch `?tab=cards&switch=<id>&out=&in=`); Arena: every open trader card shows until withdrawn,
  ≥ topTierPct takes the top tier; Fuse Fee-Back (`card_feeback`: share of fees paid, unlocks after holding, + loyalty, + Arena,
  capped; book + "Mark paid" in HQ). Profile shows `FuseHeldCards` (held P&L) above receipts.
- ⚡ Copy cards: Arena trader cards → "Fuse this too" loads the Lab with `incoming.copyOf` (banner `fl-copy`); FuseGo sends
  `copyOf` on `/fuses/position`; the original owner (never self/linked) earns `copyPct` (card rules, ≤50%) of the copier's
  FEELESS fee (`fuse_hq.copy_cut`, in the Fee-Back book as `copyUsd`). Cards show copies + $ earned.
- Swap streaks (`fuse_hq.swap_streak`): switch-ins counted from card events; 🛡 Survivor ≥1 · 🔥 Phoenix ≥3 · 👑 Immortal ≥5,
  only while the card is up; +5 activity per swap (max 15) on the Arena. `StreakBadge` on Arena + My cards.
- Fuse runs in the background: `_fuse_warm_loop` (25s) rebuilds the runner board, discovery, Arena stage and season board in
  its own task (`_FUSE_FORCE` contextvar) while viewers read the last copy — endpoints answer in ms. `_runner_loop` wakes when
  the next round is due. Frontend loaders ALWAYS do their first load; only repeat polls pause while the tab is hidden.
- Lit cards stay strong (`runners.rebuild_lit`, each tick): 2+ strong + 1 weak → the weak coin is swapped for the best passing
  runner (result kept, counts as a swap streak); fewer than 2 strong → taken down (`downAt`, off the stage, kept in history).
- 🏆 Fuse seasons (`fuse_hq.season_start/season_board`, `GET /fuses/season`, hourly `_fuse_season_tick`): weekly from Monday
  00:00 UTC, cards opened that week (≥$1, no bots) ranked by real P&L %; top 3 crowned once (inbox + phone), +seasonBoostPct
  Fee-Back on the card, 🏆 crown on My cards, past champions on the Arena board.
- 🎯 Card plan (`fuse_hq.clean_plan/leg_limit_hits`, Lab `CardPlan` → FuseGo `plan` → `/fuses/position`; edit via
  `POST /fuses/plan`): per-coin TP / SL (runners start at their lane exits), auto-profit level, on profit 💸 collect or
  ♻ compound (alert → pre-filled rebalance), hold / swap. Coin limits alert once with `?collect=<id>&pct=100&legs=<pair>`.
- Runners lens rows are live (`liveRunner` + shared `useLivePrices`): price, mcap scaled by live price, round / 5m move, flash.
- Day theme: card faces (`.mc-face`) are art and stay dark — the global day ink skips them (`:not(.mc-face *)`); selected
  `m-seg` buttons are deep green + white in day.
- LIVE everywhere: `lib/fuseLive.js` (`liveRowPnl/liveBook/liveStagePct`) + shared `useLivePrices` — My cards header, profile
  held cards, Arena stage %, runner tiles, Runners panel rows and Lab runner rows all move with 10s prices (`fl-tick` flash).
- Season race (`fuse_hq.rank_moves`, background-only `_season_race`): rank-change ticker on the Arena; a card entering or
  leaving the top 3 alerts its owner once. 💬 Card chat: every Arena card has room `fuse-card-<id>` (normal chat).
- ♻ Compound streaks (`fuse_hq.compound_streak`: bursts of top-ups; Compounder/Snowball/Diamond while winning, +5 activity
  each, max 15). Lab plan options read "💸 Auto TP" / "♻ Auto-compound".
- ⚛️ Fuse score (`fuse_hq.fuse_score`, `GET /fuses/score/{addr}`, profile `FuseScore`): perf ≤75 (real P&L, medals, copies,
  streaks, holding) + rep ≤25 (trust × 0.25); trust gets `trust_from_fuse(perf)` (−3…+6) from the CACHED score only (no loop);
  holders' scores refresh in the warm loop every ~5 min. Bots score 0.
- FeeCat Fuse edge (`feecat_brain.fuse_edge`): coins that failed a runner gate are skipped (gate = reason); coins N Fuse sources
  like get ×(1+0.05N) ≤1.2, never while discipline is cutting size; setup memory learns the `fuse` tag.
- 🔔 Bond run (`runners.bond_check/near_bond`, cfg `bond*`): pre-bond and EVERY box ticks — curve ≥90%, buys ≥60%, 5m green,
  1h vol ≥$10K, snipers out or top-10 <20%, clean creator → +15 score + its own source; `BondMeter` lights box by box.
- Card P&L NEVER includes fees: legs use `fuse_hq.pool_usd` (poolUsd = $ at the pool) for buys and sells; auto-profit triggers
  on the price move; fees show only on the receipt at fuse-in / sell (`FuseGo` before/after, with each coin live).
- ⚔ Battlefield: `runners.auto_card` (cfg `autoCoins`/`autoPools`, default 4 + 3; traders still load 3 + 3) dealt once per
  round in the warm loop (`_arena_auto_refresh`, kind `auto`); `pair_battles`/`settle_battle` + background `_battle_tick`
  (cfg `battleMins`): pairs by heat, bigger move since the bell wins, W/L/D records (`battleRecord`), winners alerted.
- Lab card plan: one-tap TP/SL presets (`PLAN_PRESETS`: Safe / Balanced / Degen / Lanes) + the per-coin list in a dropdown.
  My cards: 📈 per coin opens its chart (`openWarRoom`) with your confirmed buy marked. `TAB_TIPS` explain each tab.
- Stronger runners: tunable flow/bundles (`minBuyShare/maxBuyShare/minTrades1h/maxBundled`), kill-switch gates (top-10 spike
  `maxTop10Jump`, dev sold) from `_runner_track` history, curve speed + buyer acceleration, 👀 Bond watch 75–89% (rep-confirmed:
  `smartMin` smart FEELESS buyers via `_smart_buyers`, no flagged funders, dev not sold; half boost) + 🔔 Bond run ≥90% (8 boxes),
  `bond` lane exits. Self-tuning lanes (`runners.lane_proofs/lane_weights` → `next_round(weights=)`). ⚡ `runners.RECOMMENDED` +
  `suggest_cfg` → `GET /admin/runners/suggest`, HQ `EngineSuggest` (Apply = merged cfg), hourly admin nudge.
- Chat: `_fuse_chat` (once per key) posts battle results, bond runs (coin room + `fuse-lab`), FeeCat's book, season crowns.
- ONE season: Fuse feeds the quest engine (`quests` metrics `fuse_cards/fuse_survivors/battle_wins/feecat_beats/season_medals`,
  5 Fuse badges with art from `scripts/gen_fuse_badges.py`, weekly `fuse`/`battle` quests, events → season XP). 45 badges total.
- ⛓ FUSE Card program `contracts/fuse_vault/programs/fuse_card` (LOCALNET ONLY, not audited/deployed): one PDA per card, coins in
  card-owned token accounts, rules HARD-CODED (3+3 / 12 admin, profit levels, TP/SL ranges), owner-only toggles (auto TP,
  auto-compound, swap mode, per-coin TP/SL), owner can always withdraw, keeper can ONLY return coins to the owner's wallet and
  only when the owner switched auto on (TP / SL / profit / compound — a standing order, no click each time). Selling on-chain
  needs swap adapters + price checks (next, behind an audit). `cargo test -p fuse_card --lib`.
- Fuse tab FX (`FuseFx`): synthwave grid floor, lightning strikes, rising sparks — transform/opacity only, off in fx-lite.
  Forensics scan the 28 busiest (background); HQ sees every passing runner, traders the busiest 24.
- 💸 Weekly Fuse payout (HQ › Fuse › `FusePayouts`, `GET /admin/fuses/payouts/plan` → `lib/batchSend` ONE approval from the
  fee wallet → `POST /admin/fuses/payouts/paid`): plan frozen at today's SOL price (`fuse_hq.payout_plan`, dust < $0.05 waits,
  FEELESS + bot wallets never paid); the server credits only system transfers whose SOURCE signed the tx, × plan price, ≤ owed
  (`credit_paid`), refuses reused/failed/unrelated txs, notifies each paid wallet. Admin inbox gets "payout ready" on Mondays.
- 🐱 FeeCat challenge (`fuse_hq.feecat_week_pct/beats_cat`): her week = average trade (exits that week + positions opened that
  week, sim). Season board shows it live; cards above it are marked; the weekly tick records winners (`catChallenge`), notifies
  them, +8 Fuse score per win (max 16).
- 🧠 FeeCat learns from users (`backend/crowd.py`, pure): traders scored on VERIFIED FEELESS buys ≥24h old (win = ≥ +10%);
  elite = ≥6 scored, ≥55% won, avg ≥ +10%; `GET /crowd/elite-flow` (counts only, no wallets; rebuilt ~10 min). FeeCat
  `crowd_edge` ≤ ×1.15 + setup-memory tag `crowd`, never while discipline cuts size. Tests stub `_feecat_raw` / `_sol_usd_live`.
- Fuse tab look: blackish-purple tokens scoped to `.fuse-page` (night), `::before` sky + `::after` drifting nebula (clipped),
  violet `m-live` banners, breathing violet edges on cards, electric title (`fp-zap` + `fp-bolt`), real 3D helix `DnaHelix`.
- 🐱 FeeCat on the Arena (`_feecat_card`): her open SIM book as a card with her record (win %, realized SOL, lives); tests must
  stub `_feecat_card` (never reach the live service). ▶ Card replay (`GET /fuses/replay/{kind}/{id}`, `CardReplay`): 24h of
  15m closes per coin + the card's moments as markers; lines reveal via a clip-rect scaleX.
- Copy: Runners/Arena say "we run $5" (never "paper"); a missing live price shows "—", never a fake 0%.
- Pump Pulse sitewide: every `TokenAvatar` shows a pink `PulseDot` while the coin pulses (shared batched `lib/pumpPulse`).
- Prebuilt rail budgets: $1 / $20 / $100 or a custom $ (debounced 250ms); server breeds for the nearest bucket, Fuse in
  uses the exact amount. Pools-per-fuse segment is HQ only.

## Coin verification + coin badges
- `backend/verify.py`: coins EARN and LOSE the check and coin badges (`COIN_BADGES`) the same way — recomputed each run
  (6h TTL); `transitions()` logs earned/lost with the reason into verify.json `history` (shown in `VerifyReport`).
  A granted gold check is suspended while a `CRITICAL` gate fails (mint/freeze/creator/liquidity); official coins keep gold.

## Bot shield (our defender) — ties into rep, rewards, Fuse
- `backend/bot_shield.py` (pure, tested): 8 engines — reward_farmer, clockwork, batch_cluster, wash_trader, dust_farmer,
  chat_spam, referral_farm, fuse_self_deal — each with cited evidence. verdict bot ≥75 / watch ≥45. `_shield_of(addr)` (5 min
  cache). Ties: trust score (bot −40, watch −15), wallet case evidence, check-in rewards refused for bots, Fuse creator cut
  = 0 for self-buys and bots, Fuse creators gain rep per outside buyer (`_fuse_rep`). Check-ins store `checkinAt` timestamps.
- HQ › Safety › 🛡 Bot shield (`BotShield.jsx`): scan all, per-engine counts, evidence, Clear / Confirm / Back to auto
  (manual always wins; FEELESS wallets never flagged). New farming pattern ⇒ new engine + test, never a hand-rolled check.

## Reputation / investigation
- `backend/investigate.py` is the scoring core (pure functions, tested): every score point is cited evidence
  (claim + source). Wallet cases, coin risk (mint/freeze authority, holders, forensics), funder clusters.
- `/api/reputation/case/{address}` builds a case for a wallet or a coin; the UI opens it anywhere via
  `investigate(address)` (`components/CaseFile.jsx`). Rug shield, radar and alerts must cite the same evidence.
- FEELESS wallets (`_protected_wallets`) can never be blocklisted or scored as suspects.

## Layout
- Helius key: `HELIUS_API_KEY` or `HELIUS_RPC_URL` (SOLANA_RPC_URL may point at another RPC).
- Backend services (restart all after backend changes: `bash scripts/start-backend.sh`):
  `server` 5001 (market + trading), `reputation_service` 5077 (social, fees, admin), `feecat_service` 5088, `candles_service` 5099.
- Frontend: CRA + craco on 51367. Styles mostly in `frontend/src/styles/terminal.css` (append scoped blocks).
- HQ settings that matter at scale (keys, engine, fees) must be visible in its **Core** group.

## Shipped from the last plan (keep these rules)
- HQ › Fuse rail is GROUPED (`FuseDeck` panels = [key, label, node, blurb, group]): LIVE (🏃 Runners, ⚔ Arena ops) ·
  BUILD (🧬 Breed & fuse, 📣 Published) · MONEY (💰 HQ, 💸 Payouts, 🃏 Card rules) · SYSTEM (⚡ Engine, ⛓ Contract, 🏦 Vault).
  Settings are mounted ONCE, in their own panel (`FuseAdminSettings` → Engine / Card rules / Payouts); `FuseOpsPanels` =
  `ArenaOps` (stage mix, battles + bell, log, season vs FeeCat) + `ContractStatus` (static, never claims deployment).
- FUSE Card localnet test `contracts/fuse_vault/tests/fuse_card.ts` (5) + vault (5): `solana-test-validator --reset` then
  `anchor test --skip-local-validator --provider.cluster localnet`. On-chain selling = DESIGN in the contract README.
- Profile top = `TraderCard` (from `/fuses/score` → `trader`: medals by place, battles W/L/D, catWins, held P&L, copies) +
  Share GIF + 𝕏 post intent.
- Coin edge: `GET /api/reputation/edge?mints=` (`backend/coin_edge.py`, 15s/coin, caches only; `intel=1` ≤3 coins runs the
  scan) + ONE client poller `lib/coinEdge.js`. `usePumpPulse`, `useSnipersOut`, `useVerified`, `fetchIntel` read it. New
  per-coin data ⇒ add it to the edge record, never a new poller. (Snipers-out LIST view keeps `useSnipersOutList`.)
- My cards = 3 quick actions (💰 Take 50% · ⇄ Switch · ↩ Withdraw all) + "⋯ More" (auto-collect, rebalance, limits, replay,
  charts). Rotation is hard-coded: ONE switch-in per card per 24h (`fuse_hq.next_switch_at`, `lastSwitchAt`; top-ups don't
  count; staff exempt); 🔒 Hold = switch by hand · 🤖 Auto-rotate daily = one pre-filled swap alert per day (`_fuse_swap_tick`).
- Lab: "🔍 Explain this card" (`CardExplain`, portal; click outside / Esc closes): every coin line in plain words.

- 🎚 Risk dial (`fuse_hq.RISK_DIALS` ⇄ `lib/riskDial.js`, change both): Safe / Balanced / Degen sets every coin's TP/SL, profit
  level, collect/compound, rotation and max runners. `clean_plan({risk})` expands it SERVER-side (nothing free-typed); Lab
  CardPlan + My cards use `RiskDial`; tuning anything → `custom`. Engine dial (`runners.ENGINE_DIALS`, HQ ⚡ Engine,
  `POST /admin/runners/config {dial}`). Proof: `runners.dial_proof` → `/fuses/arena.dials` → `DialBoard` (Arena + HQ).
- Replays use `fuse.replay_window` (leg `replayPct`/`replayH`): pools younger than 24h use 6h → 1h → 5m, never DexScreener's
  since-launch h24. Bugs: same crash + page = one report ×count (`_bug_key`); `.hot-update.js` crashes are never filed.
- STILL ONE-CLICK: every card action + alert is an approval until the owner confirms they work; only then do configs go auto.
- Notices: after-notices `fuse-card` (opened / profit taken / withdrawn / switched in), coin signals `fuse-signal`
  (`_card_signal_tick`: bond run, snipers out, runner now failing a gate — coins on YOUR open cards) — all in the existing
  inbox Trading lens. NO P&L numbers in any notice text; P&L lives in Fuse › My cards and the profile only.

## Checkpoints (shipped, keep true — update this list only with STRONGER checkpoints, never weaker)
- 🛡 Guard (`backend/guard.py`, tested): write floods → 429 breather; HQ sign-in brute force → that IP's admin cools 15 min;
  suspects + evidence wait in HQ › Security (`GuardPanel`) — NO auto-blocks, every block/lift is an audited admin approval.
  XFF only behind our proxy (`FEELESS_TRUST_PROXY=1`, rightmost hop). Internal/private IPs never limited.
- Lab preview: a picked runner that just failed a gate is SKIPPED + unticked with its reason (`droppedRunners`), never an
  error wall; fresh grads are addable. Quick trade shows ≈ $ under You get / Min received.
- Guard also runs on `server.py` (5001, trading); every service's CORS reads `ALLOWED_ORIGINS` — SET IT to the real domain
  before launch (default '*' is flagged in HQ › Security). Settings › Reduce motion stops every animation (tips.css).
  Day theme: `.m-pos/.m-neg/.up/.down` deep green/red outside card faces. Chat hides calls on dead/rugged coins (`deadCall`).
- 🔐 Roles are SCOPED (`ROLE_SCOPES` in `_require_admin` → `_role_gate`): moderator/marketing reach only their sections (tabs
  filtered client-side too); every grant needs the creator's fresh signature (`grant_message`, 10 min). Owner-only money =
  `_require_owner`. Every `/admin/` route must call one of them (audit script: grep routes without `_require_`).
- 🪙 Coin drawer (`openCoin()`, one `CoinDrawerHost`), 🪪 trader chip (`TraderChip` ← `/fuses/ids`, cache-only batched poller).
- 🪟 Card window (`CardEarnings` with actions/legs/autos): last-24h autos = the holder's inbox alerts for that card
  (`fuse_hq.card_autos`), ❄ freeze per coin (`POST /fuses/freeze`; `swap_suggest` skips frozen), ＋ Top up (`topupOrders`:
  equal / weight / one coin → normal buys merged via `/fuses/position/switch`). Still one-tap — FEELESS never signs.
- ⭐ Prime tiers (`arena_prime.py`): 💎 Diamond / 🥇 Gold / 🔥 Blaze, 3★+ coins only (`stars`), major anchor never rotated or
  stopped, card floor −20% (cfg `floorPct` ≤25) → anchor, re-deal next day as a NEW run (past runs on the record), honest
  record (good days ≥ +10% of last 10, worst %). "8/10 days up 10%" is a TARGET the Arena proves, never a promise.
- ⭐ Prime = SOLID HOLDS: Diamond 3 majors + PUMP (no runners) · Gold 2 majors + pool + 1 runner · Blaze 1 major + pool + 2
  runners; stops 12/15/20%. `exit_plan` (live momentum): 🚀 ride = only the cost comes out once 2×, house money rides ·
  🏦 bank 75% when fading · 💰 gain otherwise; early cut at half the stop when fading. Tick ~50s, rotation 15 min–48 h (seg +
  typed minutes in HQ). Every coin keeps `firstEntry` + `at` → card window shows entry + a per-coin rundown.
- ⭐ Prime = 5 tiers (`arena_prime.TEMPLATES`, each with a `why`): 💎 Diamond young coins → 10× (1 major + 3 young, TP 900,
  SL 35) · 🥇 Gold · 🔥 Blaze · ⚡ Next Level (4 runners, TP 300) · ♾ Everlasting (4 majors + PUMP, sl 0 = never stopped).
  "Young" = pre-bond passing + `runners.fresh_grads` (graduated <48h, failing ONLY pre-bond) — also a 🎓 source on the Runners
  board so it never sits empty. ONE clock: `rotateHours` (HQ › Rotate every, seg or typed minutes) rotates weak coins AND re-deals floored cards; replacements are ARENA-backed first (`arena` flag from `_prime_candidates`: round picks, lit cards, stage/battle card coins), then other 3★+. Stop modes cfg `slMode`: ⇄ replace · 🅿 park (sell to SOL, keep the slot in `parked`, rebuy at
  the stop-out entry when not fading) · ❄ hold. HQ › Arena: FeeCatTune + `PRIME_META` one-click meta config.
- Holder scans: an incomplete scan (no top-10) retries after 60s; launchpad supply = 1B when RPC blanks (`scanned` needs top10).
- Vault ← Arena: VaultDesigner "Start from an Arena card" loads a Prime card's majors + pools (never runners) as vault pools.
- Profile receipts = dropdown per withdrawn card (`FuseReceipts`): legs + tx links, moves timeline, fees apart (FEELESS from
  the ledger + network estimate, explained), Share GIF + 𝕏. Badge icons are unique (test).
- Prime live %: `revalue` uses `baseUsd` (+ `extraUsd` cash/parked) when set → real-time % vs what the card STARTED with;
  no live price yet → server numbers. Crest shows `fallbackGlyph` (ticker) when every logo URL fails. Aura particles are
  HIDDEN (not frozen) in fx-lite / reduced motion — frozen dots read as "stuck". Card backs (`.fcd-back`) scroll (pan-y).
- 🔧 Runner auto-widen (`runners.widen/widen_level`, `_runner_widen`): <3 passing → soft gates (top10, mcap, vol, flow) one
  step looser (max 3, floors), 8+ passing → step back; safety gates never move; `/runners.widen` → chip on the live board.
- Profit trail = centered pop-up (`.ce.is-pop`, blurred shade, `body.ce-open` pauses page FX, solid shade in fx-lite) + Share.
- Share GIFs: `DESIGNS` royal/nebula/gold/ice/blaze/synth (`lib/shareGif` THEMES + `designFx`), picked in the preview.
- Vault prebuilt cards (`VAULT_PRESETS`): Huge Stable · Blue-chip Blend · Pump Economy · Degen Yield → one tap fills the designer.
- Card pricing reads PER COIN (`legFee`): flat $/coin · `maxPct` cap on small coins · normal % over `maxLegUsd`; >5% total
  warns with the coin size where the flat fee starts. Prime tiers are distinct MetaCard builds (`TIER.look`: design + rarity +
  colours), and lite mode keeps a static tier ring. 🐱 FeeCat weekly note (`fuse_hq.feecat_weekly`, Monday, once per holder,
  no holder P&L). Tests: real Ed25519 HQ sign-in (`test_guard`), BEFORE/AFTER receipts for buy + sell (`FuseGoFlows`).
  Test venv = `.venv` (has pynacl + base58 now); live services run `backend/.venv`.
- Lite mode (auto via Lag catcher) hides tier/aura FX — when the owner says "no design", check fx-lite first.
- Sidebar = 12 entries (`lib/hubs.js` HUBS + `HubTabs` at the page top): Pump radar|Launchpads · $FEE|Fee-Back ·
  Leaderboard|Badges|Seasons ("Season & ranks") · Whitepaper|Roadmap|Learn ("Docs & roadmap"). Old URLs still work; new pages
  join a hub instead of adding a sidebar row. Roadmap = 11 missions (`MISSIONS`, honest LIVE/TESTING/BUILDING/PLANNED + meter);
  whitepaper v1.2 (`test_whitepaper` imports + renders the PDF — an apostrophe inside a '…' chapter once broke it).
- ⭐ Showcase: any bred champion → published Fuse with `arena: true` in one click (Published keeps 🏟 on/off).
- 🔧 Engine AUTO-STRENGTH (`runners.auto_pick` → `_engine_auto`, every ~15 min round): switches to the PROVEN better dial
  (≥8 rounds, avg>0, ≥2 pts ahead), audited + admin inbox; toggle `RUNNERS_PATH.autoTune` (HQ › Engine). Advanced runner
  settings sit behind ⚙. Lab lens 🚀 New majors (`fuse.risers`: ≤14d, $800K–$50M, vol ≥$300K, liq ≥$100K). HQ
  'Published' is now 🧪 Engine playground. Prime rotation 5m/15m/30m/1h; Prime coins open their chart.
- 🧪 Engine playground (`GET /admin/fuses/playground`, `EnginePlayground`): counts, READY-for-Arena (`fuse_hq.playground_ready`),
  21 engine-cycled scenario cards (`runners.scenarios`: 12 TP×SL exit combos + 3 dials × 6h/24h/72h), dial table, change log.
  Auto-strength needs the SAME dial to win in ≥2 windows (`auto_pick_multi`). FeeCat self-tuning shown via `/api/cats/brain`.
  Real cards: `rotateHours` 1/6/12/24 + `slMode` sell/park/hold (park → `_fuse_buyback_tick` one-tap buy-back). Top-tier rounds
  (`rounds`, `roundPct`, `crown_round` 🏆), floored cards re-deal next tick, momentum for every coin from pool data.
- 🎯 PAPER = REAL: every paper buy/sell (top-tier `arena_prime.buy_px/sell_usd`, FeeCat entry + `_close`) fills with
  constant-product price impact vs the pool (quote reserve ≈ liq/2) — what a wallet would get. Fees stay apart (feesUsd/feesSol).
- 💡 Engine learning loops (every ~15 min round): scenario winner → runner exits (`runners.exits_pick`, same TP×SL best in 24h AND
  72h); dial auto-strength (`auto_pick_multi`); gate regret (`log_drops`/`gate_regret`: gates that stop 3× coins); top-2 scenario
  cards dealt onto the Arena stage (`_scenario_stage`, kind `scenario`) → battles always have ≥2; best scenarios → publishable cards.
- 🔄 Top-tier phase cycle (Blaze + Next Level, `CYCLE` anchor→degen→anchor→mixed), one run. ⚔ Back a battle side (points only,
  `POST /fuses/battle/back`, `backRecord`), clash/tug animation.
- 🐱 FeeCat engine tune (HQ › Fee 🐱 AND › Fuse › Arena, `FeeCatTune`): best proven dial (`bestDial`: ≥8 rounds, avg > 0) + stronger
  settings applied in ONE click (server audits). Whitepaper v1.1 (`backend/whitepaper.py`, served to web + PDF) covers
  FUSE cards, Runners/Arena/Prime, automation + contract, bot shield, guard/roles — keep it short, update per feature.
- Vault designer + Card rules: every number has a $ example; Vault math uses the replay window and drops ±95% outliers.
- Runners: pre-bond lives on volume (log $1h volume part; thin pre-bond curve gets half points).
- Style understanding: HQ panels = numbered steps or grouped cards, plain-words header line, `data-tip` on every field,
  a live "$ example" under each input, money in SOL AND $. Tier FX = own layers (`pt-*`), transform/opacity, off in fx-lite.

- 🃏 Arena cards: engine scenario cards get simple degen names (1–2 emojis, `runners.CARD_NAMES`, unique per round via `card_name(.., used)`)
  + a dial look (`dial_of`: safe/balanced/degen → `d-*` FX layer + config chips TP/SL/⟳/stop mode, `card_cfg`). They go to the 🥈 RUNNERS-UP
  bench (`bench: True`, `/fuses/arena.bench`), never the stage; HQ audits + publishes (`dial`/`cfg`/`fromScenario` on the Fuse) → stage.
  `runners.battle_seats`: stage first, bench fills empty seats, MAX 2 battles (4 cards). Playground best scenarios render as real FuseCards.
- ⚔ Battle bars on TOP: 💰 BUY BACKS a/b (+$) = buying the card (`FusePositionIn.back` → `battles.paid`, never mixes with free backs) and
  ⚔ BACKS a/b (free). Backing is season XP: quests DAILY `battle_back`, WEEKLY 3× `back_win` (`backLog`/`backWins` → `_fuse_quest_stats`).
- 🔁 Card rounds (`fuse_hq.ROUNDS_*`, `POST /fuses/rounds`): 5 auto rounds per card (rotation / buy-back alert window = 1); +5 = pay
  (SOL transfer the holder signs to the fee-wallet owner, `paid_lamports` on-chain, sig never reused) or compound pays (owed until the next
  profit take, one pack at a time). HQ › Fees › 7 (`/admin/fees/rounds`, owner only). Main fee save keeps `bundle` + `rounds`.
- 📖 Meme terms (`backend/meme_terms.py`, `_meme_tick` ~5 min, `GET /meme-terms`): learns new words daily from launches + chat (known
  slang explained; unknown = 🌊 ticker wave or 💬 chat slang). Rep page v2 (`styles/repPage.css`, `.rep-v2`) + trench dictionary cards.
- ⚠️ NEW runners (`runners.new_runners`, `/runners/discover.newRunners`): ≤3h old, site + X at launch, creator not suspect (clean first),
  top10 ≤25 / dev ≤5 / ≤1 bundle / buys ≥55% / vol1h ≥$3K — Lab runners lens section right after the round.
- FeeCat page v2 (`styles/feecatPage.css`, `.fc-v2`): readable sizes, solid-fill tabs, live KPI tiles, rejection bars, her brain strip.
  Her P&L label = price moves, fees apart (money rule). Chat bond-run token cards carry the coin (no "Unavailable" block).

- ⇄ Card clock: `fuse_hq.ROTATE_OPTIONS` 5m/15m/1h/6h/12h/24h (`rotate_hours` snaps client floats); swap alerts + rounds use each card's
  own window. Per-coin stop mode `coinModes` (`POST /fuses/coin-mode`, `coin_sl_mode` beats the card's slMode) + ❄ freeze in the card
  window. HQ tier cards: per-coin ❄ freeze + own stop mode (`arena_prime.set_leg`, admin prime `{leg}`), frozen = never rotated/stopped.
- 🧪 Playground versions: same scenario = one bloodline, v.01/v.02… (`scenarioVersions`, `runners.tag_versions`); hover = scenario combo +
  where it's listed (🏟 stage / 🥈 bench / not listed); Arena bench cards show the same v.0x.
- Logos: `tokenImageUrls` has `KNOWN_LOGOS` (SOL, $FEE) first; every picker uses `TokenAvatar` (full fallback chain), never a bare letter.

- ⚙ Per-coin user configs (card window ⚙): own TP / SL (`legGuard`) + replace clock (`coinRotate`, `fuse_hq.coins_not_due` → swap tick
  skips) via `POST /fuses/coin-mode` (also stop mode). ✏️ Playground "Edit in Breed" (`feeless:fuse-deck-go` + `feeless:lab-load`) →
  Lab loads coins + name + dial/configs, publish carries them. Fuse builder lives in ⚡ Engine (collapsed).
- ⚔ Backer season (`fuse_hq.backer_board/backer_prizes`): ≥3 backs to rank, most winning backs; Card rules `backerPoolUsd` (0 = off) split
  50/30/20 at the weekly tick → `backerPrizes` → owed in the Fee-Back book (paid with weekly payouts). Season board shows TOP BACKERS.
- 🐱 FeeCat fresh lane reads creator rep (`creator_adjust` via `/edge` runner.creatorRep): clean ×1.25 + cited, suspect/high → out.
- HQ › Fuse deck v2: 🗺 Overview first (grouped live tiles → panel), compact rail (blurbs on hover).

- ⚔ Playground battles (`backend/pg_battle.py`, `_pg_battle_tick` ~50s, `GET|POST /admin/fuses/pg-battles`, `PlaygroundBattles`): HQ
  ONLY, separate from the Arena. Best scenario cards fight paper rounds (5/15/30/60m) with real fills; TP / stop / dead (no 5m trades
  or volume for deadMins) coins swap for the best gated runner; bell → winners keep coins, losers re-bred; records; ⭐ publish winner.
- Profile: `MyBattles` (`GET /fuses/battles/{addr}`, battleLog keeps aKey/bKey) + "⚡ Fuse a card" `FusePopup` (Lab in a blurred pop-up).
- Lab: `CardPlan` is its own side card (`.fl-plancol`) beside the coins; per-coin `CoinExtras` (❄ freeze, ⇄ clock, stop mode) →
  `plan.coins` → `fuse_hq.coin_extras` → card `frozen` / `coinRotate` / `coinModes`. FeeCat Cat detail v2 (`.fc-v2` chart/controls).
- Card-open notice reads as ONE card buy ("Card bought in one approval: name — $A, $B …").

- 🔄 Round cycles: tier cards per-tier `cycles` (`arena_prime.CYCLE_MODES` off/classic/adaptive/safe/press, `next_phase`), 🔒 `trail`
  (a +50% run is sold before it's back under +5%), floored re-deal resets `roundStartUsd`. User cards `cycle` steady/adaptive
  (`fuse_hq.cycle_pick`: losing card → swap into a major). Lab + My cards + HQ Prime controls.
- 🏟 Arena flow: ⭐ tiers → ⚔ battlefield → 🏆 season → 🏟 cards that made it → 🎨 creator's pick → rest. Bracket (`runners.bracket_pairs/
  bracket_update/bracket_done`, `BATTLE_MAX`=3, `unique_cards`): winners vs winners, losers vs losers, 2 losses out, last standing crowned
  (`bracket.champions`), new bracket. Battlefield = fighters + HP bars + power board + champions. Arena Pick has a stable id `arena-pick`.
- 🎨 Creator's pick (`POST /admin/fuses/scenario-pick`, `creatorPicks`): runner-ups stay in the engine; only picked ones are dealt to
  the Arena. New HQ Fuses default `arena: true`; staged cards newest first.

- ⚔ Bracket pool = stage cards + ⭐ tier cards (`fighterOnly`, own section on top) + 🏆 the engine's top playground battle winner
  (`pg_battle.champion`: ≥2 wins, W>L — the only engine card that reaches the Arena by itself) + 🎨 creator's picks. `BATTLE_MAX` = 2
  (4 cards PvP), `upNext` queue, 🔮 bracket calls (`POST /fuses/bracket/pick`, one per bracket, right = `bracketWins` → weekly quest
  `bracket_win` 150 XP), champions keep `legs` → 👑 Buy the champion. ⚙ `CardConfig` on every card (fighters, power board, stage) →
  ⚡ Copy to Fuse Lab with configs (`incoming.cfg` → plan). Playground records → Ready list (`pg_battle.ready_rows`).
- Runners source chips: empty ones hidden; 🏟 arena = runner coins on fighting cards; 📣 creators = passing coins in published Fuses.
  🚀 New majors = risers + `fuse.pump_majors` (Pump's top 15 graduated coins by volume).

- 🔒 HQ is SECRET: never write 'Cmd Ctr' / 'Command Center' anywhere (code, comments, docs, user text) — it's "HQ"; user-facing text
  says FEELESS. Production builds ship NO source maps (`frontend/.env.production` GENERATE_SOURCEMAP=false). Sign-in message = `FEELESS HQ`.
- 🧬 Card DNA (`backend/card_dna.py`): cycle · compound (smart/even/off) · payoutPct · clock · stop · trail on EVERY card; `assign` keeps
  each live card unique; tier cards per-tier `cycles`/`payouts`/`compoundStyle` (payout → `walletUsd`, counted in value); users: plan
  `payoutPct` + `compoundStyle` (+ 🎲 `GET /fuses/dna/unique`, 🧠 `GET /fuses/brain`); 🤖 `AutoSpec` = what the contract will run.
- 🧠 Engine brain: playground battle cards play their DNA (payout on TPs, compound off, hold stops, `cycle_rebalance` per bell with true
  fills), every bell scores traits (`dna.learn` → `brain`), a loser is re-bred with the winning DNA. 🩺 Doctor (`runners.filter_proof/
  doctor/apply_filter`, 14 `PICK_FILTERS` on each pick's entry snapshot): positive in 24h+72h → applied to rounds; nothing wins → sit out.
- 🚨 Rug shield (`arena_prime.RUG_LIQ`): liquidity ≤ half of entry → sold / swapped at once. 🔥 Comebacks + 👑 champion's share (2× copy cut).
- Runners: young graduates (<48h) pass the stage gate, 2 feed pages, 40 busiest scanned. Battle arena = one box, spotlight per fight.
- Fuse font token `--fz-font` (Bungee). Jest runs `--maxWorkers=50%` (load flakes). Profit trail 'book' (put in → held + taken = total).

- 👛 Fuse wallet (`backend/fuse_wallet.py`, pure + tested; HQ › Fuse › 👛 `FuseWallet`, owner only): a Circle SOL wallet funds the TIER cards
  with real money. `orders` = paper target − real `book` (sells first, buys sized by the card's real SOL, ≤ maxSwapUsd, SOL anchor = native);
  `check` (armed · not paused · per-swap · daily cap · max impact); `fill_from_meta` = the tx's balance changes ARE the fill; `sync_card` shows
  true units/entries/fees; top-up RESETS the card as a new run (`topup_card`, old run kept); ↩ defund sells back to SOL → paper. Every order /
  top-up / defund → `fuse_wallet.json` ledger (public last 12 with tx on the card = `realBook`). 🔒 SIGNING IS NOT ENABLED (`_fw_signer_ready()`
  = False; arming + top-ups refuse): adding Circle transaction signing needs the owner's explicit go-ahead (GO_LIVE A·2). Dry run =
  real Jupiter quotes, never signs. `calibrate(ledger)` → `arena_prime.IMPACT_MULT` + paper fee: paper learns from real fills.
- 🧮 Card money = ONE equation everywhere (`FuseMoney.MoneyMath`): PUT IN → IN CARD + PAID OUT = NOW; profit = NOW − PUT IN; fees apart.
  Tier cards: paid out = `walletUsd`, NEVER `takenUsd` (gross TPs mostly compounded back in — counting them double-counts). `summary.math`.
- 🔔 Rounds: every tier round opens with a 10s countdown (`RoundBell`, `nextRoundAt`, `BELL_SEC`); `_prime_bell_loop` wakes exactly when due
  (`_prime_tick_lock` — never two ticks at once); HQ `roundsPerRun` (∞/5/10/20/50) closes runs on the record.
- 📜 Arena paper books (`pg_battle.paper_book/paper_mark/paper_view`): every fighter gets $100 at TRUE fills (+ per-coin fee apart) when a
  battle starts (late fighters get one at once); battles SETTLE on the books; `GET /fuses/paper?key=` = live book + finished `paperLog`;
  📜 Audit on every battle corner; 🃏 `CardShowcase` (3-card 3D shuffle) above the battle.
- 💲 Fees: FuseGo sends `card: 1` on EVERY quote → staff (HQ/creator) pay 0 FEELESS fee on any card action; users pay `bundle.perLegUsd` per coin
  at first buy and `bundle.swapUsd` (default $0.10) per coin on card swaps/sells (`card_swap_bps`, capped maxPct). `autoFees` (default on):
  out of rounds + up more than the pack → the card pays +5 from profit (`auto_rounds`, owed till the next take). `fee_plan` → Lab `CardCosts`
  receipt before buying; HQ › Fuse › 💲 Fees = knobs + $ example + every fee paid (`fee_list`, clickable → tx).
- My cards: `CoinTable` (entry → now, $ in → now, %), `TrailSummary` (✅ did good · 🪙 stays · ✂ cut). Profile: `PrimeShowcase` (tier cards).
- ⚠ `.m-num` is a 22px display preset — inside dense rows give it `font-size: inherit` (fuseMoney.css does for its rows).

- 👛 Keeper signing is ON (owner approved): Circle sidecar `POST /sign` (sign only, never send) used by `_fw_sign` for the picked Fuse wallet
  id; pending saved BEFORE broadcast (no double-buys), `_fw_resolve` books the confirmed tx; every fill / failure → owner inbox (`_fw_notify`).
  First funding keeps the SAME card (coins, phase, clock, config), scaled to the $; time + P&L restart (`topup_card(first=True)`). Dry run
  shows `paper_status` (coins, weight, $ each at that amount) + real quotes. 🔒 Config locks: tier `prime.locks` (frozen full cfg per tier) +
  playground `pgBattle.locked` (coins + DNA survive a loss).
- 🎯 Card value = what SELLING pays (`arena_prime.value(.., liqs)`, leg `liqNow`); unknown liquidity = THIN (`UNKNOWN_LIQ` $20K, mirrored in
  `revalue`), never infinitely deep — that bug once showed $29 → $389K. The inflated runs are archived in `prime.archive`.
- 🔒 HQ ships as its OWN lazy chunk (loaded only after `/admin/whoami` says yes); `ReportBug` lives outside HQ. `test_admin_routes_guarded`
  fails on any `/admin` route without a gate (only the two yes/no checks are public, bool only).

- ⛓ FUSE Card v0.3 = REAL venue (`programs/fuse_card/src/raydium.rs`, `keeper_sell_cpmm` / `keeper_buy_cpmm`): Raydium CP-Swap CPI signed by
  the card PDA; pool/config/observation owned by Raydium + matched; reserves minus owed fees; Raydium's OWN TWAP (≥300s, spot ±10%, triggers
  read the TWAP; error ≤15s/window); real fee tier (trade + creator, rounded up). Shared bookkeeping `book_sell` / `book_buy` (both venues).
  Tests: 10 Rust unit (`cargo test -p fuse_card --lib`) + 4 against the REAL Raydium program on localnet (`tests/fuse_card_raydium.ts`,
  README v0.3) + the 14 older. `fast-twap` feature = TEST BUILD ONLY (45s window) — never deploy it. Devnet: `scripts/devnet-deploy.sh`
  (needs ~3 devnet SOL). `backend/tests/test_contract_pins.py` checks the Raydium discriminator pin.
- HQ component = `components/command/HqDeck.jsx` (export `HqDeck`); testids `open-hq` / `hq-shell`. The built bundle must contain zero
  "command center" / "cmd ctr" strings (check `grep -rli` on build/static/js before shipping).

- 🔁 Real-money card buys are all-or-nothing visible: `fuseOrders` per-coin `smartSlippage` (depth: 1/2/3/5%, runners ≥3%, sells +0.5%, ≤8%),
  "Min ≥" per coin before signing, every leg its own tx; after a partial landing `fg-partial` → ↻ retry ONLY the missing coins (+1.5%
  slippage, joins the same card via `/fuses/position/switch`, fills `missing`, not a switch) or ↩ sell back. `/fuses/position` takes
  `expected` → `pos.missing` (`fuse_hq.missing_legs`). `fuse_pnl` caps every leg by the wallet's REAL on-chain balance (`_wallet_held`,
  linked wallets, 60s; `fuse_hq.cap_to_wallet` → `heldShort`); tests stub `_wallet_held` (conftest).
- 🎯 Tier paper prices = Jupiter price v3 (`_jup_prices`, 20s cache) — what real swaps route at; DexScreener pair only for liquidity +
  momentum (a single pair sat 20–40% off on runners). Quote rows with |dev| > 10% = price-source gap, never teach `calibrate`.
- 📏 Paper ⇄ real quote audit (`_paper_quote_audit`, ~5 min): tier-card coins priced by the paper model AND a real Jupiter quote for the
  same $; `fuse_wallet.quote_row/paper_match`; calibration = real fills when ≥3, else quotes (`_fw_calibration`) → `IMPACT_MULT`.
- ✦ MetaCard designs + nebula · prism · plasma · matrix · vapor (`styles/cardDesigns.css`, `badge_cards.DESIGNS` mirrors, test).
  Tier looks: Diamond prism, Next plasma, Everlasting nebula. Battle showcase = real FuseCards; 📜 Paper audit (live card + trail)
  on battle corners AND every CardConfig. HQ runs as the CONNECTED wallet (`hqAddr`), never the profile's address.
- ⛓ Devnet: fuse_card `GKE9e3M8…` deployed + config → Raydium devnet. Devnet SOL via Alchemy devnet `requestAirdrop`.

- 🔧 Tier config FIX: a card whose DAY falls to −40% (`FIX_DAY_PCT`) is re-dealt into majors as a new run on the safe cycle
  (`cycleFix`, once a day, event `fix`). Rotation runs on the normal clock. Floor default 40 (range 5–40). 🏇 `RIDE_AT/RIDE_TRAIL` (+150% rides, sold 30% off its new high). Re-deals use
  `in_play` (value − paid out − parked; never double-count). The bell loop pre-warms candidates inside the 10s countdown.
- 🎛 Big engine cards: max 4 (`creatorPicks[-4:]`), each ≥ 6 coins; even the engine champion needs HQ ✅ approval; a scrapped (dead)
  strategy leaves the Arena by itself. Playground cards 6–12 coins (`pg_battle.coin_targets/widen/dead`).
- 💵 `HqRealCards`: creator / HQ wallets see the real tier cards in Fuse › My cards. HQ wallet tier rows show a 🧾 receipt.

- 🔔 Round = clock ends → 10s bell (`BELL_SEC`, server pre-warms candidates) → deal at `nextRoundAt`; `RoundBell` pulls fresh cards at 0.
- 💳 Prepaid swaps (`fuse_hq.clean_prepay/prepay_credit/use_prepaid`, HQ › Fees › 8, `/admin/fees/prepay`): a NEW card's first buy adds ONE
  SOL transfer (same approval) = perSwap × swapsPerRound × rounds; `/fuses/position.prepaySig` verified on-chain → `prepaidSwaps`;
  card swaps quote with `cardId` → $0 FEELESS fee while credit lasts; switch/close spend it. Staff never prepay.
- 🪪 Circle wallet profiles: `/admin/circle/profiles` + `/admin/circle/profile` (owner, own Circle wallets only) → HQ › 👛 CircleProfiles.

- 🏇 Hold rule (tier engine): ≥ +150% OR a whole round ≥ +80% (`roundMin`) → held (no TP / stop / rotation); held coins stay while
  ≥ +80% and not 30% off their high, else SWAPPED for the best coin of their role. Streaks (`STREAK`=3): 3 losing rounds → `cycleFix`
  safe; 3 winning → `lockRounds`=1 (no rotation / re-shape) + best coin `freezeRounds`=1. Every cycle shape ≥ 3 coins (`MIN_CYCLE_COINS`).
- 👛 The card gets EXACTLY what's funded: network fees + new-account rent come from the wallet reserve (`apply_fill` → `rentSol`).
  Dry run shows card $ + fees (network + rent for new coins). Limits have plain-word explanations on screen.
- 🖥 Always-on host: `deploy/Dockerfile` + `deploy/run-all.sh` (all services + loops + Circle signer, auto-restart) · docs/ALWAYS_ON.md.
  ONLY one backend may run against the Fuse wallet.

- 🛟 Shapes + cycles (tier `PHASES` + user `CARD_SHAPES`): anchor · degen · mixed · 🛡 safest (3 majors + 1 runner) · ⚖ breakeven
  (1 high-vol pool + 3 high-vol runners, `byVol`). Cycles: classic/adaptive/safe/press/🛟 rescue (safest ⇄ breakeven)/🤖 auto, or a CUSTOM
  pick of ≤3 shapes ('degen,safest,anchor', `cycle_seq` / `valid_card_cycle`, `CycleBuilder`). Any card ≤ −50% (`RESCUE_PCT`) → rescue.
  Low churn: rotation swaps only coins ≤ −`rotateMinDrop` (10%); re-shape every `cycleEvery` rounds (6). Floor default 60.
- 👛 Fuse wallet fronts a tier card's network fees + rent for its first 5 rounds; from round 5 the card pays (`cardPays` on orders).
  Min order $0.75; user cards ≤ $5 need ≥ $0.75 per coin (Lab note + FuseGo blocks the slice).

- Tier live value includes PAID OUT (`primeRow.extraUsd` = cash + parked + walletUsd) — else "still held" reads $0. Tier paper fee = $0.01
  (network; staff pay no FEELESS fee). HQ `rescuePct` (30–60). Cards ≤ $10 need ≥ $0.50 per coin (keeper min order 0.50).
- ⏱ Playground plays EVERY round length (`allClocks`: 5 → 15 → 30 → 60 …), `clock_learn` / `best_clock` per length (HQ line).
- ⚔ Battle box show (`bf-show`: spotlight sweeps, sparks, arena flash; off in fx-lite) · power board ranked by `power()` score.

- 🗄 `backend/store.py` (SQLite, WAL, stdlib): `KV` (crash-safe JSON docs, one-time import of the old .json) + `Ledger` (append-only,
  never trimmed). The Fuse wallet lives there (`_fw_load/_fw_save`, every `_fw_record` row also hits the ledger table). Next stores to move:
  fee ledger, positions, runners paths (the 2.8 MB file rewritten every tick).
- 🧱 Code split, step 1: `chain_rpc.py` (RPC pool + `_rpc`) imported back into reputation_service (callers unchanged). Next: storage
  helpers → `core_store`, prices (`_fuse_pairs`, `_jup_prices`, `_sol_usd_live`) → `prices.py`, auth gates → `auth.py`, then feature routers.
- 🧠 `pg_sim.py` + `_pg_sim_tick` (~15 min, 300 sim cards on real recorded paths, fees per swap, own file `pg_sim.json`) → HQ `SimBrain`
  (apply clock + rotate-only-losers to the tier engine). Jest: `--maxWorkers=3` + `testTimeout` 30s (flake fix). Day theme: NO
  backdrop-filter on always-visible panels (was the day lag). Arena: `ArenaGuide` + jump bar; card config = live P&L + legend.

- ⏳ Why 5-min rounds failed = churn on noise. Patience: rotation only after `rotateConfirm` (3) losing rounds in a row AND
  `minHoldMins` (30) held; protection (TP/SL/rug/hold) still every tick. Sim proof on real prices: 5-min patient ≈ +5.6% vs churn ≈ −47%.
- 🔧 `_engine_self_fix` (after each sim run, `autoBrain`): 🌧 runner weather (24h sims ≤ −5% → `strictRunners`: vol1h ≥ $20K, buys ≥ 55%)
  + the brain's minDrop / confirm (median-ranked, ≥30 sims). Never the clock. Audited + `brain` event on tier cards.
- ⚖ Arena: playground (engine) cards ≤ number of Arena runner cards (lit / round / auto), max 4. 📜 Permanent record: every ended tier
  run → `card_records.db` (append-only) · `GET /fuses/record/{tpl}` · `CardRecord` on each tier card.

- 👛 Unlanded real buys: `sync_card` keeps `wantUnits` + `buying` (cost 0, card shows ⏳ buying…, never −100%) → `target` still wants it →
  keeper retries; engine compound feeds waiting coins first. `_fw_jup` backs off on 429/5xx; trail/totals = one row per tx; HQ › My cards tracker.

- 💧 Real buys need pool liquidity ≥ `minLiqUsd` ($20K default, Fuse wallet cfg) — thin/pre-bond coins stay paper-only; sells always pass.
  Real cards show SERVER (Jupiter) value only (`LiveFuseCard serverOnly`); SOL anchor cost = SOL left × entry.

- 🛡 Secure real buys (`fuse_wallet.buy_safety`): quote price ≤5% above market AND a read-only sell-back quote loses ≤6% (no honeypot /
  tax / one-way pool), else skipped + logged. Keeper retries 3× quote / 3× build+sign in-tick; `scripts/keep-alive.sh` restarts dead services.

- 🎯 Paper = real for tiers: EVERY tier rotates only into pools ≥ `minLiqUsd`; runners also need 1h up + ≥55% buys (confirmation). Cards
  carry `solStart` per run → `vsSolPct`/`holdSolPct` (tracker tile). Real card ⚙ Edit card (engine + cycle + lock + wallet). Card never pays rent.
  TODO: auto-close empty token accounts (rent back) · one tx per re-shape.

- 🔄 Every tier shape has ≥1 growth coin (`PHASES.growth`): anchor/safest = 3 majors + 1 NEW MAJOR, mixed = 2 majors + new major +
  runner, degen/breakeven = runners first. New majors (`fuse.risers`) feed `_prime_candidates` (`newMajor`). Adaptive rests only on ≤ −3%.

- 🪑 Bench (`fuse_wallet.note_miss/benched`): a coin whose real buy fails its checks 3× in 10 min is benched 1h for that card — never
  picked, and a buying leg is swapped NOW (`replace_leg`). Book saves use `_fw_keep` (never drop misses/bench). Slippage-rejected sends re-quote ≤3%.

- 💵 Real-money guard (`arena_prime.real_guard`, applied in `_prime_real_cfg`): the real card keeps ANY clock (5 min too) but can never run
  under hold 20 min (clocks ≤ 15 min) · 3 losing rounds · instant swap off or ≥ −10% · re-shape ≥ every 6 rounds. Why: a $7 card made 350
  real swaps in 39h (hold 0 + −5% instant swap). 🌦 Runner weather (`arena_prime.weather/weather_runners`, sims' 6h window, else 24h):
  rain ≤ −5% = real buys only strong (score ≥ 60) runners in pools ≥ `minLiqUsd` · storm ≤ −25% = new majors only; owner notified on change.
  Self-fix patience moves only when the same value wins 2 sim runs (`prevBest`). Chips on the tier header (`prime-weather`, `prime-guard`).
- 📡 Landing (`chain_rpc.broadcast`, `_fw_rebroadcast`): the SAME signed tx is re-sent to every RPC node every ~2s until confirmed or expired
  (idempotent). Ledger errors are split: "expired — never landed" vs "failed on-chain: <err>". Never re-sign to retry a pending order.
- ⏸ `lib/fxPause.js`: one IntersectionObserver adds `fx-off` to off-screen animated surfaces (`FX_SURFACES`) → CSS pauses them. New big
  animated surface ⇒ add its root class there. Never animate `background-position` (the battle floor did; it's a transform layer now).

- 💰 Deposit audit (`fuse_wallet.deposit_from_tx/sol_story`, `_fw_deposit_scan` every 10 min → `data/fuse_deposits.json`): a deposit = a
  confirmed tx the Fuse wallet did NOT sign that raised its SOL. HQ › 👛 shows DEPOSITED = cards + reserve + unassigned + spent, each
  deposit linked, and "➜ Put $X unassigned into <card>" (prefill only, inside `maxCardUsd`; the owner presses Top up). Top-ups never move
  SOL on-chain — they assign SOL already in the wallet, so "unassigned" is the owner's own un-assigned deposits.
- 🎯 Paper flat cost (`arena_prime.SPREAD`, `fuse_wallet.calibrate` → `spread`): swaps too small to move the pool teach the flat cost of
  swapping (median 0.38% over 357 real fills); only pool-moving swaps teach `IMPACT_MULT` (it was pinned at ×6 by $1 swaps).

- 🏁 Arena contenders (`backend/contenders.py` pure + tested, `_contenders_build` 30s cache kept warm by `_fuse_warm`, `GET /fuses/contenders`,
  `ArenaContenders.jsx` + `styles/contenders.css` `cn-*`): every pick list is a DIVISION (Anchors by volume · New majors · Top yield ·
  Deepest · Popular · ⚡ Fresh runners <12h · 🏃 Proven runners 12h+ · New 72h). Rows = score 0–100 with cited parts, ▲▼/NEW vs the last
  league, 🔥 #1 streak, seat: 🃏 on a card · ⏭ NEXT UP (best coin not on a card; one seat per coin) · chasing. Runner divisions need
  pumping (1h green, ≥55% buys, ≥$5K 1h vol). Next-up mints are `arena`-flagged in `_prime_candidates` (gates, floors, weather still
  apply). Stablecoins never compete. New pick list ⇒ new division there, never a separate ranking.

- 🏟 Arena = FOUR ZONES, one on screen at a time (`ARENA_ZONES`, `?zone=`, old names aliased; `zone=all` only for tests): 👑 Prime League
  (tier cards) · ⚔ The Pit (battles + 👑 `Throne`: one reigning card, the dethroned behind it, a repeat winner = 🛡 defended; then Main
  Stage + Creator's Cut) · 🏁 The Gauntlet (contenders + Crown Race season) · 🧪 Proving Ground (runner rounds, dials, strategies). New Arena feature ⇒ a zone or inside one, never stacked. The guide is closed until asked for.
- 💵 Real guard, part 2 (found by watching the live ledger AFTER part 1 — always re-check the ledger an hour after a real-money fix):
  `fixEvery` = a safe / rescue fix re-shapes a real card every 6 rounds, not every round (it sold + re-bought 2–3 coins every 5 min);
  `floorRestMins` 60 = a floored real card rests in its anchor before the re-deal; `REAL_RUNNER_AGE_H` 12 = real money never buys a
  runner younger than 12h, unknown age = out (a 20-min-old coin with a $534K pool went −99.99% in an hour: $0.74 lost).

- 🧹 Data cleaner v1 (`backend/data_cleaner.py` pure + tested, `_data_clean` hourly in `_fuse_warm`, admin `GET /admin/data-cleaner`):
  chat coin snapshots older than 1h lose `signals` / `quality` / `observedAt` (3.98 → 2.12 MB on the live file). Rules may only drop
  DERIVED or STALE data — never money records, message text or authors. Next rules: runner `paths` > 48h, dead `candle_ticks` pairs.

- 💵 Real rounds: `dealLeadSec` 15 = a real card's round is decided 15s before the bell (5s before the 10s countdown) so sells then buys
  finish inside it; a floored card shows 🛌 RESTING with a re-deal countdown (`summary.resting`, `RoundBell rest`) — never "dealing…".
  `REAL_MIN_HOLD` 15 (matches the 15M option). 🧠 Engine pick per clock (`pg_sim.by_clock` → `byClock` → `/fuses/prime.suggest` →
  `EnginePick` in Edit Fuse, one-tap Apply of minDrop + patience): each round length gets its own config; `profitable` only when the
  typical sim card on that clock ended up — otherwise the screen says "least-bad" and names the best clock.

- 👑 Throne v2 (`Throne` in FusePage, `th-*` in contenders.css): the champion's REAL FuseCard under voltage (`th-volt` bolts + ring,
  spinning rays), 2 challengers (`power()` top 2 not out) trading sides behind it, past champions beside it. The tall power board and the
  3-card showcase are gone from The Pit; `bf-rail` = ONE row of bracket chips (⚙ config · 🔮 call). Card wrappers that contain a FuseCard
  must be `div role=button` (the card has its own flip button — a nested <button> is invalid HTML).
- 🧱 Owner switches on the real card (Edit Fuse): `floorPct` (the WHOLE card, 15/25/40/60) and `floorRestMins` (off/15/30/60 — OFF by
  default: a floored card re-deals on the next tick; resting is never forced). ⚡ Instant swap is per COIN and must end in a coin: no
  eligible runner → the slot takes the best pool, not cash. When deleting UI, strip its CSS with a brace-aware pass — a regex once
  glued `body.theme-day` onto an `@media` line and silently killed the mobile rules.

- 👁 Seeing owner-only pages without the owner's wallet: `?viewAs=<address>` (`useWallet`, DEVELOPMENT build on localhost only, compiled
  out of production — check `grep -c viewAs build/static/js/*.js` is 0). It sets a read-only wallet with NO provider: nothing can be
  signed and every admin / money route still needs a real signed session. Use it to look at My cards before changing its layout. HQ
  itself stays behind the signed `whoami` check — never add a preview for it.
- My cards real-card header = `hrt-hero` (round bell · IN CARD NOW · ALL-TIME · VS SOL) + one `hrt-line` of details. Never nine equal tiles.

- ⚡ Fuse landing (`FuseLanding.jsx` + `styles/fuseLanding.css` `fld-*`, tab `home`, the default with no `?tab`): dark stage → spotlight
  (`is-lit` after 350ms) → the best live tier card spins 180° up to full size; front = card, back = its live book (tap / Enter flips);
  four floating notes; ONE row of four steps below. Every number is live (`usePrime` + shared `useLivePrices`), labelled 📄 paper or
  💵 real; it never promises a result. The stage and card stay dark in day theme (art).
- HQ nav = two levels (`cc-nav2`, `styles/hqNav.css`): a group bar (Core · Growth · Community · Safety) then only that group's tools.
- 🛟 Rescue OFF (`rescuePct` 0) = the card keeps ITS config: a running safe / rescue fix ends on the next tick and no losing-streak fix
  is armed. 🧊 Anchors cool like every coin (a sold major sits out 3 rounds while another major exists; SOL never "drops").
  Card cash can't go below 0 (a fee shortfall is booked to the reserve). The Gauntlet's pool divisions join the engine's candidate pools.
- Runner replays (`runnerReplay`): < 1h old → last 5 min, else last hour — never since launch ("+120,669% · $5 → $1,514" was a launch pump).

## NEXT SESSION — continue here (in this order)
00000. Owner: devnet SOL for `scripts/devnet-deploy.sh` (B·3), pick an auditor (B·4). Live test: HQ › Fuse › 👛 pick the Fuse wallet, dry run, arm, fund ONE tier with $20,
   watch the audit trail; raise caps after it proves out. HQ bundle pricing is $0.50/coin · 20% cap today (a $20 card = 18.75% over 10
   rounds) — recommend $0.10/coin · 5% cap · $0.10 per swap.
0000. Owner live test: per-coin ⚙ (card window + Lab), rounds pay/compound, buy & back, Edit in Breed → publish, playground battles,
   profile ⚡ Fuse pop-up. Then flip proven configs to auto.
000. Owner asks open: HQ › Fuse FULL layout redo (fit every panel; grouped rail is there, needs a real dashboard layout);
   FeeCat fresh-launch lane + clean-creator boost (site + X already required); card buy = ONE approval for every coin (FuseGo) but the
   receipt/notice should read as ONE card buy, not "5 coins"; one combined on-chain card contract = fuse_card program (localnet, audit first).
00. Owner asks still open: FeeCat terminal tabs UI redo (meta layout); FeeCat's OWN auto-strength (like `_engine_auto`);
   Engine playground: buy / publish / buy+publish with an amount + fee % for creator picks; Prime 'round count' that pushes the
   round's best card to the Arena stage; 2–3 live number animations on every % sitewide (`fl-tick` keyed by value);
   hosted background workers before deploy (engines already run in-process loops — move to an always-on host).
0. HQ › Fee 🐱: FeeCat builds + learns Fuse — she breeds her own card from `crowd` elite flow + runner/Prime proof,
   shows what she learned (setup memory tags `fuse`/`crowd`, dial proof) and proposes engine tweaks (admin Apply, audited).
   Prime ⇄ coin / 🃏 re-deal per tier already live (`arena_prime.replace_leg`, `POST /admin/arena/prime {replace|redeal}`).
0a. 🚦 HQ › Fuse › Contract has the REAL-MONEY GO-LIVE checklist (`GOLIVE_STEPS` adapter · twap · devnet · audit ·
   multisig; owner-only, proof required for devnet/audit/multisig, audited; READY only when all pass). Build next: the
   Raydium CPMM adapter + TWAP bound, then the devnet run.
   FUSE Card v0.2 BUILT (localnet, 14 tests): keeper_sell / keeper_buy / withdraw_quote, on-chain triggers from pool reserves,
   whitelisted `swap_program`, ≤3% slippage cap + balance diff, sl_mode payout/park/hold, compound cash only into card coins,
   `programs/mock_amm` (TEST ONLY). NEXT: Raydium CPMM adapter + TWAP/oracle bound → devnet → audit → owner deploy.
   (old plan:) (1) swap adapter = Jupiter CPI from the card PDA with
   `minOut` from an on-chain price check (pool reserves) + balance-diff assert; (2) keeper instructions `auto_sell_leg`
   (TP/SL/park per the owner's signed config) + `auto_compound` + `pay_out` (only to the owner's wallet); (3) slMode on-chain
   (replace / park / hold) mirroring `arena_prime`; (4) localnet tests with a mock AMM, then DEVNET with real Jupiter;
   (5) external audit; (6) owner deploys mainnet with a multisig upgrade authority + small caps. Never deploy/fund without owner.
0b. HANDS-FREE CARDS (owner ask): no signing per TP/SL — the card "nests" coins and pays the user back automatically. Only
   possible NON-CUSTODIALLY via the FUSE Card program (keeper returns to owner, owner toggles) + swap adapters + price checks,
   devnet run, external audit, owner deploy. Until then: one-tap alerts. Never hold user keys / never auto-sign server-side.
   Receipts: withdrawn cards → profile receipts as a shareable dropdown (swaps + history), per-card entries already tracked.
1. Prime: ⏸ PAUSE a coin (user + HQ):
   below its SL → sold to SOL and parked; re-bought only when price is back above the SL WITH volume (1h vol ≥ entry-time vol,
   buys ≥55%). Pure + tested in `arena_prime.py`, then the same "pause" as a one-tap alert on real cards (never auto-signs).
2. Prime runners: live check showed 0 runner legs (no 3★ runner passing) — confirm the runner board feeds `_prime_candidates`
   and that runners ≥60 score exist; otherwise fill runner slots with the next 3★ pool and label it.
3. One-of-a-kind tier animations per Prime card (Diamond prism shards, Gold coin rain, Blaze flame crown) — FX layers only.
4. FeeCat in HQ: auto-tune engine settings after analysis (proposes a cfg from `suggest_cfg` + dial proof; admin Apply,
   or auto-apply only inside hard bounds, every change audited).
5. Owner live test of one-click cards + notices → then flip configs to auto per dial proof.
6. Browser-verify: HQ › Security Guard, Access (signed grant), Vault, Card rules, Prime tiers, card window, chat ⚙.
