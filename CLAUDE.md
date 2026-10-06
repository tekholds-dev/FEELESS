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
- 🎛 Big engine cards: max 4 (`creatorPicks[-4:]`); even the engine champion needs HQ ✅ approval; a scrapped (dead) strategy leaves the
  Arena by itself. Playground field = 8 cards (`pg_battle.DEFAULT_CFG.cards`), each ≥ 4 coins with ≤ 2 pools (`fit_shape`), 4–12 coins.
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

- Tier card (Prime League) fits on screen: card · coins · PROFIT / PAID OUT / bell · buttons; everything else (round stats, good days,
  config chips, real book, record) lives in ONE `details.prime-more` drawer. Never stack new blocks on the card face.
- Profit trail opens with `ce-plain` — "IN PLAIN WORDS": put in → worth now → paid out → up/down $ (%) → fees apart — before any table.
- Landing v2: NO box (transparent stage on the page backdrop); the hero is the real `LiveFuseCard` with its tier `look` + `aura`
  (`TIER` is exported from ArenaPrime), `zoom: 1.45`; the big live % sits in the copy (`fld-hero`).

- 📊 Strategy board is OUTLIER-PROOF (`fuse_hq.robust_avg`, `arena_board` → `avgPct` + `medPct`): 10+ runs drop the best / worst 10%, fewer
  cap each run at +300%. `outlook.per1` = the MEDIAN run; "proven" needs average AND median > 0. Why: one freak run made HQ read
  "$1 → $62.62 a day" at a 38% win rate (real: every style negative). Any new "average of runs" must go through `robust_avg`.
- Two season tests use the real clock and fail for a minute at Monday 00:00 UTC (week boundary) — re-run, don't "fix" the engine.
- Landing headline: "MANY COINS, ONE FUSE." HQ Fuse deck: the five-step strip opens with "How the deck works" (help, not dashboard).

- 💰 PAYOUT RULE (real + paper): a card pays out ONLY what it is worth above the money the owner still HAS IN. Real = `fundedUsd`
  (`fuse_wallet.profit_available`); paper = the run's `startUsd`; the tier engine's per-coin payout is gated the same way
  (`V() + proceeds < basis` → the gain stays in the card). The owner takes principal out BY HAND only:
  ✂ `sell_leg_to_cash(..., pct)` 25 / 50 / 100 per coin or `manualSell {all, pct}` for every coin → card cash (`holdCashUsd` is never
  auto-compounded) → ↗ `fuse_wallet.withdraw_cash` (`POST /admin/fuse-wallet/withdraw-cash`, owner) moves that cash out and LOWERS
  `fundedUsd` by the same $ ($5 in, $2 out → principal $3, profit = above $3). No on-chain move: it becomes unassigned wallet SOL.
- My cards real panel v2 (`hq-real`): card on a lit stage (sticky) · hero · coin rows with ✂ 25% / 50% / All · ⚙ Config and 🧾 Activity
  as `details.hrt-fold` drawers with a one-line summary · sticky action bar. Sims skip paths with a > 4× single-step jump (`MAX_STEP`).

- ⚙ Edit Fuse v2 (`CFG_GROUPS`): tabs ⏱ Rounds · ⚡ Exits · 🧬 Shape · 🧱 Safety · 💵 Limits; one `ce-row` per setting = name + what it
  does on the left, choices on the right (never a wrapping grid of segs). New setting ⇒ add it to EDIT and to one group's `rows([...])`.
- 🪙 Size-aware real cards (`arena_prime.size_slots/fit_size`, guard `minCoinUsd` $0.75): a card holds only as many of its shape's
  coins as keep each ≥ $0.75 (first anchor + first non-anchor kept): $1 → 1, $1.6 → 2, $2.5 → 3, $5+ → 4. `underfilled` uses the
  same count. 🎯 Per-coin TP / SL on tier cards (`set_leg(tp, sl)`, `leg_tp/leg_sl`, `LEG_TPS`/`LEG_SLS`, 0 = follow the tier;
  selects on each non-anchor coin row). ⏱ `clock_rank`: clocks ≤ 15 min rank candidates by 1h volume + momentum, slower keep order.
- 🧹 Sell-all always finishes (`fuse_wallet.write_off_dust`, ledger side `writeoff`): while a card is selling out, a holding with a
  LIVE price worth < $0.05 is written off the book (coins stay in the wallet); no price = kept. A rugged coin's dust once left a
  card on "selling…" for good.

- 🪙 THE OWNER PICKS (never argue a card up in size or onto a slower clock): `coins` (Edit Fuse › Shape: auto · 2–6, `COIN_COUNTS`).
  A number = exactly that many coins at ANY card size (`grow_picks` adds the best coins not on the shape — runners, pools, majors;
  `fit_count` trims, keeping one anchor + one non-anchor); it switches the size rule off (`minCoinUsd` 0). Auto = size-aware.
  Keeper min buy goes down to $0.10 (a $1 card with 6 coins trades); the first 5 rounds of network fees are on the wallet reserve.
- My cards with no open real card: `RecentRuns` (owner) — closed real runs from `/fuses/record/{tpl}`, faded until hovered, `details`
  for the plain-words line. The real-card section has no box (page backdrop). Claude in Chrome can view the owner's My cards + HQ:
  navigation and reading only — never press a money / sign button there.
- HQ › Fuse wallet: arm / kill visible, `details[data-testid=fw-limits]` folds the six limits behind a one-line summary; numbers inside
  a sentence never use the 22px `.m-num` size.

- 🎲 Owner's degen setup is allowed on real money and PROVEN by `test_degen_5_min_card_freezes_a_runner_swaps_it_off_its_peak_and_instant_swaps_a_loser`:
  5-min rounds · patience 2 (`REAL_MIN_CONFIRM` 2) · hold 10 min (`REAL_MIN_HOLD`, option added) · ❄ freeze at +X% (`rideAt`) → swapped
  X% off its peak (`rideTrail`) · any coin at −X% swapped at once for a NEW coin (`instantSwapPct`). The SELF-FIX still never sets
  patience under 3 on fast clocks (owner can switch 🧠 Auto-tune off). Mechanics are proven; PROFIT never is — never say "100%".
- 🏁 Every candidate carries its Gauntlet `division` (→ leg → `DIVISION` chip on coin rows): every tier card is fed by every category.
- My cards, no open real card: `RecentRuns` = the tier's card FAINT with a CLOSED stamp (tap → run history), never a list. A sell-all
  writes its run to the permanent record itself (`closed: True`) — the tier tick only records runs it ends.

- 🎯 Owner's pick (`arena_prime.queue_swap/apply_queued`, `POST /admin/arena/prime {pickSwap: {tpl, pairAddress, to: mint|null}}`,
  `SwapPicker` on each real-card coin row): choose the coin that replaces this one from the LIVE Gauntlet lists; it is queued on the leg
  (`swapTo`) and swapped in at the next round bell, carrying the old coin's money, `picked` (a re-shape never drops it). Only a coin
  the league ranks right now can be picked; a real card's pick must clear the real-buy pool floor. `to: null` cancels.
- RPC: the keeper's dedicated endpoint is `SOLANA_RPC_URL` in `backend/.env` (QuickNode HTTP Provider URL works as is). The owner
  pastes it — never print or commit it. Restart all services after changing it.

- HQ panels fold, never delete: Engine playground keeps tiles + ready / proving on top; Doctor + battles · scenario cards · scenarios /
  dials / strategies · engine log are `details.hrt-fold.pg-fold` drawers (it was 3,828px tall). Fuse wallet's audit trail is a
  drawer too (`fw-audit`). Closed `details` keep their content in the DOM, so tests reading text still pass.
- `backend/.env`: `env_loader` keeps the FIRST value of a repeated key. A QuickNode `SOLANA_RPC_URL` saved below an old Helius line
  was ignored (Helius was out of quota: every keeper call 429'd). Keep ONE active `SOLANA_RPC_URL`; comment the others out.
  Jest flakes under load on this Mac when 4 services + the dev server + Chrome run (SwapWorkspace / FuseGoFlows) — re-run alone.

- 💵 Keeper RPC lane (`chain_rpc.rpc_priority` = `_krpc`): every Fuse-wallet call (balances, send, confirm, close) goes to the dedicated
  endpoint FIRST, ignoring the shared cooldown, retrying a 429 with a short wait, then the pool. Scanners keep using `_rpc`.
  New keeper code calls `_krpc`, never `_rpc` (a scanner burst once locked the keeper out of its own endpoint for 30s at a time).

- ⏱ EVERY TIER HAS ITS OWN CLOCK (`arena_prime.DEFAULT_CLOCKS` → cfg `clocks`, `tier_cfg(cfg, tier)`): Blaze 5m · Next Level 15m ·
  Gold 30m · Everlasting 1h · Diamond 2h. The tick, the view (`_eff`) and the bell loop (`rot_of(card)`) all resolve the clock PER CARD
  (real card = its own config, locked tier = its lock). A paper tier's editor saves `clocks[tier]`, never the shared `rotateHours`.
- ⚔ The Pit show: lenses `PIT_LENSES` (🔔 this bell · 5m · 15m · 1h) read the same fight over a window (`pg_battle.frame_pct` from each
  paper book's 1-point-a-minute `hist`, served as `frames`); the BELL still decides the bracket. 🎙 `pitCall` = one live line per fight
  from the numbers; 👥 `crowdShare` = free + bought backs (points only — it becomes the odds when real bids ship; never take a bid
  before that is built, audited and legal); final minute = `is-final`. Parallel brackets per timeframe are NOT built.

- ⚓ Anchors (`arena_prime.anchor_pool`, fed by `_majors_rows()` + deep new majors): EVERY real major in `fuse.MAJORS` (now + mSOL,
  bSOL, RENDER, HNT, POPCAT, PENGU, TRUMP, FARTCOIN, PUMP) and new majors with a pool ≥ $250K, ranked by what is MOVING (volume, depth,
  trend); never a dollar coin; SOL is one candidate, never forced first. `safe_anchor(leg)` = established major only: a NEW major in an
  anchor seat keeps the stop, the instant swap and the rug shield.
- RPC budget: scanners may use the dedicated endpoint only `SCAN_RPS` (8) times a second (`chain_rpc._scan_slot`); the rest of the plan
  is the keeper's (`rpc_priority`). The owner's editor once re-saved `.env` over the fix and brought a dead first line back — after
  any `.env` edit check `grep -c '^SOLANA_RPC_URL=' backend/.env` is 1. The dev server on :51367 is the owner's own `craco start`:
  attach with `preview_start {url}`, never start a second copy.

- 🔁 Trench fill loop guard (`trenchFillAt`): the FIRST fill after a card goes trench is immediate; after that one fill per round and
  never on a coin held < max(2 min, `minHoldMins`). Why: a trench coin that died on arrival was replaced by a normal runner, which the
  fill sold seconds later for the next trench coin — 2 real swaps a minute on the owner's $5 Blaze card (21 fills in one hour).
  `price_agrees` (scan price vs live price within 10%) gates every replacement; a > 50% "loss" in a leg's first 90s is a feed gap,
  never sold by the instant swap. Other sessions also push to main: `git fetch` + rebase before every push, and check
  `git stash list` — the owner's update script auto-stashes uncommitted work ("auto-saved by update.sh"), so COMMIT before long tasks.

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

- ⚓ Anchors are ranked by ACTIVITY (`fuse.rank_anchors`: turnover + 1h/6h/24h moves + buyers + depth, falling knife −15), never by
  name — SOL gets no head start. `fuse.MAJORS` = 27 real mints (BTC/ETH/SOL/JUP/PUMP/BONK/WIF/POPCAT/TRUMP/PENGU/FARTCOIN …, ≤30 for
  DexScreener's batch call); `ANCHOR_SKIP` (USDC, JitoSOL) never anchor; big new majors (≥$5M, ≥$300K pool, ≥1 day, ≤4) join the basket.
- 📉 Buy the dip + 💳 Dex paid: `fuse.STYLES` dip/meta (`dip_score`, `dex_paid` = header/boosts, a logo alone isn't paid), runner score
  parts + discovery sources (`runners.is_dip`), Gauntlet divisions `dip`/`paid`. ☠ `fuse_hq.retired_styles`: ≥3 settled runs with avg AND
  median < 0 → off the trader rails (prebuilt `retired`), autopilot probes it once a day so it can come back.
- 🎬 Pit reel (`PitReel.jsx`, `styles/pitReel.css`, scene class `prs-*` — never `pr-<scene>`, it collides with element classes): 6 scenes
  cycle every 3.4s in every fight's middle, the leader wins each. 📖 `FuseGuide` (`lib/fuseGlossary.js` = the ONE word list: cycles,
  shapes, clocks, stops, strategies, coin sources) opens from the Fuse tab tip line and the Lab card plan (pick a dial / cycle inside it).

- ⚔ Playground field: every card learns its OWN timeframe (`pg_battle.card_clock_learn/assign_clock` → `cardClocks`); a 🎨 pick goes to the
  Arena on that clock (`cfg.rotateHours`). A loser re-bred by the strategy that beat it is named its next version (`child_name`, `lineage`).
  Engine dials: 🧊 Cold Blood / ⚡ Voltage / 🔥 Inferno (`runners.ENGINE_DIALS`, `DIAL_LABEL`); user RISK_DIALS keep Safe/Balanced/Degen.
- 💵 Owner's ✂ cash (`manualCashSol`) is never re-spent by the keeper (`orders` sol_free, `sync_card` rebuy). 🩺 Real run report
  (`fuse_wallet.run_report`, owner `GET /admin/fuse-wallet/report`, `RunReport` in HQ › 👛 + HQ › Fuse overview `DeckAlerts`): fees % of money
  in, swaps/h, round trips < 30 min, fill vs market, failures, skip reasons, per-coin result vs holding SOL → flaws with their fix.
- 🎯 Real-card swap picker (`SwapPicker`): the Lab lenses + 📉 Dip + 💳 Dex paid + search any coin/CA; `pickSwap.toPair` lets any LIVE coin in
  (`_pick_row`: this mint's pool, price > 0, ≥ $25K, not a stable; real cards still need the real-buy floor). Lookalikes can't be picked.
- Fuse tabs = 4 (`TOP_TABS`: Start · Build · Arena · My cards); Runners is step 1 inside Build (`fp-steps`, `?tab=runners` still routes).
  🧲 Runners list is sticky (`runners.sticky`): a coin only being re-scanned stays as 🕘 rechecking (never addable); a real gate fail drops it.
- 💪 FeeCat auto-strength (`feecat_brain.strength`, hourly in `_tune_entries`, `cat.strength`, profile `strength`, HQ strip STRENGTH): her own
  24h (≥5) + 72h (≥10) record → 🧊 cold ×0.6 AT ONCE on a losing window · 🔥 hot ×1.15 only when BOTH windows prove it (avg ≥ +5%, ≥55% won,
  net > 0) twice in a row · never up while discipline cuts size. Sizing only; gates and discipline untouched.
- 👁 Safe HQ preview (no preview mode in the app): build → local backend with a THROWAWAY key in `FEELESS_ADMIN_WALLETS` (data/ is git-ignored,
  Mongo off, outbound blocked) → Playwright with a fake wallet + the signed session in localStorage; every request stays on 127.0.0.1.
- 💰 Paper payout line = everything PUT IN (`arena_prime.put_in`/`payout_line`: `putInUsd` set at the first deal, kept through every restart;
  real = `fundedUsd`). Only the part of a payout ABOVE that line leaves, measured on money still IN the card (paid-out money never counts).
  Screens show PUT IN from `summary.math.putIn` (paper) — a restart's lower start is "this run", never the put-in.
- 🪙 Owner-set real config keys (`prime.realOwnerSet`, saved by Edit Fuse) are never changed by the engine self-fix (`_brain_patch(owner_set)`):
  the owner's 5-min degen setup (patience 2, hold 10) sticks; the real guard floors still apply.
- 🃏 Card window (`CardConfig`, `styles/cardWindow.css`): the card itself big in its own design (FuseCard, flip) + side panes (coins · how it
  plays · 📜 trail from its paper book events). 📈 Pit live (`PitLive.jsx`): `RaceLine` (both fighters' % since the bell from `pg_battle.spark`,
  battles `spark`) under the reel + `CoinTicker` belt of both cards' coins on live 5m prices.

- 🏆 Arena LEAGUE (`backend/arena_league.py`, pure + tested; replaces the endless bracket in `_battle_tick`): a SEASON = ≤ 8 cards
  (`FIELD_MAX`, like the playground field), 7 bells (`ROUNDS`), every card on ONE $20 paper book for the whole season (`bookStart`
  subtracted per bell). Pairs by the table (1v2, no rematch), win 3 / draw 1; a book ≤ $1 or −75% over its last 3 bells is CYCLED OUT
  for the next playground card (`_league_playground`, best W−L). Last bell → champion crowned, new season, all books back at $20.
  League seats not on the stage still fight (`_league_extra` → arena `fighters`). Pit shows the table, rules line and cycled list.
- 🔁 Paper tier restart (`PRIME_RESET`, `_prime_reset_paper`, once): non-real tier cards archived to the record and re-dealt at $20
  (saved cfg `sizeUsd` 20; DEFAULT_CFG stays 100). Real cards never touched.
- 🧊 Runner cool-down (`runners.COOL_ROUNDS` 3, `recently_out`): a coin dropped or swapped out of a round is not picked again for 3 rounds.
- Runners board: only lanes with picks get a column; empty lanes collapse into one `rn-idle` chip row (no dead "nothing this lane" boxes).
- HQ › Fuse › Arena PrimeControls = PAPER tier cards only, two tabs (`PCTL_TABS`: 🃏 Cards · ⏱ Rounds & safety); size seg $20/$100/$500.
- ⚔ The Pit order: the battle box FIRST, the 👑 Throne under it with NO box (gold spotlight `th-cone`, pedestal `th-plinth` inside `th-king`,
  soft radial mask; info rows are left-rule lines, never bordered boxes).
- 🏆 Playground seats (`pg_battle.shown`, `SHOWN` 3): up to 8 big cards fight in the background field; only the top 3 (W−L, wins, live move)
  are shown (`PgTop3` at the top of Engine playground) and ONLY they can be 🎨 picked (`_pg_pick_ok` gates `scenario-pick`; no field yet =
  any). The field itself sits in a fold. Regular scenario cards = 6-coin Fuses (`REGULAR_COINS`, `_pg_scenario_cards(coins=6)`, weights → 100%).
- 💸 Keeper swap cost (`fuse_wallet.priority_cap(attempt, boost, sol_usd)`): a first try with no landing trouble keeps base + priority under
  a penny (`PENNY_USD`, 10K–50K lamports at today's SOL); a retry or a card whose txs didn't land pays more to land (≤ 300K). Keeper swaps
  carry NO FEELESS fee; new-coin rent (~0.002 SOL) comes back when `_fw_close_empty` closes empty accounts (every 30 min).
- 🧾 Verdict (`backend/verdict.py`, owner `GET /admin/fuses/verdict`, `Verdict` on HQ › Fuse overview under Needs you): every engine on its own
  record — tier runs, strategies, runner lanes, dials, playground clocks, sim configs, real runs → ✅ keep (avg AND median > 0 with enough samples)
  · ❌ scrap · 👀 unproven. Read-only: decide what to scrap from it, never auto-scrap.
- ❄ Freeze options: `RIDE_ATS` +10/15/20/25/50/100/150 and `RIDE_TRAILS` −5/8/10/15/20/30 (a frozen coin also leaves under half its freeze).
- ⚔ Every new bell opens with a `bf-intro` round slam (ROUND n · FIGHT!, 1.8s, off in fx-lite / reduced motion).
- 🛟 Rescue OFF (`rescuePct` 0) = NO fix of any kind: no rescue cycle, no losing-streak safe fix, and no −40% day fix (`FIX_DAY_PCT` only runs
  with rescue on). The owner's coin floor is the only protection.
- 💵 Real cards ALWAYS fight: `arena_league.new_season(must=)` seats every real-money card on top of the 8 (key `prime:<tier>`, never config-based)
  and `ensure` adds one funded mid-season at once on a $20 book. Clock / config changes never drop it.
- 🧼 Rep gate (`runners.rep_ok`): HIGH-risk creators, a REPORTED rug on the blocklist and bot-shield bots are always out. A SUSPECT creator (or one
  blocklisted only for sniping other launches) passes only when the coin proves itself (`banger_proof`: top-10 < 20%, insiders < 5%, 0 bundled,
  ≥ 55% buys, ≥ $20K 1h volume, dev not sold) and scores −12. New-runner launches (≤ 3h) keep the strict clean-creator rule.
- 🧾 Verdict ALWAYS runs (`_verdict_tick` hourly in `_fuse_warm`, `data/fuse_verdict.json` + history; owner inbox once when a row flips ✅/❌).
  One click per row (`POST /admin/fuses/verdict/act`, owner, audited): 🧠 sim setting → 🃏 ONE card (`tierCfg[tier]`) · 💵 real card
  (`realOwnerSet`) — there is NO "all cards" action (owner: every card keeps unique configs) · 🏟 strategy 🗑 scrap / 📌 keep (`scrappedStyles`/`keptStyles` → `_retired`)
  · 🎚 use a proven dial · ⭐ re-deal a losing paper tier. Nothing changes without the click.
- 🃏 Every paper tier card plays ITS OWN exits (`arena_prime.TIER_KEYS` rideAt/rideTrail/rotateMinDrop/rotateConfirm/minHoldMins/instantSwapPct/tp/sl,
  `tierCfg`, unique `DEFAULT_TIER_CFG`, `tier_cfg` merges; `card_template` = card TP/SL, 0 = tier's). HQ › Fuse › Arena › Cards: each paper card
  has its own ⚙ Edit Fuse (exits save to `tierCfg`). Locks snapshot the tier's own exits. A shared paper edit NEVER touches these keys (the
  Rounds & safety tab no longer shows them); `unique_exits` + one-time `_prime_unique_fix` (`PRIME_UNIQUE`) undid an "all cards" click.
  The real card reads only `realCfg` — paper edits, verdict clicks and fixes never change it.
- 🎯 3 strategies per round length (`pg_sim.strategies` in `byClock`: 🛡 Steady = best share ended up · 🧠 Engine pick = best median · 🔥 Hunt =
  best average; always 3 different configs; proof = each setting's own sims). Public `GET /fuses/strategies?hours=` (nearest clock, said so),
  `StrategyPicks` (+ `stratPatch`) in Edit Fuse › Exits (tier + real) and on every My cards card. The sim now tests ❄ freeze (`RIDES`) + peak
  trail (`TRAILS`) like the engine (out under half the freeze or trail% off its peak).
- ❄ User cards freeze too (`fuse_hq.ride_hits`, plan `rideAt`/`rideTrail`, `_fuse_leg_tick`): a coin past +X% is riding (its TP alert waits);
  ONE sell alert when it falls Y% off its peak or under half the freeze. Alerts only — never sells by itself. My cards: `fp-freeze` row.
- 🧹 Rent sweep every 2 rounds of the real card's clock (`fuse_wallet.close_every`, 10–30 min). Rent is paid by the reserve, so it returns to the
  reserve — the card never paid it, its numbers stay exact.
- 🧾 Real card P&L = PRICE RESULT: rent is always the wallet reserve's (refunded to the reserve on close); network fees the card pays from
  round 5 are tracked (`book.cardFeesSol`) and added back in `math.pnlUsd` (`cardFeesUsd`, shown "fees $X apart"); frontend `allTime` /
  `whereDown` read it. IN CARD NOW stays the true value. 😴 Overnight: `bash scripts/stay-awake.sh` (caffeinate + keep-alive, plugged in, lid open).
- 🧊 Cool-down counts ROUNDS (`arena_prime.cooling/note_dropped`, stamp `round`): a coin that left in round N is out for N+1..N+3, back at
  N+4 earliest (a time-only window let HIGGS back on the 3rd bell). Restarted runs / old stamps fall back to (3 + 1) rounds of time.
- 🗑 TRENCH cycle (`backend/trench.py` pure + tested, `_trench_build` ~2 min in `_fuse_warm`, `GET /fuses/trench`, `TrenchScan` in Edit Fuse ›
  Shape): fresh launches (≤6h) that broke $20K (≤$150K) with ≥400 on-chain holders, ≥250 trades/h, ≥$10K 1h vol, ≥55% buys, 5m+1h green,
  top-10 <25%, insiders <8%, ≤1 bundled, dev <5% not selling, no spike / flagged funders, creator not flagged or watch/suspect/high, mint +
  freeze revoked — unknown = out. Shape `trench` (1 major + 1 pool + 2 runner slots, the first `trenchCoins` 1|2 go to trench coins),
  cycle `trench`. Trench rows are `trenchOnly`: only a trench slot / trench leg replacement takes one (`best(role, trench)`, `_picks`,
  `grow_picks`). Real money: own pool floor `trenchMinLiqUsd` ($8K, never < $3K) via `liq_floor(.., trench)`, no trench buys in a runner
  storm, every other keeper check (price gap, sell-back, impact, caps) still runs. Holder counts only for the 5 busiest finalists.
- 💧 Thin-pool refusals fixed: real cards never fall back to thin pools (`p_t … or []` for real) and candidates clear the keeper floor by
  `REAL_LIQ_MARGIN` 15% (cached depth drifts before the live re-check). `fuse_wallet.note_miss`: a "pool too thin" refusal benches the
  coin at ONCE (`THIN_POOL`) → swapped now; `MISS_WINDOW` (30 min) ≥ 2× `QUIET_SEC` (a quietly re-logged skip never added up before,
  so a refused coin was never benched and its slot sat waiting). 🗑 Trench lens in `SwapPicker` (`GET /fuses/trench` → `rows` + `floor`):
  only passing trench coins, trench pool floor; a pick keeps `trenchOnly` through `queue_swap` → leg `trench` → keeper trench floor.
- 🧾 Money trail (`fuse_wallet.money_trail`, tested; `scripts/fuse-report.py [hours]`, read-only, run on the owner's Mac): per real card
  put in → now (coins + cash), realized per coin, still-held move, write-offs, card-paid fees, rent on reserve, skip / fail reasons,
  benched coins, run_report flaws, and an `unexplained` line that must read $0 (the books add up). Prints no keys / RPC / wallet id.
- ♻ RENT = the card's own refundable DEPOSIT (replaces both earlier rent rules): `orders` sets a new coin's rent aside
  (`rentDeposit`, only when the card can afford it, else the reserve fronts it → `rentSol`); `apply_fill` books it in `rentHeldSol` +
  `rentDeposits[mint]` (counted in `book_value` / card `rentUsd` → P&L never moves); a CONFIRMED close (`_fw_rent_credit` →
  `rent_back`) returns at most that deposit into card cash. NEVER credit historical refunds: the first version did (the reserve had
  re-used that SOL many times) → card read $32 in a $6.89 wallet and `reconcile_sol` halted it; `undo_rent_credits` (once, `rentFix1`)
  took it back out. A top-up can't assign more than `free_sol` (wallet − reserve − every card's book).
  ⏳ Stuck buys (`fuse_wallet.stuck_buys`, leg `buyingSince`, `STUCK_BUY_SEC` 600): a real-card coin still 'buying' after 10 min (or benched)
  is swapped for a buyable coin in the tier tick (no candidate → slot back to card cash) and cooled via `note_dropped`.
- 🗑 Trench, wired end to end: `_runner_live` adds up to 10 raw pairs passing `trench.market_pair` (fresh · $20K band · busy · buyers ·
  green) to the holder scan and keeps EVERY candidate in `_runner_cands` for `_trench_build` (it used to read only passing + the top 30
  dropped, and only the 40 busiest were ever scanned → the list stayed empty). 🗑 TRENCH FILL in `arena_prime.tick`: a card whose cycle
  (or phase) is trench takes its 1–2 trench coins on the next tick — the weakest normal runner (≤ +10%, not frozen / riding / picked /
  buying) is swapped — instead of waiting up to `cycleEvery` rounds for a re-shape.
- 🔧 Stuck buys, root cause: `sync_card` gives SOL to the SOL anchor FIRST, and the funding repair only ran for empty (not yet
  'buying') coins → a waiting coin's order was never sent ("buying… keeper retries" for hours, $2.31 idle in SOL). Now `waiting` coins
  trigger the repair too: the SOL anchor is trimmed to an equal share (coin donors are trimmed only for EMPTY slots); no-op when free
  SOL already covers every waiting buy. Manual: `POST /admin/arena/prime {fix: tpl}` (🔧 Fix buys on the real card, shown while a coin
  waits) = repair now + fresh retries (misses cleared; benched stay benched). Auto: the 10-min stuck swap above.
- ⏸ Halts: an AUTOMATIC halt (wallet SOL / token below card books) lifts by itself once the wallet shows it's fixed
  (`fuse_wallet.halt_cleared`, ledger `fix` row); the owner's own ⏸ Pause and fill mismatches never auto-lift. A halted card still
  runs its SELL pass (`halt_allows_sells`; not on a token-shortage halt) — queued ✂ / recovery sells used to sit "queued" forever.
  `rentFix2`: PUT IN rebuilt from the ledger (`funded_from_ledger`: top-ups since the book began − withdrawals).
- ♻ Recovery sells (dead / off-card coins, leg `recovered`) are NOT owner cash: their SOL goes back to work in the card (only ✂ cuts set
  `manualCashSol`). `cashFix1` released the held recovery cash once; 🔧 Fix buys also releases held cash. Trench fill takes a runner
  still waiting on its buy FIRST (free swap), then the weakest held runner.
- 📋 No empty lists: 🗑 trench auto-widen (`trench.WIDEN` / `best_level`, `_trench_cache.level`, finalists by the loosest band, 8 holder
  scans): when nothing passes, crowd / trades / volume / mcap band / age step looser (×1–3); top-10, insiders, bundled, dev, creator,
  mint + freeze, buyers, green NEVER move. Gauntlet adds 🌊 Volume runners (gated runners, $20K+ 1h, buyers ≥50%) + 🗑 Trench divisions;
  any runner / dip / paid list with nothing qualifying shows its 3 closest live coins as 👀 WATCH (`contenders.near`, never seated).
  Swap picker lens 🌊 Volume. A PICKED cycle always cycles (`arena_prime.reshape_every`: re-shape "off" + a cycle → every 6 rounds).
- ⚖ Equal weight (`arena_prime.balance_small`, end of every tick): a coin whose COST is < 50% of its equal share (went in tiny — "$0.05 in a coin") is topped up from card cash, then from coins > 125% of their share (not frozen / riding). Losers are never averaged down.
- 🔒 Round min hold OFF (0) is an owner option on the real card (`real_guard(cfg, owner_set)`: honoured only when the owner saved it).
- 🗑 Trench creator rule: 'watch' creators PASS with a 0-point creator part (most serial pump deployers are 'watch' — excluding them left the
  list empty); suspect / high / flagged stay out. `trench.funnel` → `/fuses/trench.funnel` + `seen` → TrenchScan "🔎 Why nothing passed".
  Real panel on My cards polls `/fuses/prime` every 10s (server Jupiter value, `fl-tick` flash) — no refresh needed.
- 🔒 Real swap = CHECK THE BUY, THEN SELL (`_fw_preflight` → `fuse_wallet.hold_sells`, `HOLD_SELL_SEC` 45): before a swap's sell is sent,
  every NEW coin gets a fresh live-pool read, the owner's limits, a real quote and the secure-buy checks. A coin that fails is booked
  as a refused buy and the OLD coin is kept while the engine re-picks; never held past 45s, never on a stop / rug / floor exit, a
  sell-all, a halt or the owner's ✂. ⏱ A refused / failed buy is re-picked `RETRY_SEC` 15s later (`_FW_KICK` wakes the bell loop;
  `stuck_buys(missed=, pending_mint=)` — a coin with a tx in flight is never swapped); no refusal on record = 2 min. Bench = 15 min,
  doubling ≤ 2h. 🎯 The owner's PICK keeps the floor the picker promised (`liq_floor(picked=)` = the Arena floor, leg `picked` → order):
  picks were accepted at $25K, then refused by the keeper at $80K AFTER the old coin was sold. 👁 `fuse_wallet.swap_flow` →
  `keeper.flow` → `SwapFlow` strip on the real card: done → sending → next, one transaction at a time; only the chain turns a step green.
- 📡 RPC = keeper LANES (`chain_rpc.KEEPER_LANES`: `SOLANA_RPC_URL`, `SOLANA_RPC_URL_2`, Alchemy): a burst 429 moves to the next lane
  at once; a 429 that is the PLAN's quota (`out_of_quota`: "daily request limit" / "capacity limit" / remaining 0) parks that lane until
  its reset (`_quota_until`) — the keeper used to wait ~7s per call on a spent plan. Scanners are OFF the dedicated endpoint by
  default (`RPC_SCAN_RPS` 0): a free plan is a daily budget (QuickNode 50K/day) and holder scans spent it by late morning.
  `keeper.rpc` (lane number + minutes left, never a URL). ankr (403 without a key) is out of the public pool.
- 🎛 Trench settings (`trench.OWN_OPTIONS/clean_own/own_gate`, `prime.trenchCfg`, `POST /admin/arena/prime {trenchCfg}`, TrenchScan in
  Edit Fuse › Shape): 🤖 Engine tunes (auto-widen) or 🎛 My settings — holders, trades/h, 1h volume, market-cap band, age, each from a
  fixed list. The safety checks are never options.
- 🧾 ROUTE RENT IS NOT A PRICE (`fuse_wallet.opened_sol`, fill `openedSol`): a multi-hop swap opens accounts for the coins it passes
  through; that SOL is parked rent (back when they close). A SELL's proceeds = SOL that reached the wallet + SOL the tx put into
  accounts it opened (capped 0.02); the reserve fronts it (`rentSol`). Why: baton booked −87% and ORCA −50% (neither moved), which
  pushed the owner's card through its −40% floor and sold a frozen +24% winner. `_fw_quote` asks for a ONE-HOP route first
  (`onlyDirectRoutes`; multi-hop only when one hop is missing, > 1% impact, or pays > 0.5% less). `routeFix1` (once, from the chain):
  suspicious old sells (`route_fix_rows`, ≥ 25% under cost) are re-read and the parked rent goes back into the card's cash
  (≤ the wallet's free SOL), the run baseline rises by the same $ (money back, not a gain). When a real sell books a loss the coin's
  chart doesn't show, read the tx's pre/post balances before touching the engine.
- 💸 Keeper swap cost v2 (`fuse_wallet.priority_cap`, `FIRST_USD` $0.002, `PENNY_USD` $0.009): base + priority ≤ a fifth of a cent on
  a first try, +$0.002 per retry / recent miss, NEVER a penny (the slippage-retry path used a flat 100K lamports ≈ $0.012). Landing
  comes from the one-hop route + re-broadcast to every node. When every keyed RPC plan is spent the keeper keeps `KEEPER_PUBLIC` to
  itself (scanners use the other public node) and paces its retries. `.env`: the owner's editor keeps re-activating old
  `SOLANA_RPC_URL` lines — after ANY `.env` edit run `grep -c '^SOLANA_RPC_URL=' backend/.env` (must be 1; first value wins).
- 🧊 Cool-down holds everywhere: `note_dropped` carries the stamps of the card BEFORE a re-deal / re-shape (a new card dict used to
  drop them all — Human came back two rounds after a −18% exit); the owner's pick (`cool_left` → "back in N rounds"), the hand swap
  and the stuck-buy swap all skip cooling coins; real cards cool anchors strictly while another major exists.
- 📡 Scanner share = a token bucket (`RPC_SCAN_RPS` default 0.3/s ≈ 26K calls a day, burst 6): 5/s spent a free plan by late morning,
  0 starved the holder scans (public nodes refuse most holder lookups) → "top-10 (scan done)" failed 47 of 48 coins and the trench /
  volume / fresh lists went empty. EMPTY RUNNER LISTS ⇒ check `/fuses/trench` funnel for "scan done" before touching any gate.
- 🔑 RPC keys from HQ (`RpcKey` at the top of HQ › Fuse › 👛, owner `GET|POST /admin/rpc`): lanes shown as provider domain + in / out of
  quota only (never a URL). One paste → `chain_rpc.clean_rpc_url` (https, public host) → `probe` (must answer; holder lookup noted) →
  `env_with_key` (ONE active line of that key in backend/.env, duplicates commented) → `set_lane` (live in the keeper's process, no
  restart). The URL is never returned, logged or audited. Every keyed lane spent → one owner inbox notice a day (`_rpc_quota_notice`,
  opens `?tab=fuse&rpc=1`) and the box glows ADD A KEY. Lane 1 today = Helius, lane 2 = QuickNode.
- ⚖ Stay or swap (`arena_prime.swap_cost_pct/swap_edge`, cfg `swapEdge` on by default): at the bell a patient loser is rotated only
  when the next coin is beating SOL over 1h AND beats the held coin by more than the swap costs (true fills both ways + 2 fees) + 1%
  (`SWAP_EDGE_MARGIN`); else event `keep` with the numbers. Blocks only on EVIDENCE (no 1h reading → rotates as before). Stops,
  instant swaps, rides, picks untouched. 🤖 Hourly cap (`swap_cap`, cfg `swapCapHr`: 0 auto · 2–12 · −1 none; `swaps_last_hour` counts
  only `PLAIN_ROTATE` events = round rotations + trench fills): auto = churn ≤ `CHURN_BUDGET_PCT` 2% of the card an hour from the cost
  of one swap at that card size; `summary.swapCap` {cap, auto, costPct, why, used} → Edit Fuse › Rounds shows the reason in words.
- ⚡ THE FUSE ARENA GAME (`pg_battle.duels/duel_winner/seat_prices`, `DuelBoard` in PitLive, `pl-duel` css): a league game = one bell
  = SIX DUELS, each coin vs the coin in the same seat on the other card (seat 1 = biggest coin; fewer coins = fewer seats; a coin
  subbed in mid-game starts at its entry). More move since the bell (`bellPx` saved on the pair, book `px` at each mark) = a spark;
  most sparks wins, level → the card's move (old rule), still level → draw. 🔌 Live Wire · 🧯 Blown Fuse · 💥 Overload (every seat).
  Results carry `sparks`; the table splits level points by sparks for − against (`sf`/`sa`). Points only — never a bet.
- 📡 Up to SIX keyed lanes (`SOLANA_RPC_URL`, `_2` … `_6`; HQ RPC keys box picks the slot). `rpc_priority` walks them in order and a
  lane dropped as spent never shifts the ones after it (an index bug once skipped a lane).
- 🔀 One-transaction swaps (Fuse wallet cfg `coinToCoin`, OFF by default; HQ › 👛 toggle `fw-c2c`): for a coin leaving for good ↔ a
  coin not held (`fuse_wallet.swap_pairs`), `_fw_execute_swap` takes three read-only quotes (old→SOL, SOL→new, old→new) and sends ONE
  tx only when the one-step route gives ≥ the coins two swaps would AND impact ≤ 4% (`c2c_ok`), after the same live-pool / limit /
  secure-buy / sell-near-market checks; anything else → None → the normal two swaps. Booked from the chain (`swap_fill_from_meta`,
  `swap_fill_error` halts on any mismatch, `apply_swap`: value moved = new coins × market price = old coin's sale price = new coin's
  cost; SOL beyond the fee = rent on the reserve) as a sell row + a buy row on ONE signature — every "one row per tx" de-dup is now
  per (sig, side). A failed one-step → two-step for 10 min (`C2C_COOL_SEC`). First live use = watch the ledger for an hour.
- Updates: `scripts/auto-pull.sh` only pulls OTHER sessions' pushes (a push from this Mac leaves nothing to pull) — after pushing from
  here, restart the backend yourself (wait for no `pending` order first). `keep-alive.sh` restarts dead services only.
- ♻ SAME SHAPE AGAIN = NO RE-SHAPE: a cycle whose next shape is the one the card already holds (trench → trench) is skipped for a
  full card (underfilled / one-tap re-deal / majors-only growth still deal). It used to re-deal every `cycleEvery` rounds and sell
  every coin under +5% for whatever ranked first — the owner's $5 card sold BREAK-EVEN coins every 30 min (≈ 11 real swaps an hour).
  HOW IT WAS FOUND: `fuse-report.py` hold times (9–30 min holds, ~$0 realized, all "not on the card any more") + a `phase` event.
  Idle-cash `compound` events fold into ONE line per 30 min (`n`, `firstAt`) — they had filled 54 of the 60 kept events, hiding why.
- 🧾 `money_trail` adds back `routefix` credits (`routeRentBackUsd`): the permanent audit table keeps the original sell rows.
- 🔒 Hands-off lock (`arena_prime.set_hands_off/hands_off_left`, `POST /admin/arena/prime {handsOff: {tpl, hours: 0|1|3|6|12}}`, select
  `hands-off` beside ✋ Hold all): the owner's picks and hand swaps are refused until it times out; the engine, stops, rug shield and
  ✂ sell-to-cash keep working. Real card art on My cards = `zoom: 1.34` on wide screens (1.15 under 1180px, 1 on phones).
- 🏦 RENT = THE RESERVE'S, ALWAYS (replaces the card-deposit rule): `orders` never sets a `rentDeposit`; `apply_fill` books any SOL a
  buy used beyond its swap as `rentSol` (reserve). A card's money = its coins + its cash, nothing else — a $5 card had ~$1 parked in
  deposits. `release_rent_deposits` (each balance read, only when books match the wallet) moves old `rentHeldSol` back into card
  cash as far as the wallet's free SOL covers it (ledger `fix` row `rentfree:`). Closes refund the wallet; no card is credited.
- `reconcile` skips a coin with an order in flight (`pending.mint` / `toMint`): a sale confirms on-chain before it is booked, which
  read as "coins missing" + a halt for ~30s. 🎭 `fuse_wallet.lookalike(symbol, mint, fuse.MAJORS)`: a coin wearing a major's ticker
  that is not that major is dropped from `_prime_candidates` and the picker (real money bought a fake "SOL": −28% in 78 seconds).
- 🔎 Chain audit (`scripts/fuse-audit.py [card]`, read-only, on the owner's Mac): re-reads EVERY confirmed swap of a real card's book
  from the chain, rebuilds its SOL cash (funded − into buys + out of sells incl. route rent − card-paid fees) and compares with the
  book; checks every booked coin is in the wallet; reports route rent still owed. 2026-10-05: 152 swaps, book vs chain +0.00009 SOL,
  nothing owed. RUN IT before telling the owner the books are right — never answer "are my funds all there" from the ledger alone.
- 🔒 Real card FACE = `allTime()` (price result, fees apart) — the same number as the ALL-TIME tile (it showed −$1.88 beside −$1.60).
  The ◎ cash row reads the book's confirmed SOL (`reconciliation.cardCashUsd`), the same number as "Withdraw card cash".
- 🚪 `arena_prime.entry_ok` (real cards, in the tier tick): a candidate falling right now (5m ≤ −3% or 1h ≤ −8%, own reading else
  the momentum feed) is not bought; no reading = not judged; coins already on the card are not filtered.
- 🎟 THE BUYER CHOOSES (`fuse_hq.card_choice/choice_credit`, `PLAN_ROUNDS` 5/10/20/50, `PLAN_SWAPS` 1/2/3 ⇄ `lib/cardChoice.js`, change
  both): Lab CardPlan row "🎟 Rounds & swaps" (plan `rounds`, `swapsPerRound`, `payUpfront`; kept through dial changes via `keepChoice`).
  Up front = ONE SOL transfer in the buy's approval = round packs beyond the free 5 (`per5Usd`) + perSwapUsd × swaps/round × rounds,
  re-priced and verified on-chain by the server (≥ 97%); underpaid or "🆓 free rounds first" = nothing credited, the card starts on
  its 5 free rounds and each swap pays its own fee. `maxSwapsPerRound` always applies: `next_switch_at` allows that many switch-ins
  inside one round (`switchTimes`). No pick in the plan = HQ's default prepay exactly as before.
- ⚡ Lag (Fuse pages): the sitewide ambient layer (28 flakes, 2 screen-blended orbs, orbits, scan line) animated UNSEEN behind the
  Fuse page's opaque sky — `body:has(.fuse-page)` hides it (running animations on My cards 91 → 58). No blur / backdrop-filter is on
  screen in either theme. APIs answer in 1–120 ms: when "lag" is reported, count `document.getAnimations()` before touching the API.
- 🔎 `scripts/fuse-audit.py wallet` = whole-wallet chain check (every tx the Fuse wallet appears in: deposits, buys, sells, closes,
  fees, anything sent to another address) — slow (minutes) on a free RPC.
- 🌊 WIDE PULL (`launchpad_board.pump_pages`, `BOARD_MAX` 480): the launch feed reads Pump's 250 biggest coins (market_cap offsets
  0–200) + its 200 most recently traded (it was 50 + 100 → ~75 coins in the whole feed, the runner board saw 51, so Fuse kept buying
  the same few). Deep pages are cached 45–180s (Pump 429s bursts). `_runner_live` reads 4 feed pages per kind and scans the
  `RUNNER_SCANS` 60 busiest; `fuse.pump_majors` top 40. "SAME COINS AGAIN" ⇒ check `/runners` `seen` and the feed's pair counts
  BEFORE touching a gate. `/fuses/search` returns `why` when nothing can be picked (curve-only coin / parked pools).
- 🧱 FLOOR MONEY (found 2026-10-05, card $3.00 → $1.90 in an hour): (1) `safe_anchor` = established major only — a coin the OWNER
  picked into the anchor seat keeps its stop / instant swap / rug shield ($HODL sat there unprotected: −54% in 10 min); (2) the floor
  consolidates only into safe anchors, else CASH; (3) a real card with rest OFF goes straight to cash (it re-deals next tick —
  buying the anchor then selling it a minute later cost 4–5% impact twice on the whole card: $KURA, −$0.14).
- 🔎 Whole-wallet audit 2026-10-05: 655 txs, 0 unread, 0 SOL ever sent to another address, books vs chain +0.0005 SOL. The earlier
  $0.87 "gap" was only the 27 transactions a rate-limited first pass could not read.
- ⚖ NO COIN GETS THE WHOLE POT (`arena_prime.spread_cash`): idle cash fills each coin toward an EQUAL share of (coins + cash), in
  proportion to how far under it sits; a coin at / over its share gets nothing. It used to go entirely to a coin waiting on its buy
  ($1.15 → one coin = half the card, and that coin then decided the card).
- 🔒 Stack & lock, in one line (`arena_prime.stack` → `summary.stack` → `hrt-stack` on the real card): 🔒 locked = frozen / riding
  winners (sold only off their peak) · ✅ winning = ≥ `keepWinPct` (a re-shape won't sell it) · ⏳ proving · FULL STACK = every coin
  locked. Simple on screen; the engine rules behind it (freeze, trail, half-freeze exit, stops) are unchanged.
- 🏦 BANK AT THE LOCK (`lockBankPct` 0/25/33/50, default 33, Edit Fuse › Exits): the tick a coin locks (❄ ride starts) that % is sold
  (event `lock-bank`), the money goes to card cash → `spread_cash` over the OTHER coins (a riding / frozen coin is never topped up).
  The leg gets `trimAt`; `fuse_wallet.orders` sells an engine trim even inside `REBAL_BAND` for 10 min (33% is under the 50% band —
  without the flag the real card would never have sold it). Old tests pin `lockBankPct: 0`.
- ⚖ A PICK GETS AT MOST AN EQUAL SHARE (`apply_queued`): the spare from an oversized seat goes to card cash and is spread.
- 👀 NO EMPTY LIST: `contenders.WATCH_DIVS` + `trench`; `sources['<div>_watch']` feeds the fallback (`trench_watch` = the scan's closest
  misses, else the busiest fresh launches ≤ 24h). Watch rows are never seated, never pickable. Rows carry `chg5m`.
- Swap picker rows show 5m AND 1h (live `lp.m5` / `lp.h1`, else the row's) + `⚠ falling` via `isFalling` (= `arena_prime.entry_ok`:
  5m ≤ −3% or 1h ≤ −8%). The owner can still pick it — the flag informs, it does not block.
- Swap picker rows = a FIXED 8-column grid (coin · price · 5m · 1h · ⚠ · pool · score · button): every cell is always rendered (the
  ⚠ cell is empty when not falling) — a conditional cell wrapped the row and blew the button up to full width. Adding a column ⇒ add
  it to `.sp li` grid-template-columns AND open the picker in the browser. Dollar coins are filtered out of every list (`PICK_STABLES`).
- 🙅 OWNER-REMOVED COINS STAY OUT 6h (`arena_prime.owner_out`, card `ownerOut`, `OWNER_OUT_SEC`): a coin taken off by a pick or a hand
  swap is in `cooling()` for 6 hours (the 3-round cool-down let $PENGU back three times in one afternoon). `cool_left` ≥ 1 for it too.
- 🏦 ENGINE CUTS ARE DURABLE (found when $SpaceXSI locked at +101%, its 33% bank never sold, and it ran to +430%): `sync_card` keeps a
  leg's CUT units while `trimAt` is fresh (`TRIM_SEC` 10 min) instead of copying the wallet balance back; the swap-out hold
  (`hold_sells`) only ever holds 'not on the card any more' sells — a cut of a coin that stays is never held; `lock_bank` is once per
  ride (`bankedAt`) and a coin ALREADY riding that never banked banks once on the next tick (setting switched on later / bank lost).
- 💰 SKIM = profit only, stake rides (`arena_prime._skim/skim_leg`, `POST /admin/arena/prime {skim: {tpl, pairAddress, to}}`, per-coin
  `skim-<SYM>` select on the real card; auto: cfg `skimAt` 0/10/20/30/50/100 since entry / last skim (`skimPx`), `skimTo` card | cash,
  Edit Fuse › Exits). → card = cash → `spread_cash` over the OTHER coins (a coin cut in the last 10 min is not refilled);
  → cash = `holdCashUsd` (never re-spent; the owner withdraws it, e.g. tax money). A ✂ part-sell sets `trimAt` too (a 25% cut sat
  inside the keeper's 50% band and never sold).
- 🧠 Smart gates (`runners.flow_ok/clean_holders/aged_proof`, cfg `smartBuyShare` 92, `agedProofH` 12; HQ › Fuse › ⚡ Engine now shows
  the flow inputs too): buys above the band pass up to `smartBuyShare` ONLY with clean holders; a SUSPECT creator's coin also passes
  once it has lasted `agedProofH` h with a ≥ $50K pool, spread holders, no flagged funders, dev not sold. HIGH-risk creators never.
- Real card coin names (`hrt-name`) glow on hover / focus and open the war room (`openWarRoom`), like tier-card coins.
- ⚖ `balance_small` never tops up a coin that is small ON PURPOSE: skimmed (`skimPx`), banked (`bankedAt`), freshly cut (`trimAt`
  < 10 min), riding or frozen. It bought $1.13 back into $SpaceXSI four seconds after a $1.93 skim. Time checks on optional stamps
  must test the stamp exists first (`now - 0 < 600` is true in tests that run at now = 0).
- 🏔 OFF ITS PEAK (owner's stated FUSE GOAL: "cycle until big coins are found; −30% from the peak → sell 50% of the profit"): cfg
  `peakSellPct` 25/50/75/100, default 50 (Edit Fuse › Exits). A riding coin that falls `rideTrail`% from its peak while still above
  its floor sells that % of its PROFIT (`_skim(frac=)`, event `peak-sell`), keeps riding, and the trail re-arms from that price;
  100 = the old "swap the whole coin". Under the floor (half the freeze) the ride is over and it is swapped, as before. Old tests
  pin `peakSellPct: 100`.
- 🪑 EMPTY SEAT REFILL (tick, before idle cash is spread): owner's `coins` N, fewer legs, free cash ≥ `SEAT_MIN_USD` $0.25 → the best
  runner (else pool) not on the card takes the seat with an equal share (event `seat`), one a tick, never floored / held. A seat lost
  to a refused buy used to stay empty for good (the card sat on 3 coins).
- War room chart header has a copy-CA chip (`chart-copy-ca`, styles in tips.css — command.css is at its KB budget).
- `_parsed_info(acc)` is THE way to read a jsonParsed account: some providers (seen after the owner swapped lane 1 to another RPC)
  return an account they can't parse as `[base64, 'base64']`; `.get` on that list crashed `token_intel` (HTTP 500) → coins stayed
  "unscanned" and the lists thinned. Never chain `.get('data') or {}).get('parsed')` by hand. The HQ RPC box REPLACES whatever is in
  the chosen slot — putting a new key in slot 1 removed Helius; `HELIUS_RPC_URL` now carries the Helius key for Helius-only data and
  Helius is lane 3.
- 🎯 OWNER PICKS are blocked ONLY by "no back-to-back" (`arena_prime.pick_cool`: left in the last `COOL_ROUNDS` rounds → {mint: rounds
  left}; view `pickCool` → picker button "in N rnd"). The long rules (left at a loss → out until it recovers ≤ 24h; removed by the
  owner → 6h) stop the ENGINE re-dealing a coin and never refuse the owner ("every coin to swap in is bugged": most listed coins had
  been on the card and left at a small loss). Picking a coin back clears its `ownerOut`.
- 🪑 Seat refill with NO cash: coins above the new equal share (never locked / riding / buying) are trimmed to it (`trimAt`) to fund
  the seat — a rugged coin leaves nothing, and the card sat on 3 coins.
- Under the real card: `CardVitals` (`hrt-under`: seat pips by state, swaps this hour, profit pulled, best coin) + 📜 Full activity
  (`CardEarnings` pop-up with every event, labels `KIND` + `VITAL_KIND`) + 🎞 Share (`ShareGifButton`).
- Music queue titles: `.feecat-queue li > .feecat-x { width: auto; flex: none }` (tips.css) — the ✕ also had `width: 100%`, squeezing the
  title button (flex-basis 0) to 14px so rows read "1 ✕". The player stores only `{url, title}` per song in localStorage.
- Per-coin 💰 select is a fixed 86px (`.hrt-skim`); a bare `width: auto` select stretched across the row.
- 🌊 Volume list = every launch coin passing the SAFETY gates (`runners.safe_only`: all gates except `SOFT_GATES` prebond / age / size /
  volume / flow), busiest first — soft gates keep a coin out of the ROUND, not out of sight. 🗑 Trench picker rows = passing coins +
  near-misses (`trench.soft_only`: only soft checks missed; flagged `soft`, never auto-seated, the owner may pick at the pick floor).
- 🔥 `TopThree` beside the sync chip on the real card (`top-three`, `t3-*`): the 3 busiest safe coins not on the card (`topThree`: runner
  divisions, no watch rows, none in `pickCool`), one shown at a time (5s), ONE contenders fetch every 30s; tap → menu of the card's
  coins → `pickSwap`. Locked / riding coins can't be swapped out there. The SOL seat has its own 🎯 ("swap SOL into a coin").
- 🌙 `scripts/background.sh start|status|stop`: keep-alive under `caffeinate`, detached from the Terminal (nohup + pid file). It is
  still the owner's Mac (lid closed / reboot stops it); a real host = docs/ALWAYS_ON.md. THE BIG SPLIT of reputation_service.py
  (16.5K lines) is NOT started — plan: auth → prices → Fuse wallet keeper → Arena → runners, one module per commit, tests green.
- 🎯 OWNER'S PICK FLOOR = THEIR OWN SETTING (`fuse_wallet` cfg `pickMinLiqUsd`, default $10K, never < $5K; Edit Fuse › Limits "My own
  pick min pool"): `liq_floor(picked=True)` = min(general, Arena, pick floor); `_pick_row(pair, mint, floor)` uses it (it was a fixed
  $25K — a $23.8K pool the owner wanted read "too thin"). The ENGINE's floors do not move; impact / price-gap / sell-back still run.
- 🤝 Smart top-10 (`runners.holding/top10_ok`, cfg `smartTop10` 40, HQ › ⚡ Engine): top-10 above `maxTop10` passes up to it ONLY while
  the big holders hold — scan done, top-10 not growing, insiders < 5%, no flagged funders, dev not sold, buyers ≥ 50%, ≥ 1h old, a
  site or X, creator clean / watch. A HIGH-risk creator (rug report, serial sniper) NEVER passes an engine gate — the owner may still
  pick the coin by hand: picker rows carry `warn` (`_creator_warn` from `_runner_cands`, "⚠ creator" in the ⚠ cell, never a block).
- ⚡ Pump Pulse in the lists: 🌊 Volume rows get `pulse` from ONE batched `_edge_pulses` call (pulsing first, +8 score); picker shows ⚡.
- 🧷 AN OWNER WRITE BEATS A TICK (`arena_prime.card_snap/merge_tick`, `_hq_ver`): the tier tick loads the cards, awaits prices for
  seconds, then used to save its copy over the file — a pick / skim / lock / config written in that window vanished ("top 3 pick not
  setting": the request answered 200). Now a card that changed on disk since the tick loaded it is kept and that tick's result for
  it is dropped. ANY new loop that loads → awaits → saves a shared store must do the same.
- ⚖ `spread_cash(legs, cash, prices, seats)`: the equal share is counted over every UNLOCKED coin, and cash that would lift a coin
  above it stays cash. One eligible coin (the others just cut) took all of it: a $0.74 pick became 60% of a four-coin card.
- 🧪 Trench METAS (`trench.METAS/meta_gate/loosest/meta_board`, trenchCfg `{mode: 'meta', meta}`): 🌱 Sprout · 🚀 Breakout · 🌊 Flood ·
  🏟 Crowd · 🕰 Survivor — soft checks only, from `OWN_OPTIONS`; safety checks identical in every meta. Finalists for the holder count
  are chosen by `loosest()` so every meta can be judged (`_trench_cache.got`). `GET /fuses/trench?meta=` = view-only. TrenchScan
  chips: HQ tap saves, a visitor's tap views (Fuse › Build › Runners › "🗑 Trench metas" fold).
- 🌦 Forecast (`arena_prime.forecast`, public `GET /fuses/forecast`, `WeatherStrip` on top of My cards): weather now · 6h-vs-24h sim
  trend · share of live launch coins green 1h · what real money buys in this weather. A reading, never a promise.
- ♻ PROFIT RECYCLE (cfg `recyclePct` 0/50/70/100, `recycleEvery` 1/2/3/6/12 rounds, Edit Fuse › Exits; off by default): at that
  round each coin's PROFIT × % is skimmed (`_skim(frac=)`, stake + the rest stay) and spread over the other coins. Losers never sold.
- 🔔 IDLE CARD CASH GOES BACK IN AT EVERY ROUND: the 10-min "just cut" skip is ignored at the bell (`round_now`; never for a coin cut
  on that same tick). Mid-round, cash that would lift a coin over an equal share waits.
- 🎯 Owner's pick sell-back limit = their setting (`fuse_wallet` cfg `pickSellBackPct` 6–10, default 6; `buy_safety` reads
  `maxRoundtripPct` only for `picked` orders). Stuck-buy events carry the keeper's own reason; `PickLog` under the real card shows
  the last 3 picks: came in / not bought + why.
- 📈 Trench meta paper proof (`trench.meta_track/meta_proof`, `data/trench_meta.json`): each coin a meta passes is noted once, settled
  1h later at Jupiter's price (no price = −100%), median + % up, `proven` ≥ 5 settled. Chips show it. `_trench_judge()` re-judges the
  scanned finalists at once on a settings save. Trench settings also sit inside the swap picker's 🗑 lens (`TrenchScan bare`).
- 🎞 Share on a real card = the CARD (`shareGif` `card.fuse` → `drawFuseCard`: tier colours, coin logos, per-coin %), not the mascot.
- 🪑 A RESERVED SEAT NEVER HOLDS MONEY PAST A ROUND: the heal tries the seat's own kind, then any buyable runner / pool; still no
  coin after one round → the placeholder is removed (event `slot`) and its reserve is spread into the card's coins; the empty-seat
  refill brings a coin back when one qualifies. Found live: $0.66 of a $2.40 card sat reserved for 17 minutes.
- 💾 HOLDER SCANS SURVIVE A RESTART (`_intel_save` every ~75s in `_fuse_warm`, `_intel_restore` on the first warm pass,
  `data/intel_cache.json`: complete scans < 30 min old, newest 300). Every backend restart used to blank the scan cache → runner /
  trench / volume lists empty for minutes ("57× top-10 (scan done)" in the trench funnel was mostly coins not scanned YET).
  Trench funnel now says "holder scan not done yet" apart from a real top-10 fail; trench top-10 above 25% passes to 35%
  (`HOLD_TOP10`) only while `runners.holding(c)`. THE OWNER'S RUNNER GATE in HQ › Engine is theirs (2026-10-05: top-10 < 20%,
  cap ≥ $20K, 52–80% buys) — when lists are thin, read `/runners` dropped gates and SAY which setting is doing it; never change it.
- 💤 IDLE CARD CASH, THE REAL CAUSE (`fuse_wallet.idle_sweep`, last step of `orders`): the keeper never sends a top-up inside the 50%
  re-weigh band or under the min order, and the next `sync_card` copies the wallet back — so the engine logged "idle cash back into
  the card" every tick (a folded `compound` event summing to MORE than the card = this loop) while the SOL sat in the book. When a
  tick has no other order, ONE buy puts spare SOL (beyond ✂ cash, held cash, a reserved seat) into the held coin furthest under an
  equal share; never a locked / just-cut / just-refused coin. "ENGINE SAYS X, WALLET DIDN'T" ⇒ compare card events with the ledger.
- 🧾 Real card › Activity = `CardMoves` ("WHAT THE CARD DID": recycles, skims, cash put back, picks, locks, stops — the engine's own
  words, 12 newest) above "SWAPS ON-CHAIN" (10 rows, each with the keeper's `why`). Card column: card centred, `.hrt-under` and the
  pick log ≤ 330px wide. `recycleEvery` takes 1/2/3/4/6/12. Home ($FEE on Trade) opens its chart on 4h.
- 🗑 Trench never reads empty for the owner: own settings / a meta with nothing passing → the ENGINE scan's passing coins are added
  to the picker as `soft` rows ("outside your trench settings"), pickable, never auto-seated (`_trench_cache.fallback`).
- 🔒 ONE KEEPER PROCESS (`backend/single.py` flock on `data/keeper.lock`, `_is_keeper()` gates `_prime_tick` AND `_fw_tick`; released +
  `stopping` on shutdown). 2026-10-05: `start-backend.sh` killed by PORT only — an old reputation_service gave up its port, stayed
  alive and kept its loops → two keepers for ~55 min: every order sent twice ($WAIF + $HIGGS bought twice, books saw one), ~0.0124
  SOL of the owner's UNASSIGNED wallet SOL ended up in the card. The script now stops every copy BY NAME and waits. AFTER ANY
  RESTART: `pgrep -f "uvicorn reputation_service" | wc -l` must be 1. Two ledger rows with the same order milliseconds apart = this.
- 📏 `fuse_wallet.fit_small_shortage`: wallet holds ≤ 2% less of a coin than ONE card's book → the book is lowered to the wallet
  (ledger `fix`), no halt; bigger / zero / two-card shortages still halt. A book above the wallet makes every sell fail simulation.
- 🎯 OWNER PICKS ARE NEVER COOLED (no back-to-back rule either; `pickCool` view is {}): cool-downs limit the engine only.
- 🧬 LAUNCH FACTS ARE READ ONCE (`_launch_facts`, `data/launch_facts.json`, newest 4000): `token_intel` used to re-read a coin's
  creator / bundlers / snipers every 3 minutes — up to ~60 RPC calls per coin per scan (1000 signatures + 25 transactions + 30
  balances), ~80K calls an hour for the runner board. That is what rate-limited EVERY key and left coins "unscanned" however many
  keys were added. Now a re-scan = holders only (4 calls); flagged-wallet balances at most every 15 min (`_flag_hold`).
  `_trench_build` asks for the scan of the 12 busiest coins that pass every other cheap check. COINS UNSCANNED ⇒ count calls per
  scan before asking the owner for another key.
- 🛑 `fuse_wallet.refused_now`: a buy refused by a SAFETY check (sell-back, price gap, impact, thin pool, no route back) is not sent
  again for 2 minutes; transient misses (busy route, slippage, 429) retry as before.
- ☠ `pg_sim.retire` (`pg_sim.json.retired`): a sim setting whose typical card lost in BOTH the 6h and 24h windows sits out of the
  brain's picks (`best`, `by_clock`, `strategies`) for a day, then is judged again; a trait never loses its last value.
- ⚡ Home: `BestFuseTile` (best card from `/fuses/prime`, real / paper label, one tap → Arena) above the pulse grid; the home $FEE
  chart (`FeeHeartbeat`) opens on 4h.
- 📡 2026-10-05 lane check (provider names only): lane 1 Alchemy (new key) answers; Tatum and Helius returned 429 on every call; the
  older Alchemy key is out for the month; public nodes refuse `getTokenLargestAccounts`. So ONE key was doing all holder scans at
  the scanners' 0.3/s share. Now `RPC_SCAN_RPS` default 0.5 and `INTEL_TTL` 300s (re-scan = 4 calls). To test lanes without printing
  a URL: post the 3 scan methods to each `chain_rpc.RPC_POOL` entry and print `provider_of(e)` + status only.
- 👀 Trench picker never empty (`trench.closest`): nothing passing, no near-miss, no fallback → the 5 busiest fresh coins that pass
  every SAFETY check on the cheap pass and miss only soft ones, as `soft` rows with what they miss. Owner-pickable, never auto-seated.
- 📈 STOCKS AS MAJORS (`fuse.STOCKS` = 11 xStock mints from Jupiter's VERIFIED list, `ALL_MAJORS`, `STOCK_MIN_LIQ` $250K;
  `majors_pools(by, STOCKS)` → rows `stock: True`; `_majors_rows` = crypto batch + stock batch; `/fuses/discover?lens=stocks`; picker
  lens 📈 Stocks). They rank with the anchors and can take an anchor seat. Lookalike checks read `ALL_MAJORS`. Add a ticker ONLY
  with its verified mint (never from memory) and a read-only SOL → stock → SOL quote (2026-10-05: ~0% round trip on $1).
- 🔁 `LEAGUE_RESET` one-time Arena league restart: the flag is saved in `d2` at the battle tick's own save. The first version set it
  on `d` (never saved) → the season would have restarted at EVERY bell. A one-time flag must be written where the tick SAVES.
- 🙈 NO CARD-WIDE CALL ON A BLIND TICK (`arena_prime.tick(blind=)`, set by `_prime_tick` when a real card's true book can't be read:
  an order in flight or no SOL price): floor, day fix and rescue are skipped that tick; per-coin stops still run. 2026-10-05: two
  picks mid-swap (old coins sold, new ones not landed) made the engine's estimate read −40% on a card that had lost nothing → the
  floor sold all four coins and re-dealt on a $1.07 baseline. A REAL card's floor is judged on `book_value` or not at all.
- 🧬 STRATEGY GENERATION + SCRAPPING (`fuse.breed_style` / `BRED` / `style_weights`, `fuse_hq.bred_cycle`, `_bred_tick` hourly with the
  autopilot; `fuse_hq.json` `bredStyles` / `bredScrapped` / `bredN`): ≤ 3 engine-made strategies (`gen-N`) run $5 paper like any
  style. A child = the best judged style's weights pushed further away from the worst one's (momentum may go negative = fade what
  ran), seeded, never a copy; one new per 6h. ≥ 6 settled runs with average AND median < 0 → scrapped to the log; both > 0 → owner
  inbox once. Arena board marks them 🧬 with parent. They never reach a trader rail by themselves.
- 🔁 NO BUY-THEN-TRIM LOOP (`fuse_wallet.idle_sweep`, `SWEEP_WAIT_SEC` 300, book `soldAt` set by `apply_fill`): idle cash waits 5 min
  after ANY failed / refused buy (the engine is re-picking that seat) and a coin SOLD in the last 10 min is never topped up. Found
  live: a failed buy's cash was swept into two coins, both were trimmed again 2 min later to seat the replacement (4 swaps for 0).
  A floored real card is not re-dealt on a blind tick either (its new run must start from the true book value).
- 🎯 ENTRIES NOW (`arena_prime.entry_setup/entries`, in `GET /fuses/forecast.entries`, chips in `WeatherStrip`): 🧹 sweep & reclaim
  (1h ≤ −8, 5m ≥ +2, buyers ≥ 58) · 🚀 breakout (1h ≥ +10, 5m ≥ +3, buyers ≥ 58, 5m volume pace ≥ 1.5×) · 🧲 pullback (1h ≥ +15,
  5m −6…−1, buyers ≥ 52). Only coins clearing every SAFETY gate with a ≥ $10K pool; tap opens the chart. A read, never a promise.
- 🧪 Entry-setup paper record (`trench.meta_track/meta_proof(keys=)` reused, `data/entry_proof.json`, tracked in `_trench_build`):
  each safe coin showing a setup is noted once and settled 1h later (no price = −100%); `/fuses/forecast` → `entries[].proof` +
  `setups` (n, median, % up). Chips show the median only from 5 settled. `ENTRY_RAN` 150: more than +150% on the hour is not an
  entry (a launch pump read as a "breakout"). 🗣 `TRENCH_WORDS` in `lib/fuseGlossary.js` → FuseGuide tab "Trench talk".
- 🧷 AUTO PROFIT KEEPS THE STAKE (`arena_prime.tp_room`, cfg `tpStakeUsd` 0/0.1/0.25/0.5/1, default 0.25, Edit Fuse › Exits; leg
  `tpCostUsd`): every automatic take (skim, bank at the lock, peak sell, recycle) also sells a slice of the coin's COST; once those
  takes removed that much stake they stop for that coin (it rides on with stops / trail / rug shield). The owner's 💰 / ✂ are never
  limited. Found live: $phubber, $0.56 in, +63%, whittled to $0.09 riding. Old tests pin `tpStakeUsd: 0`.
- 🎛 THE TRENCH FILTER FILTERS (`trench.band_miss`): the owner's own band is scanned FIRST (`_runner_live` raw pairs by `own_gate`,
  `_trench_build` holder-count seats) — with "≤ 1h · $10K–$100K" none of the scanned coins were ever in that band, so it read 0
  whatever was set. Picker rows: pass → near-miss (inside the age + cap band, only crowd / candles missed) → `outside` rows labelled
  "not in filter" with the exact number ("6.3h old — filter ≤ 1h"). `/fuses/trench` adds `inBand` + `nearMiss`.
- 🆕 PUMP CURVE COINS ARE PICKABLE BY THE OWNER (`fuse.curve_liq/with_curve`, mirrored in `fuse_wallet.live_buy_market` for `picked`
  orders only): a Pump coin still on its launch curve has no pool figure, so search / the picker hid it ("can't buy <CA>"). Its
  depth = 2 × √(32.19 × market cap in SOL) (virtual reserves; $37K cap ≈ $24K), judged against the owner's pick floor; the
  keeper's real quote checks (price gap, sell-back, impact) still decide. The ENGINE never buys a curve coin. Picker lens
  🆕 Pump live (`/fuses/discover?lens=pump`: newest + busiest launch coins, curve included, 60 rows, tagged `curve`).
- ↗ MONEY THAT IS NOT THE CARD'S LEAVES IT (`fuse_wallet.settle_owed`, book `owedOutSol`): off the card's value at once
  (`book_value`), never spent (`orders`, `sync_card`), moved out of the book as cash appears (ledger `fix` `owedout:`), PUT IN
  unchanged. `strayFix1` (once, owner's call): the 0.012552 SOL the duplicate keeper put into degen is owed out, every coin cut by
  the same share, run baseline lowered by the same $. A book-vs-chain surplus is NEVER booked as put-in without the owner.
- 🧠 PICK EDGE (`backend/pick_edge.py`, pure + tested; built every sim tick → `data/edge.json`, `_edge_load`): replaying 200 runner
  rounds (50h) against their recorded prices showed the board's typical pick −26% three hours later and the hand-written score
  UPSIDE DOWN (score ≥ 80 → −82%; fresh / thin / hyper-traded coins lost, older coins in deep pools with ≥ 70% buyers held). The
  table = typical 3h result per feature bucket (age, pool, cap, 1h / 5m move, buyers, turnover, stage), learned ONLY from picks
  whose outcome is known, a vanished coin = −18% (never dropped). `rank` orders tier-card runners (after `clock_rank`); `gate` =
  real money buys only runners with estimate ≥ 0 (cfg `edgeGate`, on; Edit Fuse › Rounds; `newMajor` + `trenchOnly` rows keep their
  own rules; owner picks never limited). `proof`: learn on 60%, rank the rest — the table is USED only while its best third beats
  its worst by ≥ 10 pts (2026-10-05: +1% vs −75%). `/fuses/forecast.edge` → WeatherStrip line. A ranking, never a promise:
  even the best group was only about flat.
- 🎯 THE SIM IS HONEST NOW (`pg_sim`): it used to replay only coins whose path covered the whole window (the survivors) at 0.6% a
  swap and read "+67% a day" while the real card lost. Now: every coin with a reading is kept (`None` = off the feed → sold
  `GONE_HAIRCUT` 18% under its last reading), `SWAP_COST` 1.5% (measured on 360 real fills), cards buy ONLY what the runner board
  offered at that step (`offers(rounds)`), genes `age` / `pool` / `edge` test selection, a card that never bought is not counted.
  2026-10-05: typical card −20% / 24h; edge on −10% vs off −31%. `byClock.profitable` finally means something. The weather reads
  these sims, so it is harsher (truer) than before. WHEN A SIM SAYS + AND REAL MONEY SAYS −, AUDIT THE SIM FOR LOOK-AHEAD FIRST.
- 📏 SMALLEST ORDER FITS THE CARD (`fuse_wallet.min_order`, card `seats`): the owner's `minOrderUsd`, but ≤ 40% of one seat's share
  (≥ $0.10). A $0.99 card with 4 seats could not buy its 4th coin at a flat $0.25 minimum → "buying…" → swapped for another coin
  every 2 min, for good. The tier tick gets it as cfg `minOrderUsd`: a seat is opened / a coin trimmed only by an amount the
  keeper would really send, else ONE `seat-wait` event per 30 min; a stuck seat under the minimum goes back to cash, not to
  another coin.
- 🧾 2026-10-05 autopsy of the owner's real card (360 fills): engine-chosen coins −$0.13 on $62 (≈ flat), owner's hand picks
  −$3.18 on $29 (6% won), trench −$0.71 on $7, fees $0.62; exits inside 15 min −$3.05 (8% won), trims of winners +$3.21 (80% won).
- 🏁 Swap picker opens on **Arena** (`contenders.everyone` → `/fuses/contenders.all`, lens `arena`, ≤ 160 rows): EVERY coin the
  Gauntlet ranks in one list (each division's best 25, one row per coin in the division where it scores highest, `divisionLabel`
  under the ticker; watch rows flagged and owner-pickable). The board itself still shows 6 per division. `pickSwap` accepts any
  mint in `all`. Row grid unchanged (the division sits inside the coin cell).
- 💸 Keeper swap cost v3 (`FIRST_USD` $0.001, `PENNY_USD` $0.005): first try ≈ a tenth of a cent at today's SOL, +$0.001 a retry,
  never over half a cent. (v2 measured: median $0.0016, p95 $0.004, none over $0.005.) THE FEE PROBLEM WAS NEVER THE SIZE — it was
  the COUNT: 177 swaps in 6h on a ~$1–2 card = $0.29. Slower clocks cut it; so does every "no pointless swap" rule above.
- ⚡ FAST GUARD (`arena_prime.guard_hits`, `GUARD_SEC` 10, `_real_guard_loop`): every ~10s ONE fresh batched Jupiter price read for
  the coins a REAL card holds; a coin at its stop / instant-swap line, or a rider off its trail, wakes `_prime_tick` at once (one
  wake per coin per 30s). It only wakes the tick — every rule and keeper check still decides. Why: a −15% stop sold at −48%
  ($SpaceX AI fell from +20% between two checks a minute apart). Applies on every clock.
- 🎯 SNIPER = ONE FIXED SETUP, PROVEN WALK-FORWARD (`pg_sim.SNIPER/prep/joint/proven`; `_pg_sim_tick` → `pg_sim.json.proven[clock]` +
  `provenLog`; first card in `GET /fuses/strategies`, `StrategyPicks` key `sniper`). Trait scores judge each setting ALONE, so a
  setup that only works as a whole never showed. `proven` replays SNIPER on a 3h window every 1.5h back through the record, each
  with only what was known when it opened; `profitable` = ≥ 10 windows, typical window up, ≥ 60% of windows up. IT IS NOT TUNED:
  a per-window hill-climb did WORSE on the next 3h than the fixed setup (5m: −2.7% vs −0.5%) — tuning on 2 days fits noise.
  WHAT MATTERS IS WHAT IS BOUGHT, not the exits or the clock (stop / freeze / trail / seat rest / time exit / round length all read
  the same): record-backed (estimate ≥ +3%) · ≥ 12h old · pool ≥ $50K · buyers ≥ 65% (the biggest single mover). 2026-10-05, per
  3h window: 5m and 15m +1.05% typical, 10 of 14 up, worst −2.0%; 30m +1.2%, 8 of 12; 60m too few windows. No selection: −14% to
  −41%. ~1 buy a card per 3h: it mostly WAITS. 12 variants were tried on the same 50h, so the best of them is flattered — small
  edge, thin evidence, never a promise. Real cards: "Use this" sets the exits + `edgeGate`, `edgeFloor` (0/3/6), `runnerMinLiqK`
  (0/25/50/100 $K), `runnerMinBuy` (0/55–70) (`arena_prime.deep_runners`, Edit Fuse › Rounds; all off by default — the owner applies).
  NOT the same as the replay yet: a real card fills an empty runner seat with a pool coin instead of waiting in cash.
- 🚀 RUNNER HUNT (owner's call, then measured; `pg_sim.HUNT/SETUPS/setups`, `pg_sim.json.setups[clock]` → first cards in
  `GET /fuses/strategies`, key `rhunt`): of 92 board picks 21% peaked ≥ 2× within 6h (8% ≥ 3×) after a typical dip of only −6%,
  ~3.5h after the pick. When picked they were ALREADY up 40%+ on the hour on REAL volume ($75K–$245K 1h vs $32K) and ≥ 12h old.
  Hunt = age ≥ 12h · pool ≥ $25K · 1h volume ≥ $50K · 1h move ≥ +40% · stop −30 · freeze +50 · trail 30 · record gate OFF (the
  table marks every coin up > 30% on the hour a loser — true only without the age + volume condition). Walk-forward, 6h windows,
  2026-10-06: 5m +8.5% typical / +16% average, 11 of 14 up, worst −10%; 15m the same; 60m +21% on 6 windows; ~1 buy a card.
  UNDER 6h OLD THE SAME RULE LOSES (−15% typical): age separates a runner from a launch pump. Found by a 486-config sweep on 50h,
  so the level is flattered; the whole neighbourhood (age ≥ 6h + mom ≥ 20) was positive, which is why it ships. Sniper (+15% / −8%)
  can never hold a 2× — Sniper = don't lose, Hunt = catch runners. Real cards: `runnerMinVolK` (0/20/50/100) + `runnerMinChg1h`
  (0/20/40) (Edit Fuse › Rounds; `deep_runners`, `is_hunt`); a coin passing BOTH is bought in rain and storm
  (`weather_runners(cfg=)`: the weather is the no-selection result, and the rain rule used the upside-down score). "Use this" on a
  real card sets exits + selection and turns the −15% instant swap off (it would cut before the −30% stop). Skim / bank / recycle
  stay the owner's — they sell a runner early; the replay does not model them.
- 🚀 OLDER RUNNERS ON THE BOARD (`runners.older_runner`, `OLD_AGE_H` 168, `OLD_MIN_VOL1H` $50K, `OLD_MIN_LIQ` $25K; `_runner_live` keeps
  those pairs; gates `prebond` + `age` pass them): the board dropped every launch coin past 48h — 61 of 111 in the feed — while
  Hunt / Sniper / real money can only buy coins 12h+ old (the board's ages were 31 of 39 UNDER 12h). "BETTER COINS" WAS NEVER AN
  RPC PROBLEM that day (10 of 50 unscanned, one 429): count the feed by AGE before asking for keys. The launch feed itself holds
  only ~111 coins (trending 95 + new 43) — widening it is the next supply step. 📄 Paper tier cards buy runners by the real-money
  rules too (≥ 12h old via `weather_runners(.., 'clear')`, record gate on): they had bled to $6–$17 of $20 on launch pumps.
- ✅ VERIFIED PICKS (replaces "owner picks are never limited" for SAFETY only; cfg `pickVerify`, on by default, Edit Fuse › Safety;
  `runners.pick_check`, `_pick_verify`, `_creator_state`): a hand pick for a REAL card is queued only when the coin passes every
  SAFETY gate (holder scan done, top-10, snipers / bundles, spike, dev share + not sold, creator, mayhem) — judged on the runner
  board's record when it tracks the coin, else on a fresh holder scan of its own pool. Majors / stocks and coins > 7 days in a
  ≥ $100K pool pass as established. Soft gates (age, size, volume, flow), cool-downs and the edge table still never limit a pick.
  A refused pick says what is missing; a queued pick that fails before the bell is dropped and the old coin stays. Why: 2026-10-06
  the owner's hand pick $SpaceX went −98% 3.5 minutes after the bell ($0.38 of a $1 card). WHEN A REAL COIN RUGS, READ THE CARD
  EVENT THAT BROUGHT IT IN FIRST ("🎯 your pick" vs an engine rotate) before touching an engine gate.
- 🏷 Browser tab title (`lib/tabTitle.js` `useTabTitle`, a stack — last mounted wins, the page title returns on unmount): an open
  chart = `$SYM $4.40M MC · $price` (`TrenchChart`), My cards = the real card's ALL-TIME P&L (`HqRealCards`, same number as the tile).
- 🗑 Trench fill follows the card's CURRENT cycle only (it used to fire on `phase == 'trench'` too): an owner who switches Trench
  off gets no more trench coins while the card waits for its next re-shape (a picked cycle with "re-shape: off" re-shapes every 6 rounds).
- 🧩 Real card "Re-shape every 3" is the OWNER's option (`real_guard`: `REAL_OWNER_RESHAPE` 3 when `cycleEvery` is in `realOwnerSet`;
  a value nobody chose is still raised to 6; a safe / rescue fix still re-shapes every 6). The button used to snap back to 6.
- 🌊 MOVERS IN THE LAUNCH FEED (`launchpad_board.JUP_LISTS/jup_candidate`, `market.launchpad_board`, provider `Jupiter` =
  lite-api.jup.ag `/tokens/v2/{toptrending|toptraded}/{5m|1h|6h}`, 100 each, 45s cache; trending board only): launch coins (pump /
  bonk mints) on Jupiter's live rankings join the candidates FIRST (never cut by `BOARD_MAX`); stage comes from the live pair. The
  Pump index pages are "biggest" + "most recently traded", so a coin running on volume was in neither. Every board filter, runner
  gate and real-money rule still applies. FEED THIN ⇒ this is the source to widen (more intervals / categories), not RPC keys.
- `OLD_AGE_H` is 720 (30 days), not 7: Pump's own trending tab was full of pump coins older than a week still trading hard.
  NEVER chain `pytest … | tail -1 && git commit`: the pipe hides the failure (a red test was pushed once, fixed minutes later).
- 🚀 MOVER UPGRADE (real cards, cfg `moverSwap` on by default, Edit Fuse › Rounds; `arena_prime.movers/flat_leg`, block in
  `_prime_tick` before the tick): a runner-seat coin that is NOT moving (±10% of its entry after 20 min; never riding / frozen /
  picked / trench / buying) gives its seat to a coin that IS (the card's hunt selection, else ≥ $50K 1h volume and up ≥ 20%), one
  per card per 30 min (`moverAt`), through `replace_leg` (a normal engine swap: cool-downs, keeper checks, "check the buy then
  sell" all apply). Why: rotation only ever swapped LOSERS — a flat coin held its seat for good while a hunt-ready coin sat on the
  board. 🕐 `runnerMinAgeH` (0/1/6/12, default 12; `weather_runners` reads it): the OWNER may let younger launch coins in; every
  safety gate still applies. The replay backs 12h (under 6h lost ~15% a window) — say so once, then it is the owner's setting.
- ⚙ Edit Fuse v3 (`CFG_GROUPS`): 🎯 Setup (one-tap proven setups + engine pick) · 🪙 Coins (how many / cycle · launch coins the
  card may buy · checks) · ⏱ Rounds · ⚡ Exits (a losing coin · a winning coin · taking profit automatically) · 🧱 Safety. Sub-heads
  = `sub('…')` (`h5.ce-sub`). Each row shows ONE short line (`brief(tip)`), the full text is the hover tip. Follow-up rows show
  only while their parent is on (`on('rideAt')` → trail / off-peak / bank; skim → goes-to; recycle → every; record gate → floor;
  trench cycle → trench coins). 💵 The Fuse WALLET's limits are NOT a tab: `details.ce-wallet` under the editor (real card only),
  labelled "not this card — every real buy and sell". `.ce-row` is flex-wrap with a ≥ 240px name column: a wide choice row drops
  under its name (a grid squeezed "Off its peak" to one word a line). New card setting ⇒ EDIT + one group's `rows([...])`;
  a wallet-wide limit ⇒ `TYPED`, never a card tab.
- 🪑 A SMALL CARD HOLDS THE SEATS IT CAN FILL (`fuse_wallet.fit_seats`, `SEAT_ROOM` 1.25; `_prime_tick` lowers cfg `coins` for
  that tick + ONE `seat-wait` event, card `seatFit`): a seat needs ≥ $0.125 (smallest sendable order $0.10 × 1.25). A $0.39 card
  set to 4 coins had $0.0975 a seat → three seats on "buying… keeper retries" for good while the card bought, trimmed and
  re-bought the one coin it could send. The owner's count comes back by itself as the card grows (seat N opens at N × $0.125).
  "BUYING…" ON SEVERAL SEATS WITH IDLE CASH ⇒ divide the card by its seats before reading the keeper.
- ⚖ A TOP-UP LIFTS EVERY SEAT TOWARD AN EQUAL SHARE (`fuse_wallet.topup_card`, later top-ups; riders / frozen left alone; a seat
  still 'buying' gets the money as `wantUnits`). By-weight spreading put a whole $2 top-up into the one held coin and sold $1.49
  of it back 7 seconds later. 🆕 `arena_prime.FRESH_SEC` 900: `keep_winners(.., now)` carries a coin bought in the last 15 min
  through a re-shape (found live with "re-shape every 3" on 5-min rounds: two coins sold 3.5 minutes after they were bought).
- 🧰 Mini box (`FeeCatWidget` bottom right) = 4 tabs: Chat · Music · 💼 Mine · 🔥 Top 10 (`components/MiniDeck.jsx`, `styles/miniDeck.css`
  `md-*`). Mine = the owner's real tier cards (`/fuses/prime`, owner / staff wallet only) + trader Fuse cards (`/fuses/pnl`) +
  coins held (`useHeldList`). Top 10 = `topTen(pairs)`: launch coins ≤ 12h by 1h volume from the launch feed, 30s poll, row →
  `openCoin`. `mini-bar` = a one-line player (prev · play · next · title) on every tab but Music. Moves ≥ 1000% read as `12.4x`.
  First load ALWAYS runs (`load(true)`); only repeat polls pause while hidden — a `document.hidden` check on the first load left
  the panes blank in a background pane. Jest cannot resolve `react-router-dom` in a bare component test: use `<a href>`.
- 🏆 `GET /fuses/strategies` offers ONLY setups that ended up on the replay when at least one did (the rest are counted in `note`);
  when nothing won, the least-bad ones still show, marked as such.
- 🚪 A FAILING EXIT ESCALATES (`fuse_wallet.sell_escalation`, `SELL_SLIP_MAX` 800 bps; `_fw_execute` + `_fw_quote(order.wide)`):
  a sell that already failed in the last 15 min starts with +2% slippage per failure (≤ 5% after one, ≤ 8% after two) and takes
  Jupiter's best route instead of one-hop first. Buys never escalate. Why: $SI's one-hop sell was refused three times at 3%; the
  keeper sends sells first, so every buy behind it "never landed in 2 min" and the card re-picked seats in a loop with $1.44 idle.
  SEVERAL "buy never landed" EVENTS + ONE failed sell ⇒ the sell is the jam; read its ledger `err` first.
- 💵 THE ENGINE NEVER PICKS A DOLLAR-NAMED TICKER (`fuse_wallet.dollar_named`: USD? / EUR? / ?USD …; filtered from `p_t` + `r_t`
  in `_prime_tick`; the owner may still pick one). A "new major" must be ≥ 24h old (`_prime_candidates`: `newMajor` only then;
  younger rows from Pump's top-by-volume list carry `ageH` / `liq` / `chg1h` and face the launch-coin rules). Why: three different
  half-hour-old "USDF / USDP / USDD" launches with $1.7M seeded pools kept taking the real card's seats through the new-major door
  (exempt from age and from the owner's selection) — "SAME COINS AGAIN" on a real card ⇒ check which DOOR each leg came through
  (`division`, `newMajor`) before touching the feed.
- 🪑 Fill seat (`arena_prime.queue_seat`, card `seatPick`, `POST /admin/arena/prime {fillSeat: {tpl, to, toPair}}` = the pickSwap
  path with `pairAddress '__seat__'`: same live-list / pool floor / verified-pick checks; button `fill-seat` on the real card
  while it holds fewer coins than the owner's count; `SwapPicker out.seat`). The seat refill takes the owner's pick first (leg
  `picked`), on the next tick, with an equal share; `to: null` cancels. Left alone the engine still fills the seat itself.
- 📈 CHART READ (`backend/chart_read.py` pure + tested: `candles/read/keys` — 15-min candles from the recorded 5-min prices of the
  last 4h → structure up / range / down · fair value gap in / above / lost · reclaimed sweep · squeeze · place in range ·
  pullback from high; None under 5 candles). `pick_edge.samples` attaches `keys()` to each judged pick (readings BEFORE the pick
  only) and FEATURES learns `cread` / `cstruct` / `cpos` / `cpull`; `_prime_tick` attaches the same keys to live candidates before
  `rank`. 2026-10-06, 179 picks: chart too short to read −72% typical vs −12% readable · up +1 / range −14 / down −40 · top third
  of its range −2 vs bottom −31 · 5–15% under its high +26% (11 picks). Out of sample the best-vs-worst spread widened 42 → 58
  pts (the losers are found better; the top third is unchanged ≈ flat). FVG, sweep and squeeze did NOT separate winners on this
  record, so they are read but not learned. NEW SIGNAL (stock / options / trench idea) ⇒ add it to `read`, add a FEATURE, compare
  `proof` with and without it — it ships only if the spread grows.
- 🎯 Swap picker lists are DIFFERENT SETS (`PICK_LENSES`): 🚀 Movers (default; `/fuses/discover?lens=movers` = the live launch feed,
  up ≥ 10% on the hour on ≥ $20K in a ≥ $10K pool, biggest hourly move first, no dollar-named tickers, each row labelled
  "30m old · $76K/h") · 🆕 Pump live · 🌊 Volume · 🏃 Runners · 🏁 All ranked · 🪙 Majors · 📈 Stocks · 🚀 New majors · 🗑 Trench ·
  📉 Dip · 🏊 Pools. Popular / Top yield / Deepest / New 72h / Dex paid were five sorts of the same ~40 pools (the owner saw the
  same names under every tab) — a new list must be a new SOURCE, never a re-sort.
- 🪙 Coin drawer accepts a market PAIR too (`asCoin`: `baseToken` → mint / symbol, `stats` from the pair): a pair used to open it
  with no mint → title "$…" and "Reading the coin…" for good. No read after 6s says so. `styles/coinDrawer.css`: slide-in, four
  stat tiles (cap · 1h volume · pool · age), animated 5m / 1h / 6h / 24h move bars (transform only), reading dots.
- 🪙 Coin drawer is ALIVE (`CoinDrawer`, `coinDrawer.css`): `cd-live` backdrop (3 drifting glows + 6 sparks; green rising when the
  tapped timeframe is up, pink falling when down; `--heat` set inline from the size of the move, never animated; off in fx-lite /
  reduced motion) · tap 5m / 1h / 6h / 24h (`cd-tf-*`) to drive it · `cd-spark` live price line since the drawer opened ·
  `cd-vit` vitals (top-10, insiders, dev, bundled, creator, 5m buys / sells, avg trade, stage; bad values pink) · source chips.
  NEVER give `.ce.cd` `position: relative` (the drawer is `position: absolute; right: 0` — it jumped to the top-left) and keep
  `grid-template-rows: none` (the base `.ce` rows stretched the move bars down the whole panel). LOOK AT THE DRAWER after any CSS.
- 🌊 Solana war room = chain discovery WOVEN with the live launch board (`market.py` feed, solana, page 1, no scope): it was
  DexScreener discovery only and looked frozen. `TopCoins` + `EcosystemWorld` lists refresh every 20s (were 90s / 60s).
- 🚨 RUG TIGHTENING (2026-10-06, after 5 pulled coins in one day — every one under 12h old, three under 1h):
  (1) EVERY DOOR OBEYS THE CARD'S MIN AGE on real money (`_prime_tick` `_too_young` on `p_t` AND `r_t`, age from `ageH` or
  `createdAt`): $Grok was dealt 20 minutes old through a list that was never age-checked while min age read 6h, and was pulled an
  hour later (−99.7%). (2) a VERIFIED PICK is ≥ 1h old (`runners.PICK_MIN_AGE_H`; unknown age = not verified) — $CUM (30 min) and
  the other hand-picked rugs were under an hour. (3) `RUG_LIQ` 0.5 → 0.65: a pool that lost a third of its depth is sold.
  A STOP CANNOT SAVE A PULLED POOL (−99% lands between two price checks): the only defence is not holding minutes-old coins.
- 🎯 LAUNCH ENTRY (owner: "get in as soon as a coin drops, with X + website registered — your call"): trench META `launch`
  (`trench.METAS`: ≤ 1h old, cap $10K–$250K, ≥ 150 holders, ≥ 120 trades/h, ≥ $10K 1h + `needSocials` = website AND X set at
  launch, checked in `precheck`; every trench safety check unchanged). 🎟 A trench / launch coin is a SMALL TICKET: cfg
  `trenchStakePct` (10 / 15 / 25 / 0 = full seat, default 15) of the card goes in, the rest of that seat returns to card cash;
  `trenchSlPct` (default 25) is its own stop on the leg (`sl`). Edit Fuse › Coins shows both while the cycle has trench.
  Switched ON for the real card 2026-10-06 by the owner's delegation: `trenchCfg {mode: 'meta', meta: 'launch'}`, cycle `trench`,
  1 trench coin. The replay does NOT back coins this young (under 6h lost ~15% a window; 5 rugs that day were all young) — the
  ticket size is the protection, not the gate. OFF = Cycle back to Press in Edit Fuse › Coins.
- 🍳 LET IT COOK = the card's `minHoldMins` (Edit Fuse › Rounds: off / 15m / 30m / 1h / 2h / 3h) now covers a RE-SHAPE too
  (`keep_winners(.., hold_sec)`), on top of round rotation, mover swaps and trench fills; stops, rug shield, floor and the owner's
  hand still act at once. WHY (real card, 2026-10-06, 71 closed pieces in 9h, −$1.67): 49 exits inside 15 min = −$1.43 (4–17%
  won) · 51 "scratch" exits between −10% and +10% · turnover $46 on a ~$2 card (23×) · only 3 pieces held ≥ 1h, and they ended
  up · owner hand picks 41 pieces −$1.12 (15% won) vs engine 30 pieces −$0.55 · 6 rug pieces −$0.99. The board's runners took
  ~3.5h to peak: a card that turns over every 15 minutes can never hold one. "NO REAL MOVES, JUST SMALL LOSSES" ⇒ group the
  ledger's closed pieces by HOLD TIME before touching selection.
- 🔭 SCOUT & PROMOTE (`arena_prime.scout_step`, cfg `scoutPct` 0 / 10 / 15 / 20, Edit Fuse › Coins; `_prime_tick` runs it once a
  round and it REPLACES the plain mover swap while on): ONE seat is a small ticket that hops onto the best mover; ≥ +20% →
  promoted to a holder (its 🍳 hold starts, the weakest runner seat becomes the next scout and its freed money sizes the promoted
  coin); ≤ −10% or 3 rounds without +5% → hops on. `scout` legs are never topped up (`balance_small`, cash spread). This is the
  owner's "5 min cycles funds to find the banger, holders keep the weight": the fast clock searches with small money, only
  winners get size. Picker: with verified picks on, rows under 1h read "under 1h", are disabled and sort last (`SwapPicker verify`).
- ⚙ Edit Fuse v4 = MAIN + ALL: it opens on ONE pane — 1 · pick a setup · 2 · the six dials that decide a card (`rotateHours`,
  `coins`, `minHoldMins`, `scoutPct`, `runnerMinAgeH`, `sl`). "⚙ All N settings" (`ce-adv`) reveals the v3 tabs; "‹ Back" hides
  them. A dial replaced by another is hidden (mover swap while the scout is on). New setting ⇒ EDIT + an ADVANCED tab; the six
  main dials change only when one of them stops deciding a card.
- 🎛 Trench settings POST is a PATCH (`{trenchCfg: {only what changed}}`, server merges over the stored cfg): the editor posted its
  whole ≤ 30s-old copy and twice put an old `mode` back over a newer one. NEVER write a `//` comment in the middle of a one-line
  JSX / JS statement when patching by string — it swallows the rest of the line (it broke the build twice; use `/* */`).
- 🌊 Movers come from EVERY venue: `jup_candidate` keeps pump / bonk coins (suffix or `launchpad` tag) and ANY other coin ≤ 30 days
  old as `launchpad: 'other'` ("Solana movers": stonk.fun, Meteora DBC, MetaDAO, plain pools — 28 of Jupiter's 100 trending).
  🔭 The scout's ticket may take any safe mover (`r_pre_`: age + checks passed, $50K / +20%), not only the card's full hunt line.
- 🆕 NEW COINS ONLY (real card cfg `newOnly`, Edit Fuse main pane + Coins): `_prime_tick` hands the engine NO pools and NO anchors
  (`p_t = []`, `a_t = []`, deal with `[]`), so every door that reached for a major or an old pool finds none and a seat with no
  qualifying launch coin WAITS IN CASH. The owner's hand picks stay (a re-shape never drops a pick). Why: "still buying the same
  damn coins, ORCA or something" — anchor / pool seats and the "no runner → take a pool" fallbacks kept re-buying the same majors.
- ⇄ HAND SWAP is a door too: on a real card it obeys the min age + no dollar-named tickers, and with `newOnly` it brings a launch
  coin on ANY seat (movers first; the new leg's role becomes `runner`). It used to take the best coin of the SAME KIND — ⇄ on a
  major's seat is what kept buying $ORCA / $TRUMP (ledger: "⇄ swapped by hand"). READ THE EVENT'S WORDS before blaming the engine.
- 🔎 PIPELINE (`_prime_tick` `_step`, card `pipeline` {steps, next, scout}, `PipeLine` under the real card): how many launch coins
  survive each filter on the last tick — safe → wallet pool floor → up on the hour + buyers 55% → weather + min age → record
  gate → the owner's hunt line → not on the card / not cooling. READ IT BEFORE TOUCHING A GATE: on 2026-10-06 it showed 62 safe,
  10 clearing every owner setting and only ONE buyable — the cool-downs were the choke, not selection or RPC.
- 🚀 A coin that is RUNNING NOW skips the long cool-downs (`cooling(.., running)`: movers by the default line or the card's hunt
  line): "left at a loss → out until it recovers (≤ 24h)" and "removed by the owner → 6h" no longer hold it; "no back-to-back"
  (3 rounds, 30 min after an owner removal) still does. A card whose owner swaps by hand all day had locked out its own best coins.
- ⚠ PICK CHECKS WARN, NEVER BLOCK (owner, 2026-10-06: "warn users, don't stop them — they click acknowledge"; this REPLACES the
  blocking in "VERIFIED PICKS"): a hand pick / fill-seat that fails `pick_check` returns HTTP 409 "⚠ $SYM did not pass: …"; the
  card shows `pick-warn` (what is missing + "I understand — pick it anyway") and re-sends the same pick with `ack: true` → queued,
  `swapTo.ack` / `seatPick.ack` kept so the pre-bell re-check leaves it alone. Picker rows under 1h read "⚠ pick" and are
  clickable. The checks still decide the ENGINE's own buys. Never add a hard refusal to an owner action again: warn + acknowledge.
- 🪑 A NEW COIN OPENS ITS SEAT DOWN TO $0.05 (`fuse_wallet.NEW_SEAT_MIN`; the smallest-order rule is for top-ups of coins already
  held): `orders` silently dropped a buy under the card's minimum — a pick that inherited a $0.10 seat against a $0.124 minimum
  was never sent, no ledger row, "buy never landed in 2 min → X took the seat", three owner picks in a row ($MINTRO, $KOMO, $IRL).
  "BUY NEVER LANDED" WITH NO LEDGER ROW ⇒ the order was never CREATED: read `fuse_wallet.orders`, not the keeper.
- ⏭ COMING UP (`pipeline.up` = the coins the engine takes next, best hourly move first, ≤ 6; `ComingUp` under the real card,
  above the pick log): tap a coin → coin drawer (live flow); "swap in for…" select → `pickSwap` for that seat (same warn + ack).
  📈 Swap picker rows carry a baby chart (`GET /fuses/sparks?mints=` → last ~2h of the board's recorded prices, indexed to 1.0,
  ≤ 60 mints, one call per list; `sp-spark` inside the coin cell — the 8-column grid is unchanged) and the ticker opens the drawer.
