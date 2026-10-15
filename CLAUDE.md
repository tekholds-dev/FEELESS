# FEELESS — working rules

> 🧨 Working on Fuse / the real card? Read `docs/DEGEN_PLAYBOOK.md` first — the owner, the money, what the records say, the mindset.
> 🧭 New session / new Claude account? Read `docs/HANDOFF.md` first (the map, the commands, the current state) — then grep this file.

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
- 🩸 ONLY A REAL LOSS LOCKS A COIN OUT (`arena_prime.LOSS_COOL_PCT` 8; cool stamps carry `pct`): "left at a loss → out until its
  price is back above the exit (≤ 24h)" used to fire on ANY exit under entry — a −1% scratch or the owner's −5% instant swap
  locked the coin for a day. One card had 106 such stamps and "13 coins clear your settings → 0 buyable". A scratch exit now sits
  out the 3 rounds only; stamps written before `pct` are not counted as losses.
- ♻ RENT IS VISIBLE (`fuse_wallet.rent_story`, `keeper.rent`, `hrt-rent` in the real card's Activity; `_fw_rent_parked` set by each
  sweep's look at the wallet's coin accounts): parked now (SOL, $, accounts, empty ones closing next sweep) · back to the wallet
  in 24h · last sweeps with tx links · sweep cadence. Measured 2026-10-06: 0.015 SOL parked in 10 accounts, 0.224 SOL returned
  in 24h over 70 sweeps (the same SOL is re-used). The rule is UNCHANGED and now stated on screen: the WALLET's free (unassigned)
  SOL fronts rent and gets it back; the card never pays it and its P&L never includes it — crediting refunds INTO a card once
  made it read $32 in a $6.89 wallet. Moving unassigned SOL into the card is a top-up, the owner's own button.
- ☀ DAY LAG, the real cause: `day-drift` (body + ::before), `day-particles` (`.ambient-background::after`) and `day-sweep`
  (`.terminal-main::before`) animated `background-position` on FULL-SCREEN layers → the whole page repainted every frame. Stopped in
  tips.css (`animation: none !important` under `body.theme-day`; the layers stay, still). To find lag: in the page, list
  `document.getAnimations()` whose keyframes touch anything but `opacity` / `transform` — day theme went 4 → 0.
- ⚡ HQ › Fuse › Engine opens on `EngineFunnel` (`runners.gate_funnel`, admin `GET /admin/runners/funnel`, `styles/engineFunnel.css`
  `ef-*`): coins seen → pass every gate, then ONE row per gate sorted by what it stops ALONE (`only` = its real cost; gold bar),
  tagged safety / soft, with its regret (of the coins it stopped hours ago, how many ran 3×+), a plain sentence naming the gate
  holding the most coins back, and the real card's own pipeline + next in line. The dial (Cold Blood / Voltage / Inferno) and the
  fine-tune fold sit under it. HQ cannot be previewed from a session — it ships on tests; the owner is the first eyes.
- ♻ The rent line must NEVER show a cumulative "+X SOL back in 24h": the owner read "+0.2283 SOL ($27.44)" as $27 of money to split
  and asked for half of it in the card. It is the same ~0.015 SOL parked and returned ~70× a day. Screen now says: parked now ·
  swept N× · "the same SOL each time, never more than parked now, not profit". Any recycled amount is shown as a COUNT, never a sum.
  ⏭ Coming up = 4 rows, labelled NEXT / 2ND / 3RD / 4TH.
- 🗑 QUICK SCRAP (owner, 2026-10-06; this REPLACES "verdict never auto-scraps" for STRATEGIES only): `_verdict_tick` (hourly) takes a
  strategy the verdict marks ❌ off the trader rails by itself (`scrappedStyles` + `autoScrapped`), brings an auto-scrapped one
  back when it turns ✅, never touches a 📌 kept one, audits (`fuse-auto-scrap`) and tells the owner once. `fuse_hq.json.autoScrap`
  false = clicks only. Tier cards, dials and anything on real money are still the owner's click.
- ⚙ HQ Runner settings = 7 vital gates on top (`RUNNER_VITAL`: top-10, buy-share band, 1h volume, cap, insiders, dev) + one fold
  "All N other settings" (lane exits, bond run, light-up, battles). The ⚡ funnel above it says which gate is stopping what.
- ⚡ META BY CLOCK (`arena_prime.meta_for(rotate_hours, seed)` → `/fuses/prime.meta` → `ce-meta` card on top of Edit Fuse's main
  pane, real card, one tap): ≤ 10 min = 🗡 META SCALPER (20% scout, lock +15 / 8% trail, bank 33% at the lock, skim +20, stop −15,
  NO instant swap, hold 15 min, new coins only, movers $50K + 20%, age ≥ 1h) · 15 min+ = 💎 META HOLDER (10% scout, freeze +50 /
  30% trail, no skim, stop −30, hold 1–3h by clock, age ≥ 12h, +40%). 4 variants each (`META_VARIANTS`), picked by an owner seed so
  no two cards trade in lockstep. The patch never sets the clock or the round patience. Every value is a real option
  (test: `clean_cfg` keeps each one). Built on the record, never a promise.
- 🅿 PARKED PROFIT (`skimTo: 'round'`, `skimHoldRounds` 1/2/3/6, Edit Fuse › Exits; `_skim` + `lock_bank` + recycle park via
  `holdCashUsd` + card `skimPark`, `release_parked` in the tick before seats / cash are handled): profit taken from a coin sits in
  card cash — out of the coins, where a pulled pool cannot take it — for N rounds, then joins the idle cash spread back into the
  card. `cash` still means "held for the owner, never re-spent".
- 📈 A coin opened from a Fuse card carries that card's levels (`fuseLevels(l, cfg, label)` → `openWarRoom({.., fuse})` →
  `WarRoomHost` → `EcosystemWorld` keeps `fuse` on the chart pair → `TrenchChart` strip `chart-fuse` + `PriceChart` lines: ⚛ card
  entry · 🛑 stop · ❄ locks · 🏔 trail when riding). `WarRoomHost` used to pass only chainId + pairAddress — anything else on the
  pair was dropped.
- 🔄 REBUY (owner: "sells the coin and rebuys at a new entry"; `arena_prime.rebuy_out/rebuy_in`, `POST /admin/arena/prime {rebuy:
  {tpl, pairAddress}}`, button `chart-fuse-rebuy` on a Fuse coin's war room strip → event `feeless:fuse-rebuy` → confirmed in
  `HqRealCards`): step 1 the coin leaves the card whole, its money is held aside (`holdCashUsd`, card `rebuy`) and the seat is
  spoken for (no refill); step 2 (each tick) once the WALLET no longer holds the coin the money is released and the same coin is
  queued as an acknowledged `seatPick` → bought at today's price, so the BOOK has a true new entry. Not landed in 10 min → called
  off, money released. Never "re-base" an entry without the two swaps: `sync_card` copies the book's `entryPx` to the card, and
  changing the book's cost basis without a trade would falsify realized P&L. First live rebuy = watch the ledger.
- ⏭ COMING UP + the scout are ordered by `arena_prime.flow_rank` (`flow_tag`: entry setups 🧹 sweep & reclaim / 🚀 breakout /
  🧲 pullback first, then the coin's own chart — 🪜 back in its gap · 🧲 dip bought, trend up · 📈 trending up · 🏔 at its highs ·
  ➖ ranging · 📉 trending down · 🆕 no chart yet LAST — plus ≤ 25 pts for the hourly move). Rows carry `tag`, shown under the coin.
  Why: of the real card's last 119 buys, 99 had a chart too short to read (−$1.01, 25% won) and 20 a readable one (+$0.07, 40%).
- 🆕 A COIN BOUGHT MINUTES AGO IS NEVER THE CARD'S BIGGEST SEAT (`spread_cash(.., cap, fresh)`: for a leg bought < `FRESH_SEC` the
  idle-cash share is capped at the WHOLE card's equal share): with two coins riding, the equal share among the unlocked ones is
  half the card each — $AGENCY replaced a finished rider with a $0.48 seat and the freed / parked cash lifted it to $2.03 a minute
  later (then −9%). Banked money still spreads over the older coins in full (existing rule + test).
- 🔁 COMEBACK (`arena_prime.comeback_note/comeback_step`, card `comeback`, cfg `comeback` on by default; Edit Fuse › Exits): a
  RIDER that leaves the card is watched for 2h; once it dipped ≥ 3% under its exit and recovered 15% off that low it is tagged
  "🔁 comeback" (top of `flow_rank`, 95 pts), exempt from the long cool-downs and first in the scout's list. 60% under its exit =
  over. 🪜 STEPPED TRAIL (`trail_for`, cfg `trailStep`, on in the meta scalper): a rider's trail is the owner's own under +30%
  peak gain, ≥ 15% from +30%, ≥ 25% from +80%. Why (57 min of the meta scalper on the real card): 15 trims +$1.90, 100% won ·
  13 full exits −$0.01, 31% won · three riders left on 8% wiggles ($SNDWITCH swapped out on the way to +128%).
- 🟢 PUMP MOVED ITS COIN RECORD: `/coins/{mint}` answers 404, the record lives at `/coins-v2/{mint}` (market.py graduation read,
  the logo fallback, the rail check all pointed at the dead path → blank logos / "profile not showing"). `launchpad_board.pump_profile`
  (pure, tested) → `GET /api/reputation/pump-profile/{mint}` (60s cache) → `PumpProfile.jsx` (`usePumpProfile`, `styles/pumpProfile.css`
  `pp-*`): logo, links (http(s) only), creator → case file, graduated / on the curve, cap vs ATH (Pump's ATH is already in $), 1h
  volume, pool, replies, live. Shown on the coin page (also when the coin has NO pool yet), compact in the coin drawer; the war
  room chart's "Profile ↗" opens `/terminal/coin/<chain>/<mint>` (it opened the chat). A PUMP FIELD READS BLANK ⇒ curl the endpoint first.
- 🎇 Card FX (`CardFx.jsx` kinds aurora · grid · beam · embers, `styles/cardFx.css` `cfx-*`): `<CardFx kind tone />` as the FIRST child
  of a card with class `cfx-host` (isolated; layers at z-index −1, own DOM nodes — never the card's ::before / ::after; transform +
  opacity only; hidden in fx-lite / reduced motion; `.cfx` itself is in `FX_SURFACES` — pausing the HOST froze its fade-in half way).
  On: coin profile cards, Pump profile, weather strip, best-Fuse tile, mini Top 10, share preview. NOT on a grid whose rule styles
  `> span` (e.g. `hrt-hero`). New card ⇒ pick one of the four, never a fifth one-off backdrop.
- 🖼 Share = a STILL first (`shareGif.renderShareCard`: the same card at 2×, 1440×810 PNG, dot lattice + corner brackets + UTC stamp),
  spinning 180° into place (`gifSpin`, re-keyed per design); 🎞 Animate renders the GIF only when asked. Keep `perspective()` INSIDE
  the transform: a `perspective` parent left the finished image unpainted (blank preview) in Chromium.
- 🪙 A NEW MAJOR MUST TRADE LIKE ONE (`fuse.solid_major`, applied in `_prime_candidates`): 24h volume ≥ 1% of its market cap, volume ≥
  half its pool, cap ≤ $250M, a logo — else the row is not offered at all. $VSOF ("$667M" cap, 0.1% traded, no logo) took a real seat.
- 🅿 Per-coin 💰 has a manual PARK (`skim.to: 'round'`): that coin's profit sits in card cash for the card's own `skimHoldRounds`,
  then `release_parked` puts it back to work.
- 🛑 A RESERVED SEAT IS NOT A COIN (`fuse_wallet.sync_card`: a `placeholder` leg holds nothing and wants nothing; never in `empty` /
  `waiting`; the stop-out placeholder in `arena_prime` no longer carries `wantUnits`). A stop with no replacement ready left a
  placeholder still carrying the STOPPED coin's mint, the sync read it as "a buy that has not landed" and the keeper bought the coin
  straight back: $TikPad stopped at −15%, re-bought 17s later for $1.64, sold at $0.90. "SELL X … BUY X" SECONDS APART IN THE LEDGER
  ⇒ look for a placeholder leg with that mint before anything else.
- 🧭 UP NEXT IS META (`arena_prime.meta_ready/meta_only`, cfg `upMeta` on by default, Edit Fuse › Coins; `_prime_tick` filters `r_t` +
  the scout's `r_pre_` and adds a pipeline step; the chart read is attached to every candidate, edge table or not): the ENGINE buys a
  coin by itself only when its chart is long enough to read and is not trending down; a 🔁 comeback always may; never read = out;
  the owner's picks are not judged. No qualifying coin = the seat waits in cash. Why: 99 of 119 buys had no readable chart (25% won);
  $darwin ("no chart yet", +22% hour) hit its stop 6 minutes after the buy.
- 📈 UP NEXT READS THE MARKET'S CHART (`chart_read.points_from_candles/why_not`, `_chart_fill` in `_prime_tick`: real cards, ≤ 14
  candidates a tick, candles service 15m, 4 min cache, tests never fetch): the board's own price record starts when IT first saw a
  coin, so the best movers (new to the board) all read "no chart yet" and the meta gate left Coming up EMPTY (12 clearing every
  setting → 1). ⏭ Coming up is never blank: ready rows (NEXT / 2ND …) then 👀 watching rows (`pipeline.up[].wait` = the reason, dashed,
  gold), which the owner may still swap in by hand. "N READY · M WATCHING" in the label.
  `META_MIN_POS` 0.34: a RANGING coin in the bottom third of its 4h range is watched, not bought (record: bottom third −31% typical vs top −2%).
- 🎨 CHART BACKGROUNDS (`lib/chartBg.js` `CHART_BGS` + `useChartBg` — ONE choice for every chart, localStorage `feeless.chartBg`;
  `components/terminal/ChartBg.jsx` + `styles/chartBg.css` `cbg-*`; picker `chart-bg-pick` in the TrenchChart toolbar): ▫ Default ·
  ⚛ Fuse reactor (3 gyroscope rings + ions around the mark) · 🌀 Warp gate (gates + FUSE flying out of the vanishing point) ·
  🧬 Fuse helix (a double strand turning in true 3D) · 🐱 FeeCat prowl (the cat swaying, paw prints, flipping FEE coins). The scene
  is a layer BEHIND the candles: `PriceChart` makes its own background `transparent` while one is on (`bgOn`; the chart is rebuilt
  on the switch) and falls back to the plain chart in fx-lite / reduced motion. perspective + preserve-3d, transform / opacity
  only, `.cbg` in `FX_SURFACES`, marks ≤ 28% opacity so candles stay readable. New scene ⇒ `CHART_BGS` + a `kind` branch + CSS + test.
  The Browser pane's screenshots lag one frame behind the DOM while it is in the background — screenshot twice before judging.
- 🧾 FUSE PROOF (`backend/fuse_proof.py` pure + tested; `_proof_build` 30s cache kept warm in `_fuse_warm`; public `GET /fuses/proof`;
  `FuseProof.jsx` + `styles/fuseProof.css` `fpf-*`, ONE section on the Fuse landing with three lenses `PROOF_LENSES`):
  🃏 Pick a card = setups side by side, each with ITS OWN record and its source (`replay` walk-forward windows · `real` = a real
  card's ledger: put in → now, closed pieces won, profit takes vs full exits; "proven" for a real card needs a POSITIVE result on
  ≥ 20 closed pieces — a losing card reads as losing) · 🧾 Live proof = the real cards' CONFIRMED swaps (filled + signed, 24h) with
  the engine's reason from the nearest card event and the tx link (a buy reads "in for $OLD: …") · ⚔ Real duels = each real card vs
  the best other card for 24h on % result (`duel_step/duel_view`, own file `data/fuse_duels.json`, W/L/D record; the owner may pick
  the challenger: admin prime `{duel: {tpl, vs}}`, which calls the running duel off with no result). Points only, never a stake.
  "⚡ Build with its coins" loads a real card's coins into the Lab (the visitor signs every buy); replay setups → My cards.
- 🧾 WHY IT BOUGHT (`arena_prime._leg` → leg `bought` {tag, chg1h, vol1h, ageH, buyShare, liq}, in the card view; `hrt-why` on each
  real-card coin row, full sentence in the tip; "🎯 your pick" for hand picks). Legs bought before this have no line.
- Entrance keyframes on CONTENT are transform-only (`fpfIn`): starting at opacity 0 leaves the content invisible wherever the
  animation clock is not running (a background pane). NOT BUILT of the six ideas: hands-free user cards (needs the audited contract).
- 📈 COIN DRAWER HAS THE CHART (`cd-chart` in `CoinDrawer`: the SAME `PriceChart` the war room draws, lazy-loaded, 230px, timeframes
  1m / 5m / 15m / 1h, `⚔ War room` button ABOVE it; the tick spark line is gone). It floats (`cdFloat`, 4px) on a turning Fuse
  gradient frame (`cd-disco`, a rotating conic layer behind a 2px gap — transform only). In the drawer the chart's foot chips /
  style toggle / source note are hidden (they covered the time axis). `.ce.cd { grid-auto-rows: max-content }`: with `auto` rows a
  clipped card (overflow hidden) was squeezed under its content and the next row drew over it (chart axis + the Pump link row cut).
- ⚡ FAST STOP (`arena_prime.fast_stop`, `GUARD_SEC` 6, in `_real_guard_loop`): the guard no longer only WAKES the tick. A real card's
  coin at its plain stop is taken off the card by the guard itself (placeholder seat, cool-down stamped, under `_prime_tick_lock`),
  `_fw_tick` sells at once, THEN the full tick runs (refill, riders, instant swaps). Riders' trails, instant swap, park / hold
  modes, frozen coins, safe majors and a > 50% "loss" in a leg's first 90s (feed gap) stay with the tick. Why: $AGENCY fell −22%
  inside ONE minute; waking the whole engine pass (candidates, every card, charts) logged the stop ~2 min later → −31% on a −15% stop.
  A STOP FILLS FAR PAST ITS LINE ⇒ pull the coin's 1-minute candles and compare the crash minute with the `sl` event + ledger times.
- 🌪 TOO WILD (`chart_read` `wild` / `cWild` = deepest high → low fall inside ONE 15-min candle over the last hour; `WILD_PCT` =
  `arena_prime.META_WILD_PCT` 35): the engine does not buy it (meta gate; Coming up reads "watching — too wild: −53% inside one
  candle this hour"). $AGENCY had fallen 53% in 5 minutes twenty minutes before it was bought. Owner picks are not judged.
- Start page + home tile: a REAL card's headline = ALL TIME (`FuseLanding.cardResult`: math.pnlUsd ÷ putIn; paper = its run) and
  `heroCard` ranks on that same number ("+20% this run" sat above "−35% all time"). The small line still says "this run +X%".
- Card FX also on: Runners hero (embers, gold), Coming up (grid), profile TraderCard (beam), Fuse score (aurora), held cards (grid),
  my battles (embers). Chart background picker = 40px wide (icon only): a wide select wrapped the toolbar's Alert button onto two lines.
- ⏳ THE STUCK-BUY SWAP IS A DOOR TOO (`_prime_tick`: the block now runs AFTER min age · dollar names · record gate · chart / meta ·
  the owner's hunt line, just before `mine`): it used to run before all of them, so a refused buy was replaced by ANY liquid coin
  ($BTT, "−100% inside one candle", took the seat, was refused too, and the seat looped). No qualifying coin → the seat goes back to
  card cash. `fast_stop` only acts on legs the wallet HOLDS (`real`, set by `sync_card`): a coin dealt this tick and not bought yet
  was "stopped" on the gap between its scan price and the live price. EVERY new path that puts a coin on a real card must read the
  SAME filtered `r_t` — grep `replace_leg(` in `_prime_tick` and check where each call sits relative to the filters.
- 🚪 SOLD WHOLE = OFF THE CARD (`arena_prime.tick`, take-profit / ride-end branch): a coin whose ride ended with NO replacement
  ready stayed on the card as a 0-unit leg; the next coin's "smart compound" poured money back into it and the keeper re-bought the
  coin that had just been sold ($DONSOM sold 18:24:12, wanted again 13s later: "buying…" + a refused buy). The leg is now removed
  (never the card's last one), compound never targets an empty / reserved seat, the seat refills when a coin qualifies. THREE
  versions of this bug so far (stop placeholder, unbought leg "stopped", ride-end leg): A LEG WITH 0 UNITS THAT STILL CARRIES A MINT
  IS A BUY ORDER WAITING TO HAPPEN — whenever a coin is sold whole, the leg must become a placeholder with no want, or leave.
- 📌 MINI CHART (`components/MiniChart.jsx`: `openMiniChart(pair)` + ONE `MiniChartHost` in the terminal shell, `styles/miniChart.css`
  `mch-*`): the 📌 button in every chart's toolbar (and in the coin drawer) closes the war room / drawer (`EcosystemWorld` listens to
  `feeless:mini-chart` → `onClose`) and keeps the SAME `PriceChart` in a 360px floating window on every page — docked bottom-left
  (FeeCat owns bottom-right), draggable by its header, 1m / 5m / 15m, live price + 5m move, ⚔ reopens the war room, × closes. The
  coin and the window's place live in localStorage `feeless.miniChart` (survives page changes and reloads).
- ✨ CARD POPS (`components/CardPops.jsx` `popsFrom` / `nearTargets`, `styles/cardPops.css` `cpop-*`; wrapped around the card art of
  the real card and every tier card): a number floats off the card when money goes back to work or profit is taken (`+$0.25 ♻
  COMPOUND`, `💰 PROFIT`, `🏦 BANKED`, `🔒 $SYM LOCKED`) — only for events that arrive AFTER the card is on screen; a folded compound
  line pops its `lastUsd`, not the half-hour total. A coin in the last quarter before its lock / take-profit line shows a charging
  chip at the foot of the card (`⚡ $SK +13% · lock +15%`). Overlay only; numbers hidden in lite mode / reduced motion.
- 2026-10-06 real card, last hour: 44 swaps, $46 turnover on a ~$6 card, buys filled 1.9% above the mid price on average, 10 hand
  picks. Realized −$0.13; the rest of the fall was open positions + entry cost. TURNOVER × ENTRY COST is the leak to quote, not fees ($0.05).
- ✨ Card pops, calibrated (owner: "too big, too often, not the real compound"): a REAL card pops only CONFIRMED fills
  (`popsFromFills(realBook.orders)`: a filled buy whose reason is "idle card cash back into its coin" = COMPOUND, the $ that went
  in; a filled sale above its cost = PROFIT, the $ gained) — never the engine's per-tick "idle cash back into the card" intent.
  ONE pop at a time, ≥ `POP_MIN_USD` $0.05, at most one per `POP_EVERY_MS` 20s, 14px, OUTSIDE the card at its top-right corner
  (`left: 100%`). Paper tier cards keep the engine events under the same limits.
- 🪑🪑 FILL EVERY SEAT AT ONCE (`arena_prime.queue_seat(card, cand, more=)` → `seatPick` + `seatQueue` ≤ 5, one per coin; view
  `seatQueue`; `fillSeat.more` from the picker): the owner picks a coin for EACH empty seat — the picker stays open until every seat
  has one, the button reads "🪑 → $A · $B · $C" — and the seat refill seats ALL of the owner's picks on the same tick (a loop; the
  engine's own choice still fills one seat a tick). A pick without `more` still replaces the first; `to: null` clears them all.
- 🪑 THE OWNER'S SEAT PICKS OUTRANK PARKED PROFIT (`arena_prime.tick`, before free cash is counted): with seat picks queued and an
  empty seat, `skimPark` is released at once to fund them (event "parked profit released for the seats you picked"). Found live:
  three picks waited on a ONE-coin card whose whole $1.50 of cash was parked and whose only coin was locked (untrimmable).
  `release_parked` now also runs BEFORE `free_cash` is computed (released money used to sit one more tick).
- 💚 FULL STACK → SKIM TO THE STAKE (owner's system, 2026-10-06: "once we lock all coins it's love — it skims down to a dollar, then
  anything above"; `arena_prime.stack_skim`, cfg `stackSkimUsd` 0 / 0.5 / 1 / 2 / 5, off by default, Edit Fuse › Exits): while EVERY
  coin is locked (`stack().full`), each coin is cut down to that $ of value and whatever grows above it is taken again every tick
  (≥ 5c); the money follows `skimTo` (card cash · parked · held); a coin under the stake is left alone; the stake keeps its trail.
  Event kind `skim` with `stack: True`. Switched ON at $1 on the owner's real card the same day (their words named the number).
  THE OWNER'S DIRECTION: stop reporting fees; build UNIQUE CARD SYSTEMS (each card its own behaviour) — lead with those.
- 🎚 POP TIERS (`CardPops.popTier`, `POP_TIERS`, `POP_MIN_USD` 0.20): 20c–$1 the plain number (`t1`) · $1+ green sparks (`t2`) ·
  $5+ gold, coin burst + ring, "BIG" (`t3`) · $20+ rays + confetti, "JACKPOT" (`t4`); a bigger win stays ~0.5s longer per tier.
  Tier classes are written as literals in the JSX (`['', 't1', …][tier]`): a template `t${tier}` reads as a dead rule to cssHygiene.
- 📌 Mini chart shows where you stand (`MiniChartBody.jsx`, lazy): the Fuse card's lines on the chart (carried on `pair.fuse` from
  where it was opened, else found on the live cards by coin via `usePrime` + `fuseLevels`) AND your own FEELESS trades on the coin
  (`useMyPosition`: entry line + buy / sell marks) — strip `mch-strip`: ⚛ entry · % since · 🛑 stop · ❄ lock · 👤 your entry · %.
- 🔥 DON'T CHASE (`arena_prime.chase_why/meta_why`, `CHASE_5M` 3, `CHASE_1H` 100; inside `meta_ready`, so cfg `upMeta` switches it):
  the engine does not buy a coin that is up > 3% in the last 5 minutes or > 100% on the hour — Coming up reads "watching — too hot:
  +14% in 5 min — waits for it to cool". A comeback is exempt. The owner's hand pick of such a coin gets the same reasons as a
  WARNING through the 409 + acknowledge path (never a block). Evidence = the pick record's own buckets (184 picks, 3h result):
  5m −3…0 → +3% · 0…+3 → 0% · +3…+10 → −41% · over +10 → −77%; 1h 0…+30 → +3…+6% · +30…+100 → −14% · over +100 → −55%.
  The "🚀 breakout" entry tag (5m ≥ +3) therefore never qualifies for an engine buy any more. Real card, same afternoon, 90 min:
  −$1.53 realized, the six worst pieces all bought mid-spike and gone in 1–12 min (five hand picks, −15…−29%).
- 📌 MINI CARD (`components/MiniCard.jsx`: `openMiniCard(src)` + ONE `MiniCardHost` in the terminal shell beside the mini chart; lazy
  `MiniCardBody.jsx`; `styles/miniCard.css` `mcd-*`, shell = the mini chart's `.mch`): the 📌 `fcd-pin` button on every
  `LiveFuseCard` given a `mini` prop (tier cards, the real card, the landing hero, cards you hold) keeps that Fuse card floating on
  every page. Two sides: 🃏 the SAME card (tier look, still flips to its live money) ⇄ 📈 the chart of any of its coins (coin chips
  with each coin's %, 1m / 5m / 15m, the card's entry / stop / lock via `MiniChartBody`); ⤢ cycles three sizes (S / M / L = card
  zoom + chart height tokens `--mcd-zoom` / `--mcd-h`); draggable; card, side, size, place live in localStorage `feeless.miniCard`.
  `src` = `{kind: 'prime', tpl}` (always read live from `/fuses/prime`) or `{kind: 'row', row}` (a held card travels as a snapshot
  of its coins; live prices still revalue it). View only — no money button in the window.
- 📌 Mini chart + mini card charts open on MARKET CAP like the war room (`MiniChartBody metric`, header `$329K MC`, strip levels in MC,
  `mch-metric` button MC ⇄ $). The cap comes from the shared live-price poller (`lib/livePrices` record now carries `mc`) — no new fetch.
- 🎨 Chart backgrounds are now ▫ Default · ⚛ Fuse reactor · 🧬 Fuse helix · 🌅 Sunset ocean (slow sun, light path on the water,
  drifting swells) · 🌌 Aurora night (stars, three swaying veils, a ridge). Owner: keep the two Fuse scenes, the rest CALM — Warp gate
  and FeeCat prowl are retired (a stored 'warp' / 'cat' falls back to Default). A new scene must be calm; each has its own day palette.
- 🏔 AT ITS HIGHS = WATCHED, NOT BOUGHT (`arena_prime.at_high`, `META_MIN_PULL` 5; inside `meta_ready`, so cfg `upMeta` switches it):
  a coin less than 5% under its 4h high is not bought by the engine — Coming up reads "watching — at its highs: 1% under its 4h
  high — waits for a 5%+ dip"; `flow_tag` ranks it under every dip / trend tag (40 pts). A comeback is exempt; no pull reading =
  not judged; the owner's picks are not judged. Owner: "15% off dips is good, but if it's up wtf" — "at its highs" had been the
  NEXT coin to swap in. Record: 5–15% under the high +26% typical (11 picks), top third of the range about flat.
- 🧰 CHART TOOLS on EVERY chart (`lib/chartTools.js` pure + tested, `components/terminal/ChartTools.jsx` `ChartToolsMenu` + `useToolDraw`,
  `styles/chartTools.css` `ctl-*`; the 🧰 button lives INSIDE `PriceChart`, top-left, so the war room, coin drawer, mini chart and
  mini card all get it; one choice for the site, localStorage `feeless.chartTools`): 🪜 FVG (open 3-candle gaps; shrink as they
  fill, gone once traded through) · 🧲 Magnets (untaken equal highs / lows, ×N touches) · 🔫 Gun line (nearest swing high overhead =
  the trigger; above every swing = "fired") · 🦠 Germ (base candle of the biggest run on screen; a close under it = lost) ·
  ⚡ Meta edge (all four + `edgeRead`: score 0–100, 🟢 EDGE / 🟡 WAIT / 🔴 NO EDGE, one-line plan, reasons on tap). Levels = price
  lines; gaps + germ also draw soft bands (plain divs appended to the chart container, placed from `priceToCoordinate` /
  `timeToCoordinate` every 300ms, removed with the chart). Read from the candles on screen, labelled "not advice". The edge
  score's weights are hand-set, NOT learned from a record yet — never quote it as proven. `PriceChart` now keeps `chartRef`.
- ✋ GRAB YOUR LEVELS (`lib/chartGrab.js` pure + tested: `GRAB`, `snapLevel`, `grabLevels`, `withGrab`, `grabOrder`;
  `components/terminal/ChartGrab.jsx` + `styles/chartGrab.css` `cgr-*`, rendered by `PriceChart` only when `fuse.tpl` is set = a
  coin opened from the REAL card): a tab sits on each line the card lets the owner move — 🛑 stop + ❄ lock (🎯 take-profit when the
  card has no lock) while proving, 🏔 trail once riding. Drag = it snaps to the editor's OWN options (`GRAB` lists mirror
  `arena_prime` LEG_SLS / LEG_TPS / RIDE_ATS / RIDE_TRAILS — change both) and shows the % while held; letting go fires
  `feeless:fuse-level` → `HqRealCards` asks (`window.confirm`, says "only this coin" for stop / TP → `{leg: {sl|tp}}`, "every coin
  on the card" for lock / trail → `{realCfg: {rideAt|rideTrail}}`) → saved → `feeless:fuse-level-done` moves the line. A cancelled
  or unmoved drop changes nothing. `fuseLevels` now also carries `peak` + `tpPct`. Tabs sit at 40% across (top-left is the 🧰 menu).
- ✋ DRAGGED LEVELS MOVE IN 1% STEPS (replaces "snaps to the editor's options"): `arena_prime.STEP_RANGE` sl 5–50 · tp 10–500 ·
  rideAt 5–200 · rideTrail 3–50 + `step_ok` (a whole % in range) accepted by `set_leg`, `clean_exit` and `clean_cfg` next to the
  old lists; `lib/chartGrab.js` `GRAB` min / max mirror it (change both). Edit Fuse shows a dragged value as its own chip
  ("✋ +17%") and the per-coin TP / SL selects add it as an option, so a custom value never reads blank.
- 🎨 Chart backgrounds = Default · ⚛ Fuse reactor · 🧬 Fuse helix · 🌅 Sunset ocean · 🌌 Aurora night · 🏔 Misty peaks (dawn, three
  ridges drifting at different speeds, valley fog) · 🌸 Sakura drift (moon over still water, 14 falling petals) · 🪼 Deep sea (sun
  shafts, three rising jellyfish, bubbles). Each calm scene has its own day palette; phones drop a third of the particles.
- 🚪 OPEN GATES + 📣 CALLOUTS (owner: "make the trench category the open gates — what Pump sees — plus callout tracking every 3–4
  min"; `trench.open_row/front_score/open_board/callouts/callout_feed`, `_open_pairs` filled by `_runner_live` with EVERY raw feed
  pair whatever its age, `_open_board`, `_callout_tick` in `_fuse_warm`, public `GET /fuses/trench/open`, `TrenchOpen.jsx` +
  `styles/trenchOpen.css` `top-*` on top of every `TrenchScan`): the trench list with NO filter — every launch coin the feed sees
  (Pump's biggest + most recently traded, launch boards, Jupiter live trending), ranked by `front_score` (1h volume, trades, 5-min
  pace, buyers, green hour: ACTIVITY only), each marked ✅ passed the safety scan · ⚠ did not (`fails`) · ❔ never scanned. The
  same rows are appended to `/fuses/trench.rows` (`soft` + `open`) so the picker's 🗑 lens lists them after the passing coins:
  owner-pickable through the usual warn + acknowledge path, NEVER auto-seated — the engine's trench fill still reads only passing
  coins. 📣 Callouts every `CALLOUT_SEC` 210s: 🔥 volume leader (top 5 by 1h volume) · 🚀 mover (top 5 by 5-min move, ≥ $5K in
  those 5 min) · 🆕 fresh launch (≤ 1h, ≥ $10K 1h); a coin is noted ONCE per kind at that price and settled 1h later through
  `meta_track` / `meta_proof` (no price = −100%), `data/trench_callouts.json`; the feed shows the move since the call (live) or
  the 1h result. Pump's public API has NO callouts / trending endpoint (probed 2026-10-06: only the coin index + currently-live
  answer) and the fomo app has no public feed — these callouts are FEELESS's own read of the launch feed; say so, never label
  them "Pump's callouts".
- 🍼 Trench meta `baby` (first in `trench.METAS`; owner: "trench should be a yolo top trending / new, no snipe or rug, brand new
  baby"): ≤ 3h old, cap $10K–$1M, ≥ 100 holders, ≥ 60 trades/h, ≥ $5K 1h — the loosest crowd checks the option lists allow —
  with every safety check (top-10, insiders, bundles, dev, creator, mint + freeze, buyers ≥ 55%, green) unchanged. Set on the
  owner's real card 2026-10-06 (`trenchCfg {mode: 'meta', meta: 'baby'}`; previous value in `data/realcfg_before_baby.json`). The
  trench ticket size + its own stop (`trenchStakePct` / `trenchSlPct`) are still what limits the damage; the replay does not back
  coins this young.
- ⚛ FUSE ROOM (`components/FuseRoom.jsx` + `styles/fuseRoom.css` `frm-*`, mounted once in `FusePage` → every Fuse tab): a slim
  glass tab on the right edge (spinning ring mark) opens a 330px glass panel, hides again with ›; open / room remembered
  (`feeless.fuseRoom`); it polls ONLY while open. Three rooms `FUSE_ROOMS`: 🔥 Big moves (`bigMoves`: a real card's sale that won
  or lost ≥ 10%, any swap ≥ $5, a callout ≥ ±25% — never all activity) · 💬 Lounge (the `fuse-lab` chat) · 🎯 Radar (entry setups
  now + the top front-runners with their safety mark). Glass = translucent gradient + inner highlight, NO backdrop-filter (the
  page behind is animated). War-room coin chat (`.eco-chart-chat`, a 240–300px column): message children get `min-width: 0;
  max-width: 100%` (a coin card message was wider than the column) — rules in tips.css.
- 🧹 Cleanup pass 2026-10-06: every unused import / variable eslint (`no-unused-vars`) and pyflakes report was removed (14
  frontend, 5 backend; `env_loader` imports are side-effect imports and stay). Animation audit on Fuse › Arena: 163 running, ALL
  transform / opacity (to re-check: list `document.getAnimations()` whose keyframes touch anything else). NOT done: the
  reputation_service.py split, the 91 `exhaustive-deps` suppressions.
- 🎯 A QUEUED PICK COMES IN 5 POINTS BEFORE THE STOP (`arena_prime.near_stop_picks`, `PICK_NEAR_STOP` 5; `apply_queued(only=, why=)`,
  run every tick BEFORE the stop pass): a coin with a pick waiting (`swapTo`) that is within 5 % points of its own stop is swapped
  for the pick NOW ("swapped in early"), else at the round bell as before. No live price / not bought / no stop = waits for the bell.
- ✂ THE OWNER'S CUTS (2026-10-06, "do all those you suggested"): (1) Prime League = the real card(s) + the ONE best paper card
  (`ArenaPrime.primeGroups`); the other paper cards sit in `details.prime-rest` (they still run and keep their record). (2) The
  Pit zone is now 🏟 Main Stage: the stage first-class, the battles / league / throne behind `PitFold` (a button; closed = NOT
  mounted, so none of its animations run; `zone=all` opens it for tests); the ember sky (`ar-sky`) is gone. (3) Trench metas = TWO
  (`baby`, `breakout`); the `needSocials` check stays in the gate for a custom gate. (4) `trenchAuto` (cfg bool, default on; Edit
  Fuse › Coins "🗑 Engine may buy trench coins"): off = `_prime_tick` hands the engine NO trench rows — they stay listed and
  hand-pickable. Set OFF on the owner's real card the same day (`data/realcfg_before_trenchauto.json`). NOT cut: Edit Fuse's
  "All settings" — the real card runs on settings that live only there (skim, stack skim, hunt line), so it stays one click away.
- 🏁 Prime League opens on the LEAGUE TABLE (`ArenaPrime.standings` + `PrimeStandings`, `styles/primeLeague.css` `pls-*`): every
  tier card as a lane in one race, best first (👑 leader, 💵 REAL lane marked, a bar per result, live %), one line with the real
  card's gap to the best paper card; a lane tap scrolls to that card and opens its fold. Then the real card + best paper card,
  then the folded rest.
- ⚔ Main Stage shows the TWO live fights again (`StageBattles.jsx` + `fightRead`, `styles/stageBattles.css` `sbt-*`): two corners
  jabbing at each other with a 💥 clash, 👑 on the leader, live % since the bell, a rope whose knot slides toward the leader
  (sparks first, card move as tie-break), one ⚡ pip per seat duel (tip = both coins), the bell clock and a one-line 🎙 call.
  "Full fight, table & throne" mounts the old Battlefield underneath (`PitFold b=`; no live pair = the plain show button).
  Points only — never a bet. Max 2 fights on screen, always.
- 🖼 Share card v3 (`lib/shareGif.js`): `depthFx` under every design, royal included — god-rays turning behind the mark, a
  perspective floor rolling toward the viewer, twinkling stars, plus one extra per design (royal data rain · blaze embers · ice
  snow · nebula shooting star; gold's rays are brighter). Fuse shares add: the all-time % beside the big number (`card.bigSub`),
  four vitals tiles (`fuse.vitals`: put in · in card now · profit pulled · swaps / hour), a move bar under each coin on the mini
  card and its "$X in → $Y now" foot (`fuse.foot`). The brand moves to one line under the tiles on fuse shares.
- ⚔ Stage battles show each fighter's REAL Fuse card (`PitFold` builds `cardNode(key, move)` from the Arena cards → `StageBattles`
  `.sbt-card`, `zoom: .62`, pointer-events none); the emoji is only the fallback for a card that is off the board.
- 🎬 Live cover: `frontend/public/cover.html` (standalone, served at `/cover.html`; no app code): a 1500 × 500 canvas — turning
  rays behind the mark, rolling floor, a made-up candle run scrolling by (never a real price), the Fuse helix, the wordmark and
  taglines — with ⬇ still PNG, ⏺ an 8-second loop recorded to video (MediaRecorder; Chrome) and three palettes.
- 🚪 Open gates v2 (`TrenchOpen`): ONE plain table — # · $COIN (tap = coin drawer) · age · traded / h · 5 min · safety in a WORD
  (✅ safe · ⚠ failed · ❔ unscanned, the reason in the tip) · one button: **Pick** inside the swap picker (`onPick` ←
  `TrenchScan onPickRow` ← `SwapPicker`: the row goes through the normal `onPick(pickRow(..))` → warn + acknowledge path), else
  View. Callouts read as sentences ("🔥 $SYM · volume leader · called 5m ago · +4% since the call"). The first version was tiles
  whose `flex: 1 1 0` ticker collapsed to nothing (rows read "1 ▢ $159K/h") and a row tap only opened the drawer — the owner
  could not pick from it. A FLEX CHILD THAT MUST SHOW TEXT NEEDS A REAL MIN WIDTH: use grid columns for rows of data.
- 🎬 Covers & logos studio (`frontend/public/cover.html`, served at `/cover.html`, standalone; encoder self-hosted at
  `/assets/gifenc.esm.js`, copied from node_modules — no CDN): four 1500 × 500 covers (FEELESS · FEECAT · FEE RESERVE · FUSE,
  each its own palette, mark and motion) and two 512 × 512 logos (Fuse spinning coin: atom face / DNA back; the 3D clan F:
  extruded block F turning on a hex shield with wings, stars, a chrome sweep and a DNA helix passing behind AND in front).
  Every piece downloads on its own: ⬇ PNG · ⬇ GIF (covers 750 × 250 × 40 frames, logos 512 × 512 × 48) · covers also ⏺ an 8s
  video loop. New piece ⇒ one entry in `COVERS` / `LOGOS` with a `draw(g, t)` that loops cleanly at t = 0 → 1.
- 🎬 Covers & logos v2 = DARK STUDIO (owner: "dark and realistic, all live — not that"; reference = the slanted chrome glyph they
  sent). `cover.html`: `studio` (near-black room, slow out-of-focus lights, bokeh) + `grainVignette` + `onFloor` (the subject and
  its reflection on a wet floor) + `metal(g, polys, t, [deep, mid, hot])` = a brushed-metal 3D glyph (extruded walls that swing
  with the light, iridescent face whose hot tip breathes, noise grain, a light bar sweeping across, rim line) + `dnaBeads`
  (13 chrome beads, behind then in front) + `metalCat` (the cat mark as lit metal; its black falls away). Glyph polys: `RESERVE`
  (the reference mark, rebuilt as vectors — the sent picture has its pastel background baked in) and `FUSE_F` (the same language
  as an F). Pieces: 4 covers (FEELESS · FEECAT · FEE RESERVE · FUSE) + 5 squares (Fee Reserve pfp · Fuse chrome F with DNA ·
  FEELESS clan F with DNA · FeeCat pfp · Fuse spinning F), each PNG / GIF (+ video for covers). No cartoon rays, grids or emoji.
  The Fee Reserve PAGE (`/terminal/alpha`) has no picture of its own, and it renders a stray "Off the radar." block under the
  rooms — not fixed here.
- 🎬 Covers & logos v3 (`cover.html`): 🎨 COLOUR picker on top — Auto (each piece its own) · Chrome · Royal · Fusion · Gold · Ice ·
  Blaze · Toxic · Blood · Steel (`PALS[key] = [name, [deep, mid, hot], [3 light rgb], accent]`, `pal(default)`); one tap repaints
  EVERY piece and the download is what is on screen (the colour is in the file name). The owner's C picture was a STYLE
  reference only: Fee Reserve's mark is a slanted R (`RESERVE_R`); FEELESS and Fuse use the slanted F with DNA. Crazier: `beams`
  (light shafts from the floor), `shock` (rings rolling out over the floor), `bolts` (lightning crawling around the mark, new
  shape 24× a loop from the seed table) and `flecks` (sparks thrown off the hot edge) on every piece. New colour ⇒ one `PALS` row.
- 🎬 Covers & logos v4 (`cover.html`): a DESIGN picker next to the colours — Slab (clean bars) · Blade (old sniping-clan
  monogram: pointed cut ends `BLADE_F` / `BLADE_R`, a slash through the letter via `metal(.., slash)`, three steel blade wings a
  side) · Crest (steel shield plate `PLATE`, the cut letter on it, a name ribbon, three stars). `glyphArt(g, t, P, 'F' | 'R', k,
  dna)` draws the chosen design for every F / R piece; the design + colour are in the download's file name. The clan references
  (L7, SpaceBound, eRa) were worked from memory of the genre, not looked up — no logo of theirs is copied.
- 📈 Stock charts DO move: candles are live (NVDAx / SPYx tick every minute) but a stock token moves ~0.05% a candle and some
  (QQQx, CRCLx) print no trade for minutes outside US market hours — on a market-cap chart that reads as frozen. Not a bug; a
  "US market closed" note on stock charts is NOT built.
- 🎖 CLAN LOGOS (top section of `cover.html`; owner's real references: L7's interlocking glossy green bars on a light studio,
  SB's fat rounded blue strokes with a silver bevel + slits, the folded-paper white b with ONE blue strip on carbon — and
  "horrible lol" for the busy studio pieces): ONE bold monogram and nothing else. `GLY` = letter centre-lines on a unit grid
  (F, Z, L, R; `R_SQ` = the square-bowl R for straight bars), `clanMark` draws them three ways — Interlock (each bar laid over
  the last with a dark seam) · Round (silver bevel, colour stroke, speed slits) · Fold (white / grey facets, one colour facet)
  — italic via one skew transform, an 8px side wall from the same shape darkened, a glass half + a sweeping highlight
  (`source-atop`), a soft drop shadow, on Light studio or Dark carbon. Pieces: Fuse FZ · Fuse F · Fee Reserve FR · Fee Reserve R
  · FEELESS FL; the colour row recolours them. LESSON: when the owner names a reference, ask for or look at the actual image
  before drawing — the lightning / beads / crest versions were built from a guess and thrown away.
- 📊 EVERY chart opens on MARKET CAP: the coin drawer's chart was the last one on price (`CoinDrawer` now passes `marketCap` from
  the shared live-price record's `mc` and `metric="marketCap"` when it is known, price only when it is not). War room, mini
  chart and mini card already did.
- 🎖 Clan logos v2 (`cover.html` `MARKS`): FOUR bespoke design ideas per brand, all on screen side by side (no style picker) —
  1 Interlock (hard-slanted planes with a dark seam, an extra floating plane on the F) · 2 Fused (rounded strokes that SHARE a
  stroke: Fuse = FZ on one top bar, Fee Reserve = the F's bars closing into the R's bowl; silver bevel + slits) · 3 Frame (the
  letter cut out of a chamfered plate with `destination-out`, four folded facets, one colour strip) · 4 Stencil (a slanted hex
  emblem with the letter knocked through). `clan(design, 'F' | 'R', palette)`; backdrop Light studio / Dark carbon; the colour
  row recolours them. The typed-letter version (`GLY`, style picker) is gone.
- 🎖 `cover.html` v5 = REAL 3D, everything before it cleared (owner: "they don't reference the images — clear all this"). The 2011
  sniping-clan marks were Cinema-4D renders, so the page renders true geometry: three.js (self-hosted in
  `public/assets/three/`: three.module.js + three.core.js + RoomEnvironment.js, via an import map — no CDN), ONE WebGLRenderer
  whose viewport is drawn into each piece's 2D canvas (so PNG / GIF / video keep working), `ExtrudeGeometry` with a bevel,
  glossy clearcoat plastic, a key light with a soft shadow on a `ShadowMaterial` floor, studio backdrop textures. Three
  constructions = one per reference: **Planes** (L7: separate hard-slanted slabs at different heights so they really overlap,
  green, tilted, light grey studio) · **Pills** (SB: fused rounded strokes, colour face + white bevel and sides, white slits,
  icy white studio; Fuse = FZ on one top bar) · **Frame** (the folded b: white chamfered letter around a square hole, one
  colour strip, dark carbon). 6 profile pictures + 6 covers (the mark left, the name in clean italic caps right), each slowly
  turning, each PNG / GIF / video; colour row (Auto = the reference's own colour). Tone: ACES exposure 0.92, env intensity
  ~0.4 — brighter washes the colours to pastel. WHEN A REFERENCE IS A 3D RENDER, RENDER 3D: four rounds of 2D canvas drawings
  were all rejected.
- 🎖 `cover.html` v6: FIVE constructions, one per logo on the owner's second reference set (`BUILD` ring · chrome · blades · outline ·
  gear; `LET` = one block letter per brand reused by all, `letter` / `annulus` / `strokes`, `metal(c, rough, brushed)` + `glow`),
  a BRAND switch (Fuse / Fee Reserve, `brand`, studios cached per brand) → 5 profile pictures + 5 covers on screen; backdrops
  `ghost` (white wall of faint letters) + `matrix` (code). Emissive above ~0.25 washes to pastel under ACES. Planes / Pills / Frame are gone.
- 🔎 HQ SEARCH (`lib/hqJump.js` `HQ_JUMPS` + `jumpSearch`, `components/command/HqJump.jsx`, `hqj-*` in hqNav.css; on top of the HQ nav,
  "/" focuses it, ↑↓ Enter, Esc): type "profiles" / "rpc" / "payouts" → the tab opens and (Fuse) the deck panel via
  `feeless:fuse-deck-go`; Money views via `openTab`. A scoped role only finds places inside its own tabs. 🪪 Wallet profiles is its
  OWN Fuse deck panel (`profiles`, MONEY) — it sat at the bottom of 👛 Fuse wallet. New HQ panel ⇒ add a row to `HQ_JUMPS`.
- 🪪 Circle wallet profile editor REALLY saves now (`circle_profile_view/merge`, `CIRCLE_PROFILE_KEYS`): it posted name / avatar /
  banner, the profile stores displayName / avatarUrl / bannerUrl, so only bio + @handle ever stuck. The form has ⬆ upload for
  picture + cover (`uploadImage`, GIFs stay animated). `upload_cap(mime, role)`: user 2 MB / 6 MB GIF · HQ admin 25 MB · the
  CREATOR's GIFs up to `OWNER_GIF_CAP` 250 MB (a memory guard, not a product limit). A signed-in upload is judged by the server only.
- ✏️ Edit a Circle wallet's profile FROM ITS PROFILE PAGE (`components/CircleProfileEdit.jsx`: `CircleProfileForm` shared with HQ's
  🪪 Wallet profiles, `CircleProfileEditButton` beside 🔎 Case file for an admin wallet viewing someone else's page → pop-up form).
  The owner clicked "Profile ↗" in HQ and found no way to edit there. The server still decides (owner + own Circle wallet only).
- 👤 YOU vs 🤖 ENGINE (`fuse_wallet.versus` → `realBook.versus` → `Versus` under the real card, `hrt-vs`): the last 24h of exits split by
  who OPENED the position (buy `picked` = the owner's hand pick; a top-up keeps its side), confirmed fills only, price result. A
  leader is named only with ≥ 5 exits a side and ≥ 0.5 pts apart. 2026-10-07: 24h you −1.33% on $154 sold · engine −1.99% on $49;
  6h you −2.92% · engine −1.23% — both negative, 135 hand picks a day.
- 📉 "WE MISSED THE DIP" WAS TESTED AND IS NOT THE FIX (105 real buys with 1-min candles, 24h): a resting bid 3–12% under the signal
  filled only on coins that KEPT falling (median −6…−14% an hour later vs −3% at market); dip-then-reclaim (fall 5–20%, back up
  3–8%) was no better (−3…−25%). The buys that never dipped were the winners. Do not build a wait-for-dip entry on this record.
- 🪶 GIFs are slimmed on upload (`lib/slimGif.js` `gifPlan` + `slimGif`, ImageDecoder + gifenc, in `uploadImage`): fitted to the box
  they show in (`CROP.avatar.gif` 256², `CROP.banner.gif` 1200 × 400), ≤ 12 fps, ≤ 72 frames; untouched when already light or the
  browser has no ImageDecoder. Profile cover = always the whole 3 : 1 picture (tips.css; the height used to follow the WINDOW width
  and cropped it). Profile lag was NOT the GIFs (1.6 MB, 4.5 fps): `feed-flare` animated `left`, `feed-shine` / `tr-shimmer`
  animated `background-position` — now transform / opacity (tips.css). Count non-cheap animations before blaming an image.
- 👤 PICKS LIKE THE OWNER (`backend/pick_style.py` pure + tested: `snap/note/profile/match/rank/words`; `data/pick_style.json`;
  `_pick_style_note` after every queued hand pick / fill-seat; `_human_style`; `prime.humanTiers`, default `['next']`; admin prime
  `{human: {tpl, on}}`; `/fuses/prime.humanStyle`; button `prime-human-<tpl>` in HQ › Fuse › Arena › Cards, chip `prime-human`):
  a PAPER tier card switched to it orders its runner candidates by how close they sit to the owner's own picks (age, pool, cap,
  1h volume, 1h / 5m move, buyers: the middle 80% of the last 120 picks; needs 8) and skips the edge gate. It copies HOW the owner
  picks, never their trades; never real money; "not every card" — one by default. Its own record says whether the habit wins.
- 🎞 cover.html GIFs = a 4s loop at 15 fps (60 frames; covers 1200 × 400): the 8s / 36-frame export played at 4.5 fps and read as
  lag on the profile. `slimGif` caps at 20 fps / 96 frames so it never re-chops a smooth GIF. "LAG" ON AN IMAGE ⇒ check its fps first.
- 🌙 OWNER'S NIGHT RULES (2026-10-07, all on the real card): (1) 🪑 EVERY empty seat is filled on the SAME tick (the engine seated
  one a tick). (2) ⏳ `STUCK_BUY_SEC` 30: a seat whose buy has not gone out in 30s is re-picked (another coin, or cash) — but the
  clock does NOT run while the keeper is `busy` with another order for the card (one in flight, or a sale in the last 45s): a swap
  is sell-then-buy a tick apart and would re-pick its coin for good. (3) 🔁 NO SAME COIN AGAIN (cfg `rebuyDipPct` 0/10/15/20, Edit
  Fuse › Coins; card `rebuyDip`; `dip_ready`, `cool_track` keeps each stamp's `low`): a coin that left the card in the last day
  comes back only after it dipped that far under its exit price AND is ≥ 3% off its low — running or not; owner picks never
  limited. Set to 15 on the real card. (4) 🗑 TRENCH DROP every 30 min (`TRENCH_DROP_SEC`): a card on the trench cycle takes the
  best coin of the WHOLE trench list — owner-filter passes, engine-scan passes, then coins missing only a crowd / age / size line
  (`soft_only`) — no trench setting decides; SAFETY always; `trench_entry` = not falling, 5 min ≤ +3%, buyers ≥ 55%. ONE drop per 30 min: it
  takes the seat of the WEAKEST runner-seat coin making ≤ `TRENCH_VICTIM_USD` $0.10 (never riding / frozen / picked / just
  bought); no such coin → it waits in the queue, retried every tick, and the 30 min run from the swap. `trenchAuto` back ON for the real card.
  The earlier evidence still stands: coins this young lost on the replay — the small ticket + its own stop is the protection.
- 🧾 2026-10-07 night autopsy ($4.63 → $2.31): ONE hand pick ($TRALA, minutes old, $1.50 of the card incl. a $0.30 idle-cash
  top-up 48s after the buy) was pulled 90 seconds later → the −40% floor sold everything at 02:15. Fixes: (1) 🎟 `young_ticket`
  (`YOUNG_PICK_H` 12, `YOUNG_PICK_PCT` 15, `YOUNG_PICK_SL` 25; picks carry `ageH`): a hand pick under 12h old goes in as ≤ 15% of
  the card with its own −25% stop, the rest back to card cash — sized, never blocked. (2) leg `ticket` (young pick, trench drop)
  and `scout` are `locked` for the keeper's idle sweep and skipped by `spread_cash` / `balance_small`: a small ticket is never
  topped up to a full seat. (3) `meta_only(rows, cfg, mom)`: 🗑 trench rows use `trench_entry` instead of the chart gate (a coin
  minutes old has no chart, so EVERY trench row was dropped and the 30-min trench drop never fired once all night); a coin
  passing the card's hunt line may sit at its highs (spike / wild / down-trend still apply). (4) Real card selection set to the
  🚀 Runner hunt line by the owner's delegation ("fix to have better chance"): age ≥ 12h · pool ≥ $25K · 1h volume ≥ $50K ·
  1h ≥ +40% · record gate off; the owner's exits unchanged; trench stays open for new coins as tickets
  (`data/realcfg_before_hunt.json`). Walk-forward that day: hunt +3.7% typical per 6h window on 15m, 7 of 9 windows up — thin.
- 🪑 30-SECOND SEAT FALLBACK (`SEAT_FALLBACK_SEC`, `seat_fallback_ok`, cfg `seatFallback` built per tick for the real card, card
  `seatEmptyAt`): an empty or reserved seat with no coin clearing the card's FULL line takes the next-best WATCHED coin after 30s
  (passed safety, pool floor, weather, min age, record gate; fails only at-its-highs / chart too short / the hunt line) — never
  one falling, mid-spike, trending down, too wild, cooling or on the card. Owner: "fill seats should be 30 secs, not the round".
  It trades selectivity for filled seats: when results are judged, split exits by the event text "after 30s".
- 🌊 FEED WIDENED AGAIN (2026-10-07, "list looking the same"; before: trending 125 coins, new 40, runner board saw 71): `JUP_LISTS`
  = 9 live rankings (+ most traded 5m / 6h / 24h, organic score 1h, trending 24h) + `JUP_RECENT` (Jupiter's newest launches on every
  launchpad, both boards); Pump last-traded pages to offset 250, newest to 150; `BOARD_MAX` 660. Measure with
  `/api/market/feed?chain=solana&kind=trending&scope=launchpads&page=N` pair counts before and after any feed change.
  THE SOURCES WERE NOT THE CHOKE: nine rankings moved the feed 125 → 129. `build_board` listed a trending launch coin only with
  cap ≥ $25K · ≥ $15K/h · ≥ 60 trades/h; now `TREND_MIN_MC` $15K · `TREND_MIN_VOL1H` $5K · `TREND_MIN_TX1H` 30. Display only — the
  runner gates and the real-money lines are unchanged. "SAME LIST" ⇒ count candidates in vs pairs out of `build_board` first.
- 🚪 Open gates v3 (`TrenchOpen`, `top-*`): one coin a row with everything on it — logo · $COIN (age + cap under it) · pool · traded/h
  · 5 min · 1 hour · buyers · safety word · Pick / View — and a second line saying WHY (`whyLine`: top-10 / dev / insiders / bundled
  for a scanned coin via `open_board` facts, else what failed / never scanned). Filter seg (All · ✅ Safe · ❔ Unscanned · ⚠ Failed,
  with counts) + sort seg (Busiest · Newest · 5 min · 1 hour); "Show all" scrolls inside 560px. NEVER `.m-num` in a dense row (22px:
  "$658K" overlapped the safety column) — use `top-n`. `OPEN_MAX` 200; picker shows 25 rows first. Pump live lens = 300 rows,
  Movers 150, both read 6 feed pages (owner: "more than 80 — flood with coins").
- 🧪 EVERY PAPER CARD = ITS OWN EXPERIMENT (`arena_prime.DEFAULT_TIER_PICK` merged in `tier_cfg`, `PICK_STYLES`, card view `pickStyle`,
  shown in the league-table lane): 💎 safe = 🚀 runner hunt (12h+, $50K/h, +40%) · 🥇 balanced = 🎯 sniper (record gate floor 3, $50K
  pool, buyers 65%) · ⚡ next = 👤 picks like the owner · ♾ ever = majors · degen = engine order. UNIQUE COINS (`unique_rows`,
  `shared_leg`, in `_prime_tick` for paper only): a paper card is never offered a coin another card holds (anchors too while another
  major is free; SOL exempt) and a coin it already shares is swapped for its own, one a tick (event "🧪 unique coins"). The exits were
  already per card; the SELECTION was the same picker five times, so five cards proved nothing about what to buy.
- 🟢 BUY BOTTOM (the owner's term; example $LOOT: 55% under its high, bottom of its range, flat): `arena_prime.buy_bottom` (≥ 30%
  under its high — the chart's 4h high when read, else the 6h / 24h change · bottom third of its range · 5 min ≥ −1%, 1h ≥ −10% ·
  buyers ≥ 50% · ≥ $10K/h) → `_bottom_rows` (launch feed, 60s cache, ≤ 120) → `/fuses/discover?lens=bottom` → picker lens
  `🟢 Buy bottom` (second tab; each row's label says why). Own 1-hour paper record (`_bottom_track` in `_trench_build`,
  `data/bottom_proof.json`, shown in the lens note). A LIST for hand picks, never an engine buy: on the pick record the bottom
  third of a range lost 31% typically — let its own record decide before the engine may use it.
- 🏠 TAKE THE INITIAL, LEAVE THE PROFIT (`arena_prime._take_stake/stake_leg`, leg `house`; admin prime `{skim: {.., stake: true}}`;
  per-coin 💰 option "🏠 take my initial, leave the profit"; cfg `trenchHouseAt` 0/30/50/100/200 in Edit Fuse › Coins = automatic,
  once, for trench / ticket coins — money follows `skimTo`). A `house` coin is never topped up (spread, balance, keeper sweep).
  On a REAL card the book's cost basis falls in proportion to the sale (not to 0): the flag says "initial out", the ledger stays true.
- 🔄 WAR-ROOM REBUY: the server side always worked (sold + bought back in 15s on 2026-10-07) — the chart kept the levels it was
  OPENED with, so the old entry / stop / lock stayed on screen and it looked dead; and the button only fired while My cards was
  mounted underneath. Now `lib/liveFuse.js` (`fuseLevels` lives here, `liveFuseFrom`, `useLiveFuse`: card read every 10s, 3s after a
  kick; card view `rebuying`) feeds the strip AND the chart lines; `TrenchChart` asks + posts the rebuy itself (any page) and shows
  selling → buying back → "new entry $x". A chart opened from a card must READ THE CARD, never keep a snapshot.
- 🎯 Swap picker = 7 lists (`PICK_LENSES`): 🚀 Movers · 🟢 Dips & bottoms (buy-bottom rows + the Gauntlet's dip buys, one tab) ·
  🆕 New launches (feed, newest first ≤ 48h) · 🌊 Volume (feed, busiest first) · 🗑 Trench · 🪙 Majors & stocks (majors + stocks +
  new majors, `LENS_URLS`) · 🏁 All ranked. Up to 300 rows each. EVERY row has a line: recorded prices (sparks, 3 batches of 60)
  else `moveLine` from its own 24h / 6h / 1h / 5m moves.
- 🧷 A KEEPER SAVE NEVER ERASES A TOP-UP (`fuse_wallet.owner_add` journals every top-up on the book as `ownerAdds`; `merge_owner`
  inside `_fw_keep` applies any entry the keeper's copy has not seen — every keeper save goes through `_fw_keep`). 2026-10-07: a $2
  top-up landed 20s into a keeper swap pass; the pass saved its older book over it → the book never got the SOL (it sat UNASSIGNED
  in the wallet), the card started a run that counted it, read −54% and the floor sold everything. "WHERE DID MY TOP-UP GO" ⇒
  compare `fundedUsd` in the book with the ledger's top-up rows and read `reconciliation.outsideCardUsd` before anything else.
  Same race still open for ↗ withdraw-cash / ✂ manual cash (owner writes during a keeper pass) — journal them the same way next.
- 🏔 2026-10-07 "next up giving stuff that peaked": the 30s seat fallback waived "at its highs" and filled seats with coins that had
  already run ($POD '🏔 at its highs', $Frank, $USOR). Now `seat_fallback_ok` refuses a coin at its highs; the fallback list is
  pullback coins, then 🟢 BUY-BOTTOM coins that passed safety + pool floor + min age (`bottomWhy`); Coming up shows dips first and
  peaked coins LAST, tagged "already ran". `MAJOR_MIN_VOL_MCAP` 3% (a $19.7M "cap" trading 1.1% a day is painted, not a major).
  `_open_board`: a scan with no top-10 reading is NOT a scan (it showed "top-10 hold 0% · safe"). The pipeline that day:
  72 safe → 22 old enough → 2 after the chart rule → 0 free: the +40% hunt line and the "not mid-spike / not at its highs" rule
  pull opposite ways, so the engine's own line almost never has a coin and seats are filled by fallback / trench / hand picks.
- 📈 MAJORS + STOCKS ARE ALWAYS RECORDED (`candles_service._always_hot`, `always_pairs`, `_refresh_always` every 10 min from the
  majors + stocks lists): a tick a minute while nobody watches (`ALWAYS_GAP` 55s, last `ALWAYS_KEEP` 3000 kept), every 15s while a
  chart is open. Before, live ticks started only at the click, so a cold major / stock chart showed flat minutes (the history
  provider prints a candle only when a trade lands): MEW 24 of 30 minutes flat, QQQx 21. The owner runs 5-minute rounds ON PURPOSE
  (a locked coin is held past the round) — do not recommend a slower clock again.
- 🧷 `tpStakeUsd` = ALWAYS KEEP $X RIDING (replaces "auto profit keeps the stake"): `tp_room(l, cfg, px)` = the $ of VALUE above
  the floor; skim, bank at the lock, peak sell, recycle and the full-stack skim (`keep = max(stackSkimUsd, tpStakeUsd)`) never leave
  a coin worth less than it; a coin under the floor is not skimmed at all. The old meaning was "$ of STAKE the takes may remove",
  so with "$1" set a riding +122% coin ($JIPPI) went from $1.13 to $0.14 in five takes — the owner: "supposed to stop at $1 I
  set, not sell out". The full-stack skim also cut two hand-frozen coins to $0.50 of value (top-up money included). A SETTING MUST
  DO WHAT ITS NUMBER SAYS ON SCREEN — when the owner reads it differently from the code, the code is wrong.
- 🅿 A NEW PICK TAKES ONLY ITS SEAT FROM THE PARK: with a seat pick queued, parked profit is released only as far as that seat
  needs (an equal share beside the coins held, oldest park rows first, a row is split); the rest stays parked with its rounds. It
  used to release the WHOLE park (a $4 six-round park ended on one pick). 🧱 Safety has OFF switches (Edit Fuse › Safety, real
  card): card floor `floorPct` 0 = off (guarded in the tick), 🎟 `youngTicket` on / off (card `ticketOff`), ✅ check my picks,
  🧷 always keep riding (no limit), 🔁 same coin again (any time), rescue (off), auto-tune. The real card's split line is
  `cardSplit`: coins (the legs) · ◎ free cash · 🅿 parked — it used to print value − parked as "coins", so $2.77 of free cash read as coins.
- 🅿 PARKED MEANS PARKED (owner: "parked 6 rnds means just that" — this REPLACES both pick-release rules): nothing releases a
  park before its rounds are up; a pick with no free cash is funded by trimming coins above an equal share, or waits. Split line
  = "in coins · ◎ cash for a seat · 🅿 parked". "PROFIT PULLED" (`takenUsd`, the engine's running tally: $66.81 on a card down $7 —
  one path adds whole proceeds, and recycled money is counted every time) is gone from the real card: `fuse_wallet.realized_split`
  → `realBook.realized` → "SOLD SO FAR" = net of confirmed sales, winners / losers in the tip. 2026-10-07 chain audit (1,172 swaps,
  0 unread): every booked coin is in the wallet; the rebuilt card cash is 0.0248 SOL above the book = the two top-ups the keeper
  race erased ($2 today 12:09, $1 on 10-06 evening: ledger top-ups $17, book put-in $14). That SOL is in the wallet (unassigned +
  rent parked in coin accounts). NEVER credit it to the card without the owner pressing Top up.
- ↘ LOST TOP-UPS COME BACK (owner: "assign what's supposed to be in card and what's supposed to be in wallet FIRST";
  `fuse_wallet.lost_topups` = ledger put-in − book `fundedUsd`, matched to the newest un-journalled top-up rows; book
  `owedInSol` / `owedInUsd`; `settle_owed_in` credits from the wallet's FREE SOL only (never the fee reserve), the rest as SOL
  frees up; once per book `lostTopFix`; ledger `fix` rows `losttop:` / `owedin:`; the card's run baseline rises by the same $).
  The mirror of `owedOutSol`. 2026-10-07: $3.00 (0.02556 SOL) — the 12:09 $2 and the 10-06 21:44 $1.
- 🧾 OWNER MOVES ARE RECORDED AND SCORED (`backend/owner_moves.py` pure + tested; `_owner_moves_tick` every ~2 min in
  `_trench_build`; `data/owner_moves.json`): picks, hand swaps, rebuys, profit takes, initial-out, ✂ cuts are read from the real
  card's own events (`classify`), noted with the coin's price, judged 30 min later (brought in → up 10% = good; sold → down 10% =
  good; no price after 2h = −100%). `/fuses/prime.humanStyle.moves` (`movesLine` in the 👤 tip). The 👤 paper card now also EXITS
  with the owner's own stop / lock / trail / hold (`TIER_KEYS` from the real cfg). 💬 Fuse room calls (`owner_moves.calls`,
  `_fuse_chat` once per key, ≤ 4 a pass): ❄ a lock as it happens · ✅ a good call / good exit with the coin's % since · 📣 a
  callout up ≥ `CALL_RUN_PCT` 25%. Coin moves in % only, never the card's $ result.
- 🧷 PERMANENT: OWNER MONEY WRITES NEVER INTERLEAVE WITH A KEEPER PASS — the ten owner routes that write a wallet book (top-up,
  withdraw cash, pay out profit, reinvest, config, recover sells, retry, card, 🔧 fix) take `_fw_tick_lock` THEN `_fw_lock`, so they
  wait for a swap pass in flight instead of being saved over by it (the journal + `merge_owner` stay as the second net). Never take
  `_fw_tick_lock` while holding `_admin_lock` (the keeper pass takes `_admin_lock` inside it). 🅿 a per-coin park carries its own
  rounds (`skim.rounds` → park row `hold`; `release_parked` reads it). `.hrt-split` wraps (it was cut off with …).
- 🔢 EVERY NUMBER BOX = `components/NumInput.jsx` (`commaNum` / `stripNum`): commas while typing (1,250,000.5; placeholders too), plain
  digits handed to `onChange` / `onBlur` (callers keep `Number(e.target.value)`), a half-typed decimal survives a parent that stores a
  number, ↑ / ↓ step when it replaced `type="number"`. 100 inputs moved in one pass — never add a bare `<input type="number">` or
  `inputMode="decimal"` again (`FeeInputs.UnitInput` is the older whole-number one). Real card split = its OWN row of chips under the
  hero (`p.hrt-split`: in coins · ◎ cash · 🅿 parked cash, all three always shown): inside the 83px IN CARD NOW tile `.hrt-hero em`
  (nowrap + ellipsis) out-ranked the "wrap" fix and it still read "in coins…". Hero tiles go 2 × 2 under 1180px and their small lines
  wrap. A CSS FIX IS NOT DONE UNTIL THE ELEMENT'S scrollWidth ≤ clientWidth ON THE LIVE PAGE.
- ↘ LOST TOP-UP PAYBACK COUNTS PARKED RENT AS RESERVE (`fuse_wallet.free_for_owed`, `OWED_LIQUID_MIN` 0.00304 SOL; used by the
  owed-in settle with `_fw_rent_parked.sol`): rent parked in the wallet's coin accounts is the fee reserve's money (it returns on
  every close sweep), so it counts toward the 0.015 reserve; liquid SOL never goes under one new coin account + fees. Found
  2026-10-07: $1.17 of the owner's lost top-ups sat "still to come" for hours — the reserve was busy fronting 0.0106 SOL of rent,
  so `free_sol` read 0 and the card was never paid back.
- 🔥 PUMP'S OWN TRENDING TAB IS A SOURCE (`launchpad_board.PUMP_TREND_PATH/PARAMS/TTL` 600s, `pump_trend_rows`; market base `PumpBoard`
  = `https://advanced-indexer.pump.fun` `/boards/trending?tier=web&surface=TRENDING&platform=WEB&limit=150&chains=solana`, found by
  reading pump.fun's own JS — it is NOT on frontend-api-v3, which has no trending sort): refreshed every 10 min, its coins go FIRST
  into the launch feed (never cut by `BOARD_MAX`), listed on the trending board even under the board's floors (`pumpTrend` rank on
  the pair), and the swap picker opens on 🔥 Pump trending (`lens=ptrend`, Pump's order, "🔥 Pump #N"). Owner, 2026-10-07: had to
  open pump.fun to find LOOP and FLY. The engine's gates and real-money rules are unchanged. Each row also carries holders (`nh`),
  top-10 % (`t10`), dev share (`dh`), dev wallet (`dw`), socials — not used yet.
- 🔁 SLIPPAGE = RETRY NOW (`fuse_wallet.chain_err/buy_escalation/slip_transient/slip_busy`, `SLIP_RETRIES` 2, `SLIP_FREE` 3, end of
  `_fw_execute`): 2026-10-07 EVERY on-chain failure was Jupiter 6001 / 0x1771 (price ran past the limit) — and one such failure
  counted as a refused buy, so 15s later the seat was handed to another coin (the owner's $FLY / $LOOP picks bounced). Now the
  ledger says "slippage exceeded on-chain", the SAME order goes again at once (fresh quote, buys +1.5% → ≤ 5%, sells as before ≤ 8%,
  every live-pool / limit / secure-buy check again, id `…:rN`), the first 2 slippage failures in 15 min are NOT misses, and the
  stuck-buy clock waits 45s (`book.slipAt`). The 3rd counts → bench as before. Safety refusals (price gap, sell-back, thin pool)
  are unchanged. "STUCK BUY / SELL" ⇒ fetch the failed sig's `meta.err` first: 6001 = slippage, anything else is a different bug.
- 📏 EVERY PICKER LIST HAS ITS OWN RECORD (`_lens_track` in `_trench_build` → `data/lens_proof.json`, top `LENS_TOP` 15 of 🔥 Pump trending ·
  🚀 Movers · 🆕 New launches · 🌊 Volume, each noted once and judged 1h later, no price = −100%; `trench.list_records` + public
  `GET /fuses/list-proof`; `SwapPicker` shows the typical % on every tab (`sp-lp-*`) + one line for the open list (`listRecord`)). A list
  without 5 settled coins borrows the nearest callout record and SAYS so (`src`). 2026-10-07 records (1h): 🔥 volume leaders −1% (48% up) ·
  🟢 bottoms −6% · sweep / pullback −13…−14% · trench baby −70% · fresh launches −63% · 5-min movers −75%. Real card that day: hand picks
  sold whole inside 15 min −$8.74 on $97 (90 exits); engine coins ≈ −$1.45; trims of winners +$3.87.
- ♻ RENT SWEEP RUNS EARLY (`fuse_wallet.sweep_due`, `SWEEP_SOON_SEC` 60): when the wallet's SOL outside the cards can't open 2 new coin
  accounts and a coin was sold whole since the last sweep, the empty accounts are closed within a minute (the clock was 10–30 min). On
  5-min rounds the reserve was all parked (7 accounts, 3 empty, 0.0004 SOL free) and the next new coin waited on its rent.
- ⏭ COMING UP = ONE COIN PER CATEGORY (`arena_prime.CATEGORIES/category_picks`, `_lens_rows` cached by `_lens_track`, `_list_records`;
  in `_prime_tick` → cfg `catPicks` / `catMiss`, pipeline `catMiss`): 🔥 Pump trending · 🌊 Volume · 🟢 Dips & bottoms · 🚀 Movers · 🆕 New
  launches · 🗑 Trench, each list walked from ITS top; the first coin that passed the safety scan, clears the pool floor + min age, is not
  dollar-named and is a sane entry (`seat_fallback_ok`) is that category's pick (tag "🌊 Volume #3"); categories ordered by their own
  1-hour record. They go FIRST in the 30s seat fallback — what Coming up shows is what an empty seat takes. (Before: 0 ready, 6
  "watching" leftovers: ranging / down-trend / too wild / at its highs.)
- ✂ EARLY CUT ("half the stop + fading") never touches the owner's own pick or a coin in its first 15 min (`FRESH_SEC`): $LOOT, a
  buy-bottom pick with a −6% stop, was cut at −3% four minutes after the buy — its "1h down" was read before it was bought. The full
  stop still applies to every coin.
- ⚡ SWAP IN NOW (`arena_prime.now_picks`, pick `swapTo.now`; `pickSwap.now`; `WhenSeg` ⚡ Now | ⏱ At the bell, default Now, on Coming up
  and in the swap picker): a "now" pick is swapped in on the very next tick (`apply_queued(only=now_picks)`, event "🎯 your pick —
  swapped in now") and the route starts that tick at once (`_prime_tick` is locked — never two at a time). Same checks, warn + ack.
- 🔗 ONE REQUEST PER URL (`lib/sharedJson.js` `sharedJson(path, {maxAge, fresh})`, `markFresh` on `feeless:prime`; `src/setupTests.js` resets it
  per test): the Fuse page fetched `/fuses/prime` (98 KB) 4× at once on load (slowest 2.1s) and `/fuses/contenders` twice. `usePrime`,
  `FusePage` real cards, `MiniDeck`, `liveFuse`, `VaultDesigner`, `ArenaContenders`, `TopThree` share it. A new poller of a shared
  endpoint ⇒ `sharedJson`, never a bare fetch.
- 📡 DEXSCREENER PACING (`backend/ds_pace.py`, `install(rpm, slow_rpm)` patches `httpx.AsyncClient.send` for api.dexscreener.com only;
  server.py 150 + 30 slow · reputation_service 110 + 20 slow — together under the ~300/min per IP): requests wait for a slot (≤ 12s)
  instead of bursting, and a 429 pauses the host for its Retry-After (default 15s). 2026-10-07: after restarts 5001 alone sent 100–190
  DexScreener calls a minute (the launch board looked up 660 coins in 22 batches every 20s per board), 34 reputation call sites
  had no pacing, DexScreener answered 429 and the launch feed went EMPTY — every list, Coming up and the seat refill with it.
  Board: batches 45s, `pair_mem` reuses a coin's last good snapshot ≤ 5 min when its batch is refused, `launchpad_board.keep_last_board`
  serves the last good board (stale-marked) instead of an empty / collapsed one. Jupiter ranking lists: 2 min (5m/1h), 5 min (6h/24h),
  recent 1 min — the keeper's quotes share that free tier. "LISTS EMPTY" ⇒ `curl :5001/api/market/feed…` pair count + grep 429 in
  /tmp/feeless-api.log before touching a gate.
- 📡 ALWAYS A FALLBACK (owner: "always fallbacks, like the RPCs"): when DexScreener has no pair for a coin (refused OR its API answering
  empty — 2026-10-07 `pairs: null` even for SOL/USDC from every IP, website fine), Jupiter's token data stands in, in the SAME pair
  shape (`launchpad_board.jup_pair`: graduated pool else the launch curve, price, liquidity, cap, 5m/1h/6h/24h volume + moves + buys /
  sells, holders, socials; `source: 'jupiter'`). Wired into: the launch board (Jupiter rows already fetched first, then
  `/tokens/v2/search` 100 mints a call, 60s), `_fuse_pairs` (also fixed: it asked DexScreener for only the first 30 pairs per chain;
  `_jup_tokens`, `_pair_mint` pair → mint map learned from every answer; legs pass `mint`), and the keeper's FINAL BUY GATE (a fresh
  Jupiter read, never cached; quote checks still decide). Data sources stay DexScreener + our indexes + Jupiter — the banned chart
  source never (its name may not even appear in code: `test_no_geckoterminal`).
- 🔒 IDLE CASH NEVER GOES INTO A LOCKED COIN, NOT EVEN AS A FALLBACK (`arena_prime.tick` compound `targets`): the old "else every coin"
  fallback poured a real card's cash into its ONE frozen coin on paper (the keeper never buys a frozen coin), the engine read $AUTON
  as $6.26 (wallet: $0.49) and the full-stack skim "took" $5.76 that was never in it and PARKED it — 2026-10-07, $5.76 of a $7.41 card
  locked as fake profit while 3 seats sat empty. With every coin locked, cash stays card cash for the seats.
- 📡 FALLBACKS EVERYWHERE THE WAR ROOM READS (DexScreener outage 2026-10-07): `launchpad_board.jup_lookup(http, mint|pool)` (Jupiter search
  finds a coin by mint OR any of its pools; the pair keeps the asked pool) → `/api/market/pair` (coin snapshot), candles `_pair_snapshot`
  (trade tape), `_majors_rows` (🪙 majors + 📈 stocks, never cached empty); `/api/market/feed` on Solana falls back to the live launch
  board when discovery fails ("What's new on Solana" went blank). ⚡ The launch board answers from its last copy (≤ 5 min) and rebuilds
  in the background (`board_refreshing`) — a cold rebuild took 8.7s for whoever came after the 20s mark.
- ⚡ SWAP NOW = A BUTTON (owner): picker rows `⚡ Swap now` (`sp-pick-*`, `now: true`) + `⏱` (`sp-bell-*`, at the bell); seat picker
  `⚡ Fill now`. Coming up: per coin a target select (🪑 empty seat first when the card has one → `fillSeat`, else "for $COIN") +
  `⚡ Swap now` (`up-now-*`) + `⏱` (`up-bell-*`). The WhenSeg toggle is gone.
- 💲 SOL PRICE IS NEVER MADE UP (`_sol_usd_live` → Jupiter price v3 first, DexScreener SOL/USDC second, `fuse_wallet.sol_price_pick`
  last good ≤ 10 min, else 0 = money actions wait). It fell back to a HARD-CODED $150 when DexScreener answered empty (SOL was $116):
  every real buy read "~30% above market" and was refused, card values priced at $150 SOL. A constant price anywhere money is
  computed is a bug.
- 📡 ONE FRESH LIVE-PAIR HELPER FOR EVERY REAL-BUY GATE (`_fw_live_pairs`: DexScreener, then a FRESH Jupiter read keyed by the order's
  pair): `_fw_preflight` (check the buy before selling), `_fw_execute`'s final gate and the one-transaction swap. Two of the three
  read DexScreener only → "live market unavailable or pair/mint mismatch" on every buy during the outage. Test pins all three.
- 📡 THE BROWSER NEVER CALLS DEXSCREENER'S API (`test_no_browser_dexscreener`): search box, price chart, held signals, live tokens and coin
  resolve called it straight from the browser and went blank in its outage. They use `/api/market/pairs/{chain}/{pools}` (live prices, chat coin cards, war room, resolve; Jupiter batched by known mint, else per-pool ≤ 8), `/api/market/search?q=` (DexScreener → Jupiter
  `jup_search_pairs`) and `/api/market/tokens/{chain}/{mints}` (DexScreener /tokens/v1 shape, Jupiter for every mint it can't answer).
  Logos on dd.dexscreener.com and links to dexscreener.com pages are fine.
- 🚦 PUSH GATE IS CODE NOW (`scripts/gate.sh`, `.githooks/pre-push` on `core.hooksPath`): pytest + jest + craco build on real exit codes (+ no "command center" in the bundle) before any push to `main`; red = the push is refused. Run `bash scripts/gate.sh` yourself first. New clone: `git config core.hooksPath .githooks`.
- 🐱 FEECAT CORE LANE SKIPS COINS UNDER 3 DAYS (`coreMinAgeHours` 72; fresh lane window unchanged): her own record 2026-10-08 — thesis-broken/pulled-pool exits were 23 of 60 exits (−0.92 SOL), setups <6h −36% avg, 1–3d −60%, 3d+ +16%. Sizing may only shrink; this makes her trade less.
- 🐱 FEECAT PROOF GATE (`feecat_brain.proof_gate`): no new entries while her record is net red on BOTH 24h (n≥5) and 72h (n≥10); exits keep running, the window rolls off. Never a promise of profit in every time frame.
- 🚫 LOSING LISTS ARE PAUSED (full-size seats only — trench is a small ticket and is never paused: owner did 5x on three Pump coins with $1-2) (`arena_prime.list_paused/LOSING_LIST_N 30/LOSING_LIST_MED -20`, from `/fuses/list-proof`): a list whose own settled 1h record has median ≤ −20% over ≥ 30 coins is not bought by the engine (Coming-up category, scout/mover swap, trench drop); still listed and hand-pickable. 2026-10-08: movers −71%, Pump live −77%, trench −72%; bottoms +1.4% (proven), Pump trending −2.5%, volume −6%.
- 🟢 Dips & bottoms is the FOURTH Coming-up door (own record +1.4% / 52% up, the only proven list); 🎲 'Find my best 3' breeds each budget its OWN random basket (`again` nonce, `avoid` coins already in another basket) — the three cards no longer hold the same WLD/ORCA.
- ❄ REAL CARD FREEZE WAS OFF (found 2026-10-08: `rideAt` 0 → no coin ever locked, so lock bank 50%, full-stack skim, off-its-peak sell and the stepped trail never ran — only plain skims). `_real_ride_fix` (once, `rideFix1`, backup data/realcfg_before_ride.json) sets freeze +15% (trail 8). WHEN THE OWNER SAYS 'a runner should freeze and skim', read `realCfg.rideAt` FIRST.
- ☀ DAY COLOUR (`styles/dayColor.css`, loaded after meta.css): a static mint → sky → lavender → peach wash behind every page (html + body + terminal-app), tinted panels instead of #fff, darker muted ink; selected `m-seg` labels white (were 1.5–3:1), chat avatar initials light on their dark circle (×120 were 1.15:1), chat coin cards light in day. Contrast scan = walk text nodes, composite the backgrounds up the chain, flag < 3.5:1 (clean on Fuse arena / cards / lab / gauntlet, radar, trade, home, profile 2026-10-08). The Browser pane paints a transparent profile page black — trust computed styles, not that screenshot.
- 🩺 EVIDENCE FLOOR (`arena_prime.thin_flow`, `FALLBACK_MIN_BUY` 55 / `FALLBACK_MIN_VOL` $10K; applied to the 30s seat fallback AND every real-card pool / runner the engine picks): 2026-10-08 $Attention+ came in as a ride-end replacement with buyers at exactly 50% and no 1h volume reading, ranging, −13% right after. Unknown numbers aren't judged; majors / stocks / comebacks / trench rows / the owner's picks keep their own rules. WHEN THE OWNER ASKS 'WHY THIS COIN', read the card event right before the buy (here: SI 'ride-end … swapped' → $Attention+) and the leg's `bought` tag first.
- 🔍 SCAN BUDGET WAS THE CHOKE FOR RUNNING COINS (2026-10-08, owner: 'still running to Pump for real volume coins'): 184 of 200 open-board coins — 14 of 18 with ≥ $50K 1h volume and +20% — read 'not scanned yet' and an unscanned coin is never bought. Cause: `INTEL_TTL` 300s meant ~100 coins × 4 calls / 300s = 1.3 calls/s of RE-scans against a 0.5/s scanner budget, so new coins queued forever. Now `INTEL_TTL` 900, `RPC_SCAN_RPS` 1.0 (env still overrides; a spent lane is parked + owner told). CHECK: `/fuses/trench/open` rows with vol1h ≥ 50K & chg1h ≥ 20 → count unscanned.
- 🩺 AN EMPTY HOLDER READING IS NOT 0% (found 2026-10-08 measuring why 184 of 200 feed coins read 'not scanned'): when `getTokenLargestAccounts` came back empty / refused, `token_intel` cached top-10 = 0% (a clean-looking scan) for the whole TTL — Gary / NINJACAT / swordowl sat as 'scanned, top-10 0'. Now top10Pct / poolPct = None (incomplete, retried in 60s). If lists read 'unscanned' again: count intel_cache rows with topHolders empty before touching a gate or a key.
- 📡 SCANNER BURSTS NO LONGER COOL EVERY LANE (`chain_rpc.RPC_BURST_COOLDOWN` 4s for a plain 429, `SCAN_CONCURRENCY` 4 scans in flight): measured 2026-10-08 — lanes 1 (Alchemy) and 2 (Tatum) answer every holder call, lane 3 (Helius) and lane 4 (2nd Alchemy) 429; but ~60 parallel scans tripped each node's burst limit, each 429 cooled it 30s, the whole pool was resting and holder lookups came back empty (→ 184 of 200 feed coins 'not scanned yet'). Probe lanes by posting the 3 scan methods per `RPC_POOL` entry and printing provider + status only.
- 🔁 ONE SCAN PER COIN IN FLIGHT (`_runner_intel` → `_intel_inflight`, `_intel_failed` 45s): every board build (30s) queued ITS OWN scan for each of the 60+ busiest coins behind a 4-slot semaphore and never cancelled them, so duplicates piled up, failed top coins were retried over and over and the coins behind them starved — 'not scanned yet' on running coins. A queued copy now re-checks the cache; a failed coin sits out 45s. Holder-read capacity is ~1 call/s on the one healthy keyed lane (Alchemy; Tatum bursts 429) — more lanes or a paid key is the only way to scan MORE; this stops wasting it.
- 🧬 PICKER ROWS CARRY HOLDER FACTS (`fuses_discover` wraps `_fuses_discover_raw`: `_holder_facts` from the scan CACHE → top10 / dev / insiders / bundledN / snipersN / scanned; top `PICK_SCAN_TOP` 15 unscanned rows get a scan queued; rows under `PICK_DEAD_VOL1H` $3K/h dropped as dead): the picker had NO insider / bundle data on any row (owner: 'insider, bundlers count not working'). RowVitals shows 'N bundled', 'N snipers', '🔍 holders not read yet'. ☀ Day v2: the 120+ legacy `body.theme-day` white panels re-tinted (#eef6f1 / rgba(236,246,240,a)), `--day-surface` translucent so the wash shows, m-* tokens tinted, the war room's near-white sheet = the wash, and NO `fixed` background (a fixed wash repaints the page every scroll frame).
- 🔢 ONE NUMBER STYLE (`lib/num.js`: `tiny` · `price` · `usd` · `pct`): a price with ≥ 4 zeros after the point reads `0.0₆4123`, ≥ 1 gets commas,
  huge moves read `12.4x`. Every display `.toPrecision()` in components was moved to `tiny()` (codemod, 43 spots) — a tiny price used to
  print as `4.12e-7`. Input VALUES (state an input edits) keep plain digits. New price display ⇒ `tiny` / `price`, never `toPrecision`.
- 🧬 LAUNCH FACTS PAGE BACK TO THE LAUNCH (`SIG_PAGES` 8 × 1000 sigs; Pump's own record names the creator for `…pump` mints): a busy coin
  has > 1000 txs and "the oldest of the last 1000" was a random trader read as the CREATOR with 0 bundled / 0 snipers ($giftr, a rug: the
  real creator was its biggest wallet at 4.4%). Launch never reached → bundled / snipers / insiders = None (unknown), never a fake 0; an
  old `historyComplete: False` read is redone once. 🧼 CLEAN SCORE (`backend/coin_clean.py`, 10 checks, unknown = 0 and named) on every
  picker + trench row (`_clean_rows`), chip `🧼 n/10` first in RowVitals. Picker lists, Open gates and the Gauntlet refresh every 20s
  (in place, no blank flash).
- 🧹 DUST CLEANUP (Trade › 🧹 Dust, `DustCleanup.jsx` + `styles/dustCleanup.css` `dc-*`; `backend/dust.py` pure + tested): reads EVERY coin account of the
  CONNECTED wallet (`GET /wallet-dust/solana/{addr}` — both token programs, Jupiter price + logo) → per coin ↩ swap to gas (worth ≥ $0.50: the normal
  /api/trading quote → simulate → sign → execute path, no new money path) · 🔥 burn + close (dust / unpriced: Burn + CloseAccount, rent back) · ♻ close
  (empty). `POST /wallet-dust/solana/close-tx` re-reads every account and only builds for accounts the wallet OWNS; the USER's wallet signs everything in
  ONE approval; a burn needs the "gone for good" box. Cronos: every LI.FI-listed token (balanceOf batch on evm.cronos.org) → ↩ swap to CRO via LI.FI
  (`lifiServerQuote` + `executeLifi`). Activity log per step, rows pulse while sending, fade out when done. The FUSE wallet's own dust is NOT touched by
  this (its keeper burn was refused by the permission system — the owner decides that one).
- 🎵 MINI PLAYER FINDS SONGS (`MusicFind.jsx` + `styles/musicFind.css` `mf-*` in the FeeCat Music tab; `backend/music.py` pure + tested): 🔎 Search =
  YouTube's own public results page (`ytInitialData`, no key; Piped `api.piped.private.coffee` fallback) · 🔥 Top played = Apple Music's most-played
  RSS (US, 1h cache; tap → its first YouTube video plays) · Spotify search ONLY when `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` are set (tracks
  still play through YouTube). ▶ plays now, ＋ queues (max 20). ▶▶ NEXT KEEPS GOING like YouTube: at the end of the queue (repeat-all) — button or the
  song ending — `GET /music/next` adds another song by the same artist that is not queued, ≤ 8 min, never a "MIX"; nothing found → loops.
- ⚡ SWAP CARD v2 (`styles/swapMeta.css`, imported by SwapWorkspace; owner: "not a dead black card"): aurora backdrop (emerald / violet / ice) on a deep
  green→navy base, ONE rotating conic beam on the edge (`.swap-desk::before`, transform only — the old `--swap-angle` custom-property animation repainted
  every frame and is off), glass panels, gradient amount, glowing token pills, gradient flip that spins, sheen on Get quote; `.swap-desk` is an fxPause
  surface. Fee chips are BUTTONS (`td-fee-free` → loads $FEE into the swap · `td-fee-sol` → why that fee · `td-fee-bridge` → Bridge tab). Under 1180px
  `.trade-left` is NOT sticky (it slid over the swap card). 🧹 Dust: Cronos balances read in batches of 10 across 3 public nodes (`CRONOS_RPCS`; one
  68-call batch came back as ONE error object = "0 coins"); Cronos connect = the browser's own EVM wallet switched to Cronos (never the Solana wallet's
  paired side); any address can be LOOKED at without connecting (cleaning still needs that wallet).
- 🌐 DUST · EVERY EVM ECO (`GET /wallet-dust/evm/{addr}`, `dust.lifi_rows/merge_evm/by_chain`): LI.FI's wallet balances on every chain FEELESS signs on
  (ethereum · base · bsc · arbitrum · avalanche · polygon · optimism · zksync · zora · cronos · unichain · worldchain) + our own Cronos read (LI.FI missed
  it), positive balances only. Trade › 🧹 Dust tab `🌐 EVM · every chain` (replaced the Cronos-only tab): rows grouped under a chain header with its $,
  the native coin = "⛽ gas" (never pickable), every token swaps to ITS OWN chain's gas via LI.FI (`fromChain = toChain = r.chainId`, wallet switched first).
- 💵 REAL CARD SPLIT = THE BOOK (`ArenaPrime.cardSplit`): ◎ cash = `realBook.reconciliation.cardCashUsd` (confirmed card SOL, the "Withdraw card cash"
  number) minus parked; coins = `cardEquityUsd` − that cash; the three add up to IN CARD NOW. It was `value − coins − parked`, so every cent of price
  lag between the leg prices and the card value read as cash ($0.20 shown vs $0.17 on the book). Paper cards keep the old split.
- 🧹 DUST = ONE CLICK (`DustCleanup` `cleanAll`, button `dc-clean-all` "🧹 Clean all N coins — one click"): every non-gas coin with its best action;
  burns are confirmed in that same click (one `window.confirm` naming what burns), then it runs. Solana = ONE wallet approval for all swaps + closes;
  swaps quote 4 at a time. EVM tokens still need one wallet prompt each (one tx per token per chain — EVM can't batch-sign).
- 🎰 RIDE OR RUG (owner, 2026-10-08, trenching new narratives: "if it gets rugged oh well, gotta be a good one, and pull"; cfg `ticketRide`, Edit Fuse ›
  Safety under 🎟 Small ticket; `arena_prime.ticket_marks`): a TICKET (young hand pick / trench coin, ≤ 15% of the card) carries NO stop — per-coin stop
  mode 'hold' + `rideOrRug` (the stop pass, `fast_stop` and the instant swap skip it). It rugs (that slice is lost) or runs until 🏠 `trenchHouseAt`
  pulls the initial out. The rug shield (pool collapse) still sells what's left. `_ticket_ride_fix` (once, `rugFix1`) switched the real card on,
  tickets already on it included; old value in data/realcfg_before_ticketride.json. Chip "🎰 ride or rug" on the coin row.
- 🔁 BUY RETRY = 5% (owner, 2026-10-08: "buy retry should open slip to 5% max on retry only"; `fuse_wallet.buy_escalation` / `retry_slip`): a buy's FIRST
  try uses the normal slippage (≤ 3%); ANY retry after a slippage failure — at once at send, or the next order for that coin within 15 min — goes straight
  to 5% (`BUY_SLIP_MAX`), never higher. Sells keep their steps (≤ 8%). The secure-buy checks (≤ 5% over market, sell-back) still run on every try.
- 🎯 TAKE-PROFIT COUNTS FROM THE LAST TAKE (`arena_prime.tick` TP branch, leg `tpPx`): on a real card `sync_card` puts the book's ORIGINAL entry back every
  tick, so a coin at +100% read +100% again seconds after its take and sold half of what was left again and again ($TikTok 2026-10-08: the 🏠 pull took its
  $0.74 initial, then 7 TPs in 8 min → dust). TP now fires only when the price is +TP% above max(entry, `tpPx`); a `house` coin (initial already out) gets NO
  TP — it rides on stops / trail / rug shield. Any per-tick take on a real card must carry its OWN last-take price (`skimPx`, `tpPx`), never trust `entry`.
- 🧪 JUPITER AUDIT = A HOLDER READING FOR EVERY COIN (`backend/jup_audit.py` pure + tested; `_jup_lite` batched through `_jup_tokens`, 3-min cache
  `_jup_facts`): 2026-10-08 only ~19 of 271 listed coins had ever been holder-scanned (one RPC lane answers; a new coin costs ~40 calls) and unscanned =
  never bought, so the lists ran in circles. Now a coin our scan has not reached gets `lite_intel` (top-10 = Jupiter's topHoldersPercentage, dev
  balance, creator = dev; insiders / bundles UNKNOWN = None) on the runner board, picker rows (`scanned: 'jup'`) and Open gates; our full scan still
  runs and replaces it. Live mint / freeze authority = hard out (`authority_bad`). Jupiter's % never feeds the top-10 spike / dev-sold history.
- 👥 CREWS (`jup_audit.crew`, from the dev wallet's launch record devMints / devMigrations): 🔥 popular crew (≥ 3 graduated, ≥ 20%) · ☠ serial
  launcher (≥ 50 launches, < 5% graduated) · 🆕 fresh dev (≤ 3) · ⚪ mixed. A READ, never a block ($TikTok's dev: 1,076 launches, 22 graduated, still +10,000%).
- 🫀 THE VITAL (`CoinVital.jsx` + `styles/coinVital.css` `cvl-*` (NOT `cv-*`: CardVitals already owns `.cv-bar` — a 4px bar with overflow hidden — and clipped the vital bars to dashes), `jup_audit.verdict` → row `vital`; replaces the long RowVitals chip line in Coming
  up + the swap picker): grade ring A–F + score, four bars (🧩 holders · 👤 dev · 👥 crew · 🌱 organic flow = organic share of 1h volume), the 3 facts
  that decide it (bad first: 🐋 top-10 · 📦 bundles · 🕵 insiders · 👤 dev · ☠ crew · 🤖 bots) + one stats line. Not read yet → the old chip line.
- 🔄 NEW TO YOU (picker lens `fresh`, opens first): Pump trending · movers · Pump live · volume · dips · the Arena's ranked coins woven one from each in
  turn, MINUS every coin the real card bought / sold / holds in the last 24h (`from` tag on each row).
- 📡 A LIST'S TOP COINS ARE ALWAYS ON THE RUNNER BOARD (`_runner_live`): the top 60 of every category list (was 8; = what Coming up walks); a coin the launch feed never carried
  gets its pair built from Jupiter's row (`launchpad_board.jup_pair`) — 2026-10-08 Coming up read "43 of Pump trending's top 60 not on the runner board yet".
- 🏃 OWNER MONEY BUTTONS NEVER WAIT FOR THE CHAIN (`_fw_kick_now`): ✂ sells / sell-all / ⇄ hand swaps / recover-sell / retry-dead start the keeper pass in the
  BACKGROUND and answer at once (`_fw_tick_lock` keeps passes one at a time; the card's swap-flow strip shows the steps). They used to await every sell's
  send + confirm before the screen answered (owner: "confirm sell all takes a lot").
- 🫀 Vital v2 (`jup_audit.verdict`): FIVE bars, 🌱 organic flow FIRST, then 📈 growth (holders +% this hour, net buyers / traders, pool drained ≤ −25% =
  🩸 bad flag), holders, dev, crew; `organicPct` on the verdict. Pick lists: `VitalView` sort (🌱 Organic first = default · 🫀 Best vital · 📈 Growing · ≡ List)
  + filter chips (B+ · 10%+ organic · skip serial · hide bots < 5% organic), remembered per browser (`feeless.vitalView`); `applyView` is pure + tested.
- 🎛 COMING UP FILTER = real card cfg `vitalMin` (0/35/50/65) · `organicMin` (0/5/10/20/30) · `noSerial` (`jup_audit.filter_why`, `UpFilter` above Coming
  up, saved as `realCfg`): `_prime_tick` filters r_t + the scout list (pipeline step "your vital filter"), category picks (`_cat_ok` → "your vital filter")
  and the 30s seat fallback. No Jupiter reading = not judged. The owner's own picks are never filtered.
- 🗑 TRENCH VITAL (`jup_audit.trench_verdict` → row `tv` on any row that is trench / on the curve / < 6h old; `TrenchVital` in CoinVital.jsx, `tvl-*`):
  🔥 HEAT (5m pace vs the hour, buyers, holders arriving, net buyers, a sane 5m candle — > +40% in 5m = "chasing") vs ☠ RUG (top-10, bundles,
  snipers, insiders, dev, serial launcher, bots, no site / 𝕏, pool drain, < 15 min old, live authority; worst three weigh most) → call 🔥 SEND IT
  (heat ≥ 60, rug ≤ 35) · ☠ RUG BAIT (rug ≥ 65) · 🧊 COLD (heat < 35) · 👀 WATCH. Ten-cell meters; replaces the plain vital on new coins (picker, Coming
  up) and sits mini under each Open gates row (`top-tv`). Hand-set weights, NOT learned — a read for a small ticket, never a promise.
- Coming up filter selects (`.hrt-upf`) are pill-sized with a high-specificity rule (`.hrt-up .hrt-upf select.m-input`): the Fuse page's .m-input font /
  padding blew them up and a plain `padding` wiped the arrow's room (the arrow sat on the text).
- 🏁 RIDE OPTIONS (owner, 2026-10-08: "it says swap off its peak, don't want that"): `peakSellPct` 0 = sell NOTHING off its peak, keep riding (trail
  re-arms) · `rideEnd` swap | keep (ride over, coin stays, normal stops) | cash (sold to card cash, no new coin) — Edit Fuse › Exits; the freeze event
  says what will happen. A frozen coin keeps ITS freeze line (`rideAtPct`): $UDR froze at +20% and was sold 45s later "under +75%" because the next tick
  read rideAt 0 → default 150. Real card set: freeze +30 · stepped trail · 🏠 pull +50 · ride end = keep (backup data/realcfg_before_meta1008.json).
- 🏠 HELD CASH IS NOT CLAMPED WHILE A TAKE IS LANDING (`clamp_hold(c, now)`, `HOLD_SETTLE_SEC` 180 after any `trimAt`): the $fone 🏠 $0.99 "held for
  you" was clamped to the pre-sale wallet cash and then spent as idle cash (restored by hand, backup data/fuse_hq_before_fone_hold.json). The split line
  shows 🏠 held for you (`heldUsd` = holdCashUsd − parked).
- 🔥 CALL RECORD (`_call_track` in `_trench_build`, `data/call_proof.json`, `GET /fuses/call-proof`): every open-list coin's trench-vital call (send /
  watch / cold / bait) noted once at its price, settled 1h later (no price = −100%); the call badge tip shows its record. The engine puts SAFE 🔥 SEND IT
  coins FIRST in the trench drop only once `send` is proven with ≥ `CALL_AUTO_MIN` 10 settled (cfg `sendItAuto`, on; Edit Fuse › Coins).
- Owner buttons: ↩ Sell all / ▶ resume also start the keeper at once (`_fw_kick_now`).
- 🎢🧲💀 MORE READS (owner, 2026-10-08: "love SEND IT — more for fast volume on the curve, better vitals for dips, Coming up coins shouldn't be dead";
  `jup_audit.curve_verdict / dip_verdict / dead_why / pick_read`, `_read_for(row)` fills curve % + curve speed + 5-min flow from the runner board):
  🎢 CURVE (on its launch curve) = 🎢 BOND % × ⚡ PACE → BOND RUN · EARLY RUSH · DUMPING · SLOW CURVE · WATCH (RUG BAIT wins) · 🧲 DIP (well off its
  high) = 🧲 BOUNCE × 🔪 KNIFE → BUY THE DIP · FALLING KNIFE · DEAD DIP · WATCH · else new coins keep 🔥 SEND IT. Row `tv` = {kind, call, meters,
  tags}; `TrenchVital` renders any of them (`tvl-k-curve` blue, `tvl-k-dip` green). Every call is scored in `call_proof.json` (bond, rush, dump, slow,
  dip, knife, deaddip). 💀 DEAD (`dead_why`: nothing in 5 min, < $3K or < 20 trades an hour) = never under Coming up, never an engine buy on the real
  card (pipeline step "alive", `_cat_ok` "dead", 30s seat fallback).
- 🏠 HELD FOR YOU → BACK TO WORK (`arena_prime.release_held`, admin prime `{releaseHeld: {tpl, pairAddress?}}`, select `hrt-held-go` on the 🏠 chip):
  into the card (it becomes idle card cash, spread into the coins) or into ONE coin (its target grows by the held $, the keeper buys the difference;
  leg `ownerAddAt` → not a donor for `balance_small` / seat trims for `OWNER_ADD_SEC` 1h). Not a top-up: PUT IN unchanged. Parked profit keeps its rounds.
- 🫀 CHART HEADER = THE FEELESS EDGE (`ChartVitals` + `useCoinRead` ← `GET /api/reputation/coin-read/{mint}`, 15s cache, re-read 20s; `chartVitals.css`):
  status chips + socials, then the vital (`CoinVital only="vital"`) beside the read that fits (🔥 / 🎢 / 🧲 `TrenchVital`), then one `cv-nums` line (cap ·
  1h · pool · age · 5m). The 8 plain tiles + the Pump radar strip are gone (owner: "the stuff on top of the chart isn't vitals to give the FEELESS edge").
- 💬 ONE CHAT in the war room (`EcosystemWorld`): with a coin's chart open the left chat column IS that coin's room (`coin-<chain>-<pair>-trenches`);
  the chart's own `aside` chat (`eco-chart-chat`) is gone.
- ⚡ SPEED + CLEANUP (2026-10-08, owner: "clean dead code, run like butter"): GZip on all four services (`GZipMiddleware` ≥ 1KB; a 287KB trench list
  went raw) · pick lists / trench / Open gates cached 10s server-side (`_disc_cache`, `LIST_CACHE_SEC`) · 46 dead frontend files removed (unused shadcn
  ui kit, TopCoins, EcosystemPlatforms, DocumentPages, constants/testIds, hooks/use-toast) · dead backend: old Arena bracket (`bracket_*`,
  `battle_seats` — the league replaced it), `_globe_row`, unused locals/imports (pyflakes clean except env_loader side-effect imports). Build = 0
  warnings. Re-run the "never imported" scan after deleting anything (one deletion orphaned toast / use-toast). Not done: moving ethers / wagmi out of
  the main bundle (wallet connect rework), the reputation_service.py split.
- 🏷 EVERY PICK TAB HAS ITS OWN READ (`jup_audit.read_for_lens`, `LENS_READ`; discover rows `tv`; the curve read always wins on the curve):
  🚀 Movers / Pump trending = `mover_verdict` (🚀 MOMENTUM × 🧯 BLOW-OFF → BREAKOUT · BLOW-OFF TOP · COOLING) · 🌊 Volume = `flow_verdict`
  (🌊 SURGE × 🧪 WASH → VOLUME SURGE · WASH TRADED · DRYING UP) · 🪙 Majors & stocks = `trend_verdict` (📈 TREND × 🌀 CHOP → TREND UP / DOWN · CHOP)
  · 🟢 Dips = dip read · 🗑 Trench = SEND IT · New to you / New launches / All ranked = `pick_read`. Every call is scored in `call_proof.json`
  (`_call_track` also reads the dressed tab lists in `_disc_cache`). `tvl-k-mover` pink · `-flow` cyan · `-trend` gold.
- ⛶ Mini chart + mini card have a corner expand button (`mch-max` / `mcd-max`, `.mch.is-max` = 84vw × 70vh chart, remembered). Open gates rows are
  neutral with a slim left edge in the call's colour (`top-tr.call-*`); the mini call is a compact pill (flex, never stretched).
- ⚡ CHART LOADING, THE THREE REAL CAUSES (2026-10-08; charts on new coins took 7–20s, then the service froze): (1) `candles_service._load()` parsed the
  33 MB tick store on EVERY chart request / tick / stream message and `_save` re-wrote it each tick → the event loop froze, health timed out and
  keep-alive killed the service (RSS 948 MB). Now ONE in-memory store (`_mem`, re-read only if the file changed), `_LAZY_SAVE` on at startup, written by
  `_flush_loop` every `FLUSH_SEC` 20s in a thread + on shutdown (RSS 334 MB; 30 charts at once ≤ 2.2s, health 66 ms meanwhile). (2) `_pair_base_token`:
  each of the chart's four callers did its own 8s DexScreener wait on an un-indexed pool → ONE shared lookup (`_base_flight`), DexScreener + Jupiter at
  once, a miss kept 45s; `_accept_mint_hint` is capped at `HINT_BUDGET` 2.5s (Jupiter proof first, then any RPC lane) and a miss sits out 30s.
  (3) `_late_history` waited for ALL providers before using any → each is used as it lands. Frontend: `PriceChart`'s live-stream effect is keyed by
  the POOL (refs for `pair` / `ratio`) — a parent rebuilding `pair` each render reconnected the websocket on every tick; `warmCoin` (hover) warms ONE
  timeframe after 140 ms (`candles.prefetchInterval`), not six per row passed over. "CHARTS SLOW" ⇒ `curl :5099/api/candles/health` time + the service's RSS first.
- 🫀 CARD LIVE (`components/CardLive.jsx` + `lib/cardActivity.js` pure + tested + `styles/cardLive.css` `clv-*`; inside `.fcd` of BOTH `FuseCard` and
  `LiveFuseCard` → tier cards, the real card, held cards, landing hero, mini card, Arena stage, prebuilt rail): heat 0–3 from the coins' live 5-MINUTE moves
  (avg |m5| ≥ 1.5 / 4 / 9; one coin ≥ 15% lights a sleepy card) — activity, not profit. Edge ring beats faster with heat (4.2 → 1s), tinted up / down /
  flat / ice (every coin locked); sparks 0 / 4 / 7 / 11 rising or falling; one-shot sweep when the card's value changes; gold scan line while a coin is
  buying; ONE chip for the hottest coin ("🔥 $SYM +22% 5m"). transform + opacity only, `.clv` is an fxPause surface, lite / reduced motion keep a still
  ring. `LiveFuseCard` reads the live poller even when `serverOnly` (for m5 only — the real card's value stays the server's).
- ⚡ QUICK LOOK ON EVERY LIST (`TrenchQuick`, opened by the ticker in every `SwapPicker` tab and every Open-gates card; replaces the side drawer there):
  live chart + the tab's read + vital + ten fact tiles + Pick / War room / Mini chart / Case file / Copy CA, ← → through the list. 🏷 CALL CHIPS
  (`callLanes`, `sp-call-*`) on every tab filter the list by its own read (BREAKOUT 7 · WASH TRADED 142 …). `jup_audit.fill_row` gives every list row the
  facts its source never carried (cap, logo, 5-min volume, trades / h, holders, curve %) — only empty fields, the runner board first, then Jupiter.
  Trench Open gates = ⚡ Split (🆕 newest | THE READS lanes Hot · Curve · Dips · Watch · Avoid) or ≡ List (`feeless.openLayout`).
- 📣 PUMP'S OWN CALLOUTS (`backend/pump_calls.py` pure + tested; found by reading pump.fun's page scripts — the 2026-10-06 note "Pump has no callouts
  endpoint" is WRONG now): on the Pump coin index (`PUMP_API_URL`) `GET /home-feed?pageSize=150&platform=WEB&chain=solana` (ranked callouts: caller,
  thesis, cap it was called at, multiple since, views), `/home-feed/new` (newest) and `/pnl-leaderboard/positions?period=daily` (today's top callouts by
  the caller's profit). `_pump_calls_build` (60s, last good board kept) → public `GET /fuses/pump-callouts`, picker lens `calls` (📣 Pump callouts,
  loudest first: `pump_calls.heat`), row field `pc` on every list / Open-gates row + coin-read, `PumpCallouts` strip on top of Open gates (🏆 top today ·
  🆕 newest), `PumpCall` in the quick look. Called coins also join the launch feed (market.py `pcall` jobs → movers). Thesis text is other people's
  words: trimmed, control chars dropped, rendered as text. Our own leader / mover / fresh calls are now labelled "📡 FEELESS CALLS". Never advice.
- 🧲 FEEDERS (`backend/feeders.py` pure + tested; Pump, 2026-10-08: a new coin PAIRED with an existing runner routes every buy through the runner's
  pool): Pump's coin record carries `quote_mint` (all-ones / wrapped SOL = plain SOL). `_feeders_build` (2 min, 8 `/coins` pages read one after another)
  → per runner: paired coins, new this hour, trading in the last 5 min, cap riding on it, `feed_score`. Row `fd` on the runner, `pairedWith` on the
  child (⛓ "trades through $X, moves with it"), picker lens `fed` (🧲 Fed runners, ≥ 2 paired), `Feeders` in the quick look, public `GET /fuses/feeders`.
  ENGINE: `arena_prime.CATEGORIES` + `fed`, behind `PROVE_FIRST` {'fed': 10} — the engine takes a fed runner only once the list's OWN settled 1-hour
  record (`LENS_TRACK` now + `calls`, `fed`) is positive over ≥ 10 coins; until then Coming up says "proving first". A new list ⇒ PROVE_FIRST, never straight in.
- ⚛ SWAP-IN = A POP-OUT (`SwapPicker pop`, portal `.spx`, `FuseBanner`: spinning atom, $OUT → ? energy wire, live coin count, 20s refresh bar;
  `styles/quickPulse.css` `spx-*` / `qp-*` / `pcl-*`; `.spx-banner` is an fxPause surface; Esc / outside closes, the quick look opens above it).
  11 lists. The inline `<SwapPicker>` (no `pop`) is what tests render.
- 🫧 QUICK LOOK IS LIVE (`TrenchQuick` + `QuickPulse.jsx`): the list's own row re-read every 20s, `useCoinRead` (coin-read re-reads Jupiter every ~60s for
  a WATCHED coin), price every 10s. `Socials` (site / 𝕏 / Telegram from Jupiter via `jup_audit.facts` + `fill_row`; "✓ site set" when the board only
  knows it exists; 🚫 none) · `ChartPulse` (`lib/chartPulse.js` pure + tested: place in range, off high, greens, streak, volume vs before, body — from the
  candles of the timeframe ON SCREEN, so it changes with the chart) · `FlowWindows` (`jup_audit.windows`: buy pressure by $, organic, net buyers, traders,
  avg trade, holders / pool / volume change per 5m · 1h · 6h · 24h; follows the chart: 1m→5m, 5m→1h, 15m→6h; `flowShift` = 5m vs 1h pressure) ·
  `edgeTiles` (avg trade · turnover %/h · exit depth = pool ÷ cap · callers · feeders). The chart column is sticky. Hand-set reads, not learned.
- 🩸 Card pops = −HP text (`POP_MS` 4000, 13px number + one plain meta line "♻ COMPOUND · $SYM · BACK TO WORK", no pill; `popTag(why)` from the keeper's
  reason; a confirmed sale ≥ 20c UNDER its cost pops red `−$0.30 🩸 LOSS` falling; sparks only from $5).
- 🎯 A REFUSED PICK SAYS WHY (`_pick_why`): "$SYM's pool holds $7,000 — under your $8,000 pick floor … your own setting" / no price yet / dollar coin /
  lookalike / source did not answer — never the old "no live pool right now" (owner: "stop it from saying coin has no live pools in trench"). A launch coin
  on the open list is held to min(pick floor, trench floor) and keeps `trenchOnly` so the keeper uses the same floor; when the live lookup misses, the
  feed's own pair for that coin (`_open_pairs`) stands in. Trench tab rows use the trench floor in the picker too.
- Open gates ≡ List view has the read lanes (`list-lanes`: All reads · 🔥 Hot · 🎢 Curve · 🧲 Dips · 👀 Watch · ☠ Avoid, with counts) like the split view.
- ⚡ LAG 2026-10-08 (Fuse): the nebula `.fuse-page::after` was a page-TALL promoted layer (≈ 1,275 × 4,070px) drifting forever → still; `.fp-zap` lost its
  drop-shadow filter (children animate under it); mouse glow + scan line are off on Fuse pages; `.cfx > i` no blend mode. Picker lists draw `PICK_PAGE`
  40 rows at a time (IntersectionObserver + "Show 40 more"; live prices + sparks only for drawn rows) — 300 rows were ~18K nodes re-rendered every
  10s. Site wide: `hot-pulse` (filter), `signal-flash` (background), `live-grad` (background-position) replaced by transform / opacity (tips.css).
  The Browser pane reports `visibilityState: hidden` and ~2 fps — never judge fps there; count animations, big animated layers and DOM size instead.
- 🔥🔥 DOUBLE SIGNAL + 🎯 CALLERS + 🔔 RUSH + 🧲 FED LOCK + 🎟 SECOND TICKET (owner, 2026-10-08: "do all ideas"):
  · lens `double` (`_double_rows`): coins BOTH called by 2+ Pump users AND with launches paired with them; own 1h record (`LENS_TRACK`), engine category
    behind `PROVE_FIRST` like `fed`. Often empty — that is correct.
  · caller scoreboard (`pump_calls.caller_track/caller_board/mark_pros/leaders`, `data/pump_callers.json`): each call noted once, judged by Pump's own
    multiple ~1h later (`res`), PROVEN = ≥ 3 judged, median ≥ 1.2×, ≥ half up; `pc.pro` / `pc.pros` on rows, "🎯 Best callers" tab on the callouts strip.
  · call rush (`pump_calls.rush`, `_call_rush_alert`, `prime.callAlert.capK` 0/50/100/250/1000 via admin prime `{callAlert}`; `CallAlert` select in the
    picker's 📣 tab): 3+ DIFFERENT callers in 10 min under the owner's cap → one `fuse-signal` notice per coin per 6h. Off by default. Never buys.
  · fed lock (`arena_prime.fed_lock`, cfg `fedRidePct` 0/25/50/100, leg `fedN`): a coin with ≥ 2 paired launches locks later. second ticket
    (`second_ticket`, cfg `secondTicketPct` 0/5/10, leg `calledN`, event `ticket2`): ONE add from idle cash to a LOCKED coin still called by 2+ —
    PAPER ONLY (`card.real` → never): the keeper does not buy a locked coin, so on real money the engine would count cash that was never spent
    (the $AUTON bug). `PAPER_TRY` switches both on for paper cards unless the owner saved a paper value; the real card's stay off until the owner
    turns them on (Edit Fuse › Exits). Second ticket on real money needs a durable keeper buy flag first — do not just drop the `real` guard.
- 🧹 CRONOS DUST = EVERY COIN (`dust.index_tokens/merge_tokens/clean_contracts/meta_calls/meta_tokens/abi_string`, `_cronos_candidates`): a token LIST only
  finds listed coins, and no Cronos indexer answers without a key (explorer API 401, public nodes cap log scans at 2,000 blocks of 98M). Candidates
  = LI.FI list + CronaSwap list + the contracts a wallet index reports for THIS wallet (`CRONOS_WALLET_INDEX`, Rabby's public token_list — DISCOVERY
  ONLY, its amounts are never used) + contracts the owner pastes (`?add=`, `dc-track`, localStorage `feeless.dustTokens`; unknown ones get their own
  decimals() / symbol()). Every balance is read on-chain by us. Response `checked` / `indexed` → the screen says which sources answered.
- 🎯 SWAP-IN = SEVEN LISTS (`PICK_LENSES`: Pump trending · 📣 Pump signals · Movers · Dips & bottoms · Volume · Trench · Majors & stocks; opens on Pump
  trending). 📣 Pump signals = `LENS_URLS.signals` double + calls + fed in one tab (record shown = `LENS_RECORD`). New to you (9s cold), New launches and
  All ranked are gone from the picker (their server lenses still exist). `SIGNAL_CACHE_SEC` 30 for the three signal lenses. `spx-vs`: the pop-out
  shows the owner's own you-vs-engine record (`realBook.versus`) above the lists.
- 🧹 DUST ONE CLICK, NO SECOND BOX (owner, 2026-10-08): `dc-clean-all` reads "Sell all N coins → gas — one click · 🔥 burns K worthless ($)" and runs
  at once — no `window.confirm`; the wallet's own approval is the confirmation. EVM (`runEvm`): per chain, quote all, then `executeLifiBatch`
  (`lib/lifiExec.js`, EIP-5792 `wallet_getCapabilities` → `wallet_sendCalls` → `wallet_getCallsStatus`): every exact-amount approve + swap on that
  chain in ONE wallet request when the wallet can batch; it returns null on a plain wallet and the swaps go one after another (the wallet prompts per
  transaction — no site can change that; the screen says so once). Every quote still passes `checkQuote`. Picker = EIGHT lists (+ 🆕 New launches).
- ⚡ Quick look chart fills its panel (`--tql-h` clamp(340px, 52vh, 520px) on `.tql-chart .chart-area` + `.candle-canvas`, like the drawer / mini chart; the
  canvas was a fixed 286px in a 420px box and `.chart-foot-chips` / `.chart-stale-note` floated in the gap — both hidden there). 🔍 A coin being LOOKED at
  gets our full holder scan at once (`coin_read` → `_runner_intel`, `scanning: true`, that read cached 6s): insiders / bundled / snipers read "reading…"
  (`WAIT`) then the number (~40s live), "—" = not readable (never a clean zero; a candidate's `bundled` count is used only when `scanned is True`).
- 🧹 EVM sell-all without the prompt spam (owner: "cronos wallet keep spam asking for every sell"): a plain wallet signs every transaction itself (allow +
  swap per coin) — no site can remove that. So: dust (< swap minimum) is SKIPPED on EVM unless "include dust" is ticked (`evmTodo`; it was 2 prompts + gas
  to return cents), the log says up front how many prompts are coming, a wallet "no" (`isRejected`: code 4001 / reject · denied · cancel) ENDS the run
  instead of popping the next coin, and ⏹ Stop (`dc-stop`) does the same. Wallets that batch still get one request per chain.
- 🪜 SIZE LADDER (owner, 2026-10-08: "$2 5-min in the trenches … to $100K holding big majors on 1h"; `arena_prime.LADDER/ladder_stage/ladder_patch/
  ladder_view`, real cfg `ladder` (owner's switch, off by default), `_ladder_step` in the tier tick → card `ladderStage` + event `ladder`, applied in
  `_prime_real_cfg`; `/fuses/prime.ladder` → `LadderCard` on top of Edit Fuse's main pane, `styles/sizeLadder.css` `lad-*`): 🗑 TRENCH $0+ (5m, 3 coins,
  20% scout, lock +15 / 8%, stop 15) · 🏃 RUNNER $10+ (15m, hunt line) · 🎯 SNIPER $100+ (30m, $100K pools, buyers 65%) · 🐋 BLUE-CHIP $1K+ (1h, majors
  anchor) · 👑 MAJORS $10K+ (1h, 6 coins, safe cycle). Stage = value at the last bell; up at the floor, down under 80% of it. Every value is an editor
  option (test). While on, the stage's keys beat the owner's own for those keys; everything else stays theirs. Plan for the size — not a proven edge.
- ⚙ EDIT FUSE = A POP-OUT (owner, 2026-10-08: "more space and understanding, meta + degen styling"; `CardEditor` in ArenaPrime, `styles/configPop.css`
  `cep-*`): on the card only a launcher (`ce-open`: live chips — clock · coins · stop · lock · ladder stage — + a seat warning); the portal panel has a
  RAIL of sections (⭐ Main · 🎯 Setup · 🪙 Coins · ⏱ Rounds · ⚡ Exits · 🧱 Safety · 💵 Wallet caps, real card) and ONE roomy pane; Esc / outside closes.
  The old tab row, "All N settings" button and wallet `details` are gone (their CSS removed). 🪑 `seatHealth(c, cfg)` reads the card's own pipeline and
  names the step that leaves an empty seat with nothing; when it is the owner's vital filter it offers ONE tap to C+ · 10% organic (never applied
  for them). 2026-10-08: card set to 4 coins held 3 — 4 coins cleared everything, the owner's B+ / 30% organic filter removed all 4.
- ⏱ VITALS UPDATE PER ACTIVITY (owner, 2026-10-08): `jup_audit.pace(row)` → hot (≥ 600 trades/h or ≥ $10K in 5 min) · busy (≥ 120/h or ≥ $2K) ·
  quiet = coin-read cache 4 / 8 / 15s, Jupiter re-read 12 / 25 / 45s, client poll 5 / 10 / 20s (`coin-read.pace`, `at`). `useCoinRead(mint, kick)`
  polls at that pace and re-reads AT ONCE when `kick` changes (the live price moved = a trade), never faster than half its pace (kick reads share
  only a 1.5s-old answer). Quick look passes the live price, the war-room header its pair price. LIVE chip shows the pace (🟠 HOT) + "Ns ago";
  every fact tile number re-animates when its value changes (`tql-flip`, keyed by value).
- 🧬 EDGE SCORE = COMING UP (owner, 2026-10-08: "coming up should be the best of my swap-in, not bs — plus meta humans could never figure out";
  `backend/confluence.py` pure + tested, `_swapin_lists` (the picker's dressed lists ≤ 5 min old + bottom + trench) → `_edge_rank` (20s) →
  public `GET /fuses/edge`): every coin across the swap-in lists scored by EVIDENCE = rank-weighted average of each list's own 1h record + its
  read's own call record + a LEARNED combo bucket (lists 1/2/3+ × read tone × 5-min pace; `_edge_track` notes the top 40 each pass, settled 1h
  later, `data/edge_proof.json`) + capped hand-set tilts (vital, organic, proven callers, failed safety; ±6 max, labelled). Coming up = the top
  coins that clear the card's own checks (`_cat_ok`), then up to 4 best-evidence coins one check away; the 30s seat fill takes edge coins first.
  `EDGE_BUY_MIN` −25: a coin whose evidence says it typically loses 25%+ an hour is never shown or bought. Coming up keeps ITS OWN record (key
  `up`, label "ITS RECORD"). 2026-10-08 records: BOND RUN −82%, movers −87%, Pump trending −1.5%, fed −0.5% — the score mostly ranks bad vs worse.
- 🪜✋ A TAP BEATS THE LADDER (owner, 2026-10-08: "trying to click how many coins"): with the ladder on, its stage set coins = 3 over the owner's
  saved 4, so the button looked dead. Now every realCfg key the owner saves while the ladder is on joins `prime.ladderKeep` and
  `ladder_patch(.., keep)` skips it; switching the ladder ON again starts a fresh climb (`ladderKeep` = []). Editor rows say `🪜 ladder` (the stage
  sets it) or `✋ yours` (`ce-mark`); `/fuses/prime.ladder.keys/keep`. One-time `_ladder_keep_fix` (`ladderKeepFix1`) kept the owner's 4 coins.
  Edit Fuse › Coins: the trench lists sit in a fold (`cep-fold`), not inline. "A BUTTON DOESN'T WORK" ⇒ compare the stored realCfg with `cfgEff`
  first — a layer on top (ladder, real_guard, seat fit) is the usual cause.
- 🌊 FLOW EXIT + 🚨 RUG RADAR + 🌊 FLOW ENTRY (owner, 2026-10-08: "flow exit — and per coin"; `backend/flow.py` pure + tested): the candles
  service's trade tape (`/api/candles/trades/solana/{pool}`, its own 15s cache) → `window` (last 90s: buy $, sell $, trades, price move, biggest
  sell). `_flow_guard` inside the 6-second `_real_guard_loop`, every `FLOW_EVERY` 15s, for the real card's held coins: FLOW EXIT (cfg `flowExit`
  normal 2× sellers · tight 1.5× · off; needs $ + trades + a sliding price; per-coin override leg `flowExit` via admin prime `{leg: {flowExit}}`,
  the 🌊 select on each coin row; riders / ride-or-rug tickets / frozen coins keep their own plan) and RUG RADAR (cfg `rugRadar`: creator sells
  $20+, a top-10 / bundle / sniper wallet dumps $100+, one wallet ≥ half the flow; watches every coin) → the coin leaves the card like a fast stop
  (placeholder seat, keeper sells next pass), event kind `flow` / `rug`. Every such exit is noted at its sell price and judged 1h later
  (`data/flow_proof.json`, `/fuses/prime.flowProof`: negative = the exit saved money). FLOW ENTRY (cfg `flowEntry`): Coming up's top 4 edge coins
  get their tape read; a coin whose last 90s are seller-led waits as watching ("sellers lead …"). `/fuses/prime.flow` → `FlowBar` on each coin row.
- 💀 PAPER CARDS DIE AT −60% (owner, 2026-10-08: "paper cards must sl at −60%, we can't promote dead cards"): `paper_reset.BROKE_PCT` 25 → 40 —
  a paper tier card worth ≤ 40% of everything put in (after ≥ 5 rounds and 1h) goes to the record, its config is scrapped and it restarts on a
  NEW config (`_paper_broke`, the existing path — never a second mechanism).
- 🧠 THE ENGINE LEARNS FROM THE REAL CARD (`backend/real_learn.py` pure + tested, `data/real_learn.json`): `_learn_drops(before, after, price)` records
  every coin that leaves the real card — round tick, fast stop, flow / rug exit — with its buy snapshot (leg `bought`: age · 1h move · buyers ·
  pool · 1h volume · tag) + who picked it → its result vs the book entry. `table` = median per feature bucket (≥ 5 pieces); the 🧬 edge score adds
  it as a part ("your real trades (N pieces)", `confluence.edge(real_tbl=)`), so Coming up drifts toward what paid with real money. Public
  `GET /fuses/learn` (n + best / worst buckets, % only) → `LearnLine` under Coming up. It starts empty: lessons land as coins leave the card.
- ⏭ A BUY THAT CAN'T FILL FALLS BACK TO NEXT UP (owner, 2026-10-08: "swap-in should work or fall back to retry or the next up buyable"): Jupiter
  "token is not tradable" / "no route" (`fuse_wallet.UNROUTABLE`) benches the coin AT ONCE (it was retried forever — $HOOKI sat "waiting for card
  cash"); the stuck-buy swap then takes Coming up's READY coins first, in order (`up_ord` from the last tick's `pipeline.up`), event names the coin
  "(next up)". Slippage misses still retry first (5% max).
- 🎯 TP + SL = ONE control on each real-card coin row (`TpSl`, `tps-*` in configPop.css): the button shows "+TP · −SL"; its panel has a + column
  (take-profit) and a − column (stop), "tier" = the card's own. Replaced the two selects.
- 🫀 LIVE COIN ROWS ON EVERY FUSE CARD'S LIVE SIDE (`LiveFuseCard` → `legState`, `LegLogo`; `styles/cardLegs.css` `fcl-*`, `.fcd-legs` is an fxPause
  surface): logo beside the name · a heat bar under the row = the coin's live 5-min move (±15% = full width) · state glow + icon: ❄ riding,
  🧊 frozen, ⏳ buying (gold scan), 🔥 hot / 🩸 dumping (|5m| ≥ 5%, pulsing edge) · the % re-animates when it changes. Card images inside the
  card back are blocks by default — logos need `.fcd-legs .fcd-leg .fcl-logo { display: inline-block }`.
- 🌊 BUYS vs SELLS BAR EVERYWHERE (`BsBar.jsx` + `styles/bsBar.css` `bsb-*`; data = the coin-edge record's `bs` via `_bs_rows`: Jupiter's 5m / 1h
  window stats re-read ≤ 30s old for coins on screen (2.5s cap) + the live 90s tape for held coins — NO new poller): `[5m] [bought ▮|▮ sold]`,
  tap the time → 5m ⇄ 1h for the whole site (`feeless.bsTf`), tap the bar → the coin's flow-exit menu where `onFlow` is given (real-card coin rows;
  the separate 🌊 select is gone). On: real-card coin rows, swap-in picker rows (inside the coin cell), Coming up, quick look header, war-room
  chart header (`cv-nums`), mini chart. Old `FlowBar` removed.
- 🎈 `lib/floatPop.js` `useFloatPop(width)`: popovers on rows that animate are drawn on <body> at their button (fixed, flips up near the bottom,
  outside click / Esc / scroll closes). The TP/SL panel used to sit UNDER the next row. Any new row popover ⇒ this hook.
- When deleting a component by string, cut from ITS OWN start to ITS OWN end — a cut from a comment to the next export once took `TpSl` and
  `LearnLine` (inserted in between) with it.
- 🔗 SOCIALS FIRST ON EVERY LIST ROW (owner, 2026-10-08: "trench should show socials first and clickable"): `_clean_rows` fills `site` / `x` / `tg`
  from Jupiter's audit (a real link) else the runner board (may only know it exists) — they were on 0 of 250 Open-gates rows. `SocialIcons`
  (QuickPulse.jsx, `qp-ico`): 🌐 𝕏 ✈ links FIRST on trench read cards, Open-gates list rows and swap-in picker rows (each link stops the row's
  click); "✓" = set at launch but no link on record; 🚫 = none set.
- 🧹 MY CARDS CLEANUP (owner, 2026-10-08): real-card coin rows show 4 things — 🌊 buys/sells bar (flow-exit menu), 🎯 TP·SL, 🎯 pick, Sell all —
  the rest (💰 profit, sell 25 / 50%, ⇄ auto-swap, ❄ freeze) sit in ONE `RowMore` "⋯" popover (`rmo-*`, floatPop). Coming up's three filter
  selects became one chip (`UpFilter` → `hrt-upchip`) that opens Edit Fuse › Coins (`feeless:edit-fuse` {tab}); the filter rows live there
  (`vitalMin`, `organicMin`, `noSerial` in EDIT). The two "sold" numbers are named for what they are: under the card CONFIRMED SALES (ledger),
  in ALL-TIME "everything else" (all-time − coins now: sales + write-offs + dust).
- 🧨 DEGEN EDGES (`backend/degen.py` pure + tested): 🐳 SMART-WALLET RADAR — `_smart_track` (with the lens pass, ~2 min) reads the tapes of the real
  card's coins + Coming up's top 8 (`_flow_fetch` keeps the raw trades in `_flow_trades`), notes each wallet's FIRST buy of a coin, settles it 1h
  later (no price = −100%), `data/smart_wallets.json`; smart = ≥ 3 settled, median ≥ +20%, ≥ 60% up. A coin a smart wallet buys is tagged
  "🐳 N smart" (edge rows `smart`, Coming up tag); it moves the edge score ONLY once the radar's own record (edge proof key `smart`) has ≥ 5
  settled. ⚡ BUY BURST — flow entry reads Coming up's top 8 tapes; buys ≥ 2× sells, ≥ $150 bought, price up → the coin goes first, tagged
  "⚡ buy burst", scored under edge proof key `burst`. 📣 CALLOUT SPIKE SELL (real cfg `calloutSell`, on; Edit Fuse › Exits) — 3+ different Pump
  callers in 10 min on a held coin up ≥ 20% → half its PROFIT sold into the buying (`_skim`, once an hour per coin, card `spikeAt`).
  Moon bag NOT built: it needs a leg that sits in the card outside the seat count — ask the owner how it should count first.
- 🔗 REAL SOCIAL ICONS (owner, 2026-10-08: "globe and x icons — a real icon"): `SocialIcons` / `SocIcon` (QuickPulse.jsx) draw SVG globe ·
  X · Telegram; a real link opens it, set-at-launch with no link = a dim icon that opens the coin's Pump page, none = 🚫. `runners._socials`
  now keeps the LINK (http(s) only, `_link`) instead of True, so trench rows carry real links. 🔗 Socials first: `VFILTERS` `soc` (pick lists)
  + `open-soc` in Open gates (`socFirst`: link → set → none, order kept). ⋯ per coin = a tile tray (`RmoTile`: 💰 into coins · 🅿 park ·
  🏦 cash · 🏠 initial out · ✂ 25 / 50% · ⇄); ❄ freeze is ONE tap on the row (`hrt-fz`). 🎯 `GoalBar` on the real card (milestone the
  owner picks, remembered per browser + "% of put-in back"). ☠ BUSTED calls (`busted`: ≥ 30 settled, median ≤ −20%) render red with
  their record badge (`tvl-rec`, every call with ≥ 10 settled shows `±N%/1h`). `real_learn.note`: no buy stamp = `holdMin` None.
- 🏦 DEGEN SETUP 2026-10-09 (`_degen_fix_1009`, once, `degenFix1009`, backup data/realcfg_before_degen1009.json; every key → realOwnerSet + ladderKeep):
  the "always keep $1 riding" floor (`tpStakeUsd` 1) sat above every coin on a $1.39 card → `tp_room` 0 → no peak sell / lock bank could
  fire (six rides to 1.1–1.3× gave it all back in 40 min). Now: floor off · stack skim $0.50 · 🏠 `houseAt` 50 (NEW: initial out once on EVERY
  non-anchor coin; trench / ticket coins keep `trenchHouseAt` when set) · ⏳ `pickLockMins` 30 (NEW, `arena_prime.pick_lock` +
  `_cook_warn`: a hand pick-swap / ⇄ replace / whole ✂ sell of a coin held < N min → 409 "⚠ ⏳ …" → "Sell it anyway" re-sends with `ack`;
  the warn dialog now covers pickSwap · fillSeat · replace · manualSell) · ride over → 🏦 `rideEnd: 'bank'` (NEW: sells what it holds above
  entry, ignores the keep-riding floor, coin stays) · min hold 30 · lock bank 50% · trench off (`trenchAuto` false, `ticketRide` false and
  the legs' ride-or-rug cleared so their stop sells them, cycle → press). Clock untouched. Evidence: pay-map 1,223 pieces — trims +$21.89,
  whole exits −$32.83, sold < 15 min −$19.30, held 30–60 min +$4.99. A plan for the record, not a promise.
- ⚡ SLOW LOAD = COLD CACHES, LAG = DEV MODE (measured 2026-10-09): warm, every Fuse endpoint answers in ≤ 120 ms, 0 long tasks, all
  animations transform / opacity. What was slow: (1) a viewer arriving after a cache ran out waited for the rebuild — `/fuses/contenders`
  0.4–4.4s every 30s, `/fuses/arena` ≈ 20s cold, the launch feed 16–23s after every restart (auto-pull restarts the backend on each
  backend push). Now stale-while-revalidate: `_contenders_build` (copy ≤ 10 min answered, ONE background `_contenders_rebuild`; warm
  loop passes `fresh=True`), `_arena_mega` (≤ 10 min, background rebuild under `_FUSE_FORCE`), launch board snapshot on disk
  (`launchpad_board.save_board_snapshot/launchpad_board_snapshot`, `data/board_snapshot.json`, ≤ 15 min, written ≤ 1/min per kind) served
  stale on a cold start; the Arena stage + contenders league the same way (`ARENA_SNAPSHOT_PATH`, `CONTENDERS_SNAPSHOT_PATH`, read once on boot only — an admin clear never restores it). (2) The owner's Chrome runs the DEV server (`craco start`): unminified 2.7 MB JS, StrictMode mounts every poller
  twice. ⚡ FAST MODE = `bash scripts/serve-fast.sh` → production build on :51368 (`scripts/fast-server.js`, same proxy as setupProxy.js —
  change both), rebuilt on new commits (reload to see it): JS 899 KB, DOM ready 67 ms vs 328, load 183 ms vs 862. New port = new origin
  (connect the wallet / sign in to HQ once there). The dev server stays for development.
- 🧾 CARD TOTALS READ THE WHOLE LEDGER (`_fw_full_ledger`, cached by row count): the KV doc keeps only the newest 2,000 ledger rows,
  and `_fw_public` / HQ Fuse wallet / run report / payouts paid / deposited SOL / lost top-ups / funded-from-ledger summed THAT — once
  the real card passed 2,000 fills it showed fees $1.33 of $2.18, top-ups $15.50 of $22.50, and realized / you-vs-engine lost their
  oldest fills. `realBook.feesUsd` = the book's own total (each fill at its SOL price). `fuse_wallet.card_fees_usd`: card-paid fees at
  the fills' average SOL price, never today's (math.feesUsd read $2.02 vs $2.15). Never sum `d['ledger']` for a money total again.
  "UNEXPLAINED" IN THE MONEY TRAIL IS MOSTLY SOL'S PRICE: put in 0.1912 SOL at ~$117.6 avg; at $110 that alone is −$1.47.
- 🌙 OVERNIGHT SETUP 2026-10-09 (`_overnight_fix_1009`, once, `overnightFix1009`, backup data/realcfg_before_overnight1009.json): the real
  card's SELECTION copies the two paper cards that are up (Diamond +14.9%, Gold +10.2%): runners 12h+ · pool ≥ $50K · ≥ $50K/h · no +20%
  hour required · buyers ≥ 65% · scout off · mover swap off · newOnly off · 3 coins · ≤ 2 swaps an hour · parked profit back after 2
  rounds (was 6 = 3h idle on the owner's 30-min clock). Owner's clock / stop / hold / exits untouched. One command overnight:
  `bash scripts/background.sh start` (keep-alive under caffeinate; plugged in, lid open).
- 🚨 RUG RADAR "ONE WALLET" NEEDS A POOL-SIZED SELL (`flow.RUG_ONE_POOL_PCT` 3, `rug_why(.., liq)` ← leg `liqNow` / `liq`; unknown depth =
  judged as before): overnight 2026-10-09 it sold STONK / WETH / RAY / Fartcoin / CATE / DARK ×3 on a whale's $1K–13K sell into a deep
  pool — its own record: 23 rug exits, median −0.4% an hour later (saved nothing) and every exit + refill was a round trip (102 swaps in
  10h with a 2/h rotation cap — the cap only counts round rotations). Creator-sold and top-holder-dumped rules unchanged.
  Flow exit's record is +3.7% after its sells (n 4, too few to act on yet). READ `data/flow_proof.json` BEFORE TRUSTING AN EXIT RULE.
- 🚀 SEND IT 2026-10-09 (`_hunt_fix_1009`, once, `huntFix1009`, backup data/realcfg_before_hunt1009.json): owner chose the one-shot lane —
  real card = 2 coins on the Runner hunt line (12h+ · $50K/h · +40% on the hour · $25K pool · record gate off), stop −30, freeze +50,
  trail 30, 🏠 initial out at +50, ride over → bank, runners only (newOnly), scout / mover swap off. Clock 30m, hold 30, ≤ 2 swaps/h kept.
  Vital filter one step looser for it (`_hunt_fix_1009b`: 35+ · 5% organic — 50 / 10 removed all 6 hunt coins). The owner decided with the numbers in hand (replay: ~1 in 5 hunt picks hit 2× within 6h) — don't re-argue it; report results.
- 🗑 TRENCH SETUP 2026-10-09 (`_trench_fix_1009`, once, backup data/realcfg_before_trench1009.json): owner's 5-min / patience 2 trench card =
  🔥 `trenchSendOnly` (NEW, `arena_prime.trench_pool`: the engine's trench drop takes ONLY SEND IT coins, none → it waits; the list reads
  −79% an hour, SEND IT +0.5% / 52% up) · 2 trench coins · trenchAuto on · cycle trench · lock +20 & bank 50% · 🏠 initial out at +30 (all
  coins + trench) · stepped trail 15 · cook 15 min · ride over → bank. The owner's stop (−30), flow exit and rug radar unchanged.
- 🎯 PRO-CALL ENTRY (`pump_calls.pro_entries`, cfg `proCallEntry`, Edit Fuse › Coins; `trench_pool(.., pro=)` puts them FIRST, also under
  SEND IT only): a trench seat takes a coin a PROVEN Pump caller (caller_board `proven`) called ≤ 15 min ago (`PRO_ENTRY_MIN`), only while
  its cap is ≤ 1.15× the called cap (`PRO_ENTRY_LATE`: their price, not the pump after) and the open board marks it `safe`. Walk-forward
  2026-10-09 on 31,937 judged calls: proven-on-the-first-half callers → next calls 50% up (median 1.01×) vs 42% (1.0×) for everyone — a
  small edge, ridden as a ticket with the scalp-the-stake exits. Own record: `procall_proof.json` (`_procall_track` in `_trench_build`,
  shown as `proof.pro` on `/fuses/call-proof`). On for the real card (`_procall_fix_1009`).
- 💸 UNFUNDED SEAT PERMA-FIX (`arena_prime.unfunded_seats`, start of step 4 in `tick`, `UNFUNDED_SEC` 30): a leg with 0 units, no buy in
  flight (`buying` / `wantUnits`), not a placeholder, for 30s holds NO money — 2026-10-09 a pick took a reserved seat whose money had
  already been spread ("a $0.00 ticket"), a ⇄ hand swap passed the $0 on (TPAD → Sludge, "waiting for card cash" for good). It leaves
  the card; the owner's pick goes to `seatPick` / `seatQueue` (ack) and the seat refill funds it (cash, else trims coins above an equal
  share). Fourth version of the "0-unit leg with a mint" bug — this sweeper covers every door.
- 🔥 TOP-3 AUTO SEAT (cfg `topSeat`, on for the real card via `_topseat_fix_1009`; `arena_prime.top_three` = the card's TOP 1/3 chip rule
  (`TOP3_DIVS` mirrors ArenaPrime.jsx — change both), `top_victim`, `TOP_SEAT_SEC` 600): the TOP 1/3 coin takes the weakest seat that is
  not winning (≤ +5%, held past min hold; never rider / frozen / house / buying / queued), real-buy pool floor, no dollar names, not
  falling now; the 🌊 flow exit sells it when sellers lead. Its record = `real_learn` (leg `bought.tag` '🔥 top 3').
- 🛡 SAFE TRENCH (`arena_prime.trench_read_ok`, in the trench drop loop for EVERY door — pro callers, SEND IT, the list): never a coin whose
  read is a busted call (`TRENCH_BAD_READS`: BOND RUN −84 · EARLY RUSH −64 · RUG BAIT −58 · DUMPING −56 · SLOW CURVE −45 · BREAKOUT −45 ·
  FALLING KNIFE −13, 1h medians) or whose ☠ rug meter is ≥ 50 (`TRENCH_RUG_MAX`); no read = not judged; owner picks never limited. Real
  card trench ticket stop −20 (`_trench_safe_fix_1009`). Seats stay at the owner's 4 — a trench coin REPLACES the weakest seat.
- 👻 PHANTOM LEFTOVERS (`fuse_wallet.drop_phantoms`, keeper balance pass): 2026-10-09 the repair / sell-dead path read the wallet BEFORE
  taking the keeper lock, so a $UP sale confirmed while it waited still showed as held → 1.48B sold UP booked back as a $0-cost
  "recovered" leftover → card read $1.25 (real $0.77) and halted on "token balance below card books". Now: the repair route reads
  balances INSIDE `_fw_tick_lock` + `_fw_lock` and skips mints sold in the last 2 min; a recovered $0-cost leg the confirmed wallet
  holds NONE of is dropped (ledger `ghost:` fix row) so the halt lifts. Coins the card paid for still halt.
- 🏠 HOUSE DUST (`arena_prime.house_dust`, `HOUSE_DUST_SHARE` 0.4, tick step 4): after the initial-out, a small ticket's 3–6¢ of house
  money held a whole seat (owner: "not gonna profit with 6c in a seat"). A `house` coin under 40% of an equal seat, not riding / frozen,
  is sold to card cash (profit banked) and the seat refills with a full-size coin the same tick.
- 🎯 SWAP-IN = 8 TABS RANKED BY THEIR OWN RECORDS (`PICK_LENSES`, opens on 🧊): 🧊 Cooling off (`_exhale_rows`, lens `exhale`: open-board coins
  read DRYING UP / COOLING — the only positive reads, +1.9% / +0.6% — safe, rug < 50) · 🎯 Proven callers (`_procall_rows`, lens `procall`:
  `pro_entries` over the last hour, + the call-rush alert switch) · 🔥 Pump trending · 🧲 Fed runners · 🟢 Dips & bottoms · 🌊 Volume · 🗑 Trench
  · 🪙 Majors & stocks. SCRAPPED from the picker: 🚀 Movers (−67%), 🆕 New launches (−71%), 📣 Pump signals (calls −37%, double −79%) — their
  server lenses + records still run (Coming up categories / list_paused read them). `exhale` + `procall` are in `LENS_TRACK` (own records).
  `_with_tv(r)`: raw `_open_board()` rows carry NO read — every safe-trench check computes it first (pro entries slipped past "no read").
- 🧹 CLEAN + BANGERS 2026-10-09 (`_clean_fix_1009`, backup data/realcfg_before_clean1009.json):
  · 🌙 4 COINS MEANS 4 (owner: "4 coins only, figure out a better way to moon"; replaced riding outside the count): `seats_used` = every
    leg; `house_dust` banks a tiny house coin riding or not (only the owner's ❄ freeze is kept); `house_ok`: the 🏠 initial comes out
    only once what STAYS is ≥ 40% of an equal seat — a 12¢ ticket's pull left a 4¢ rider; now the coin moons with its full size on the
    lock bank + stepped trail until its profit alone is worth a seat.
  · ⚖ `cap_trim` (cfg `maxCoinPct` 0/25/35/50, real card 35): a coin over the cap (or 1.4× an equal seat when the count makes that larger)
    is trimmed to it; never riders / frozen / house / buying.
  · 🚀 `bangerRefill` (real card on): the service builds cfg `bangers` (`_bangers`: 🎯 pro-call entry → 🔥 `top_three` → 🧊 `_exhale_rows`;
    real-buy floor, not on card / cooling, no dollar names, `entry_ok`, `trench_read_ok`) and `best('runner')` takes them FIRST for every
    normal runner seat that opens (flow exit, stop, rotation, ride end, seat refill). Each leg carries the door as `tag`.
  · Edit Fuse: REMOVED rows scout, mover swap, recycle (+ every), stack-skim, "keep $ riding", second ticket, fed lock, SEND IT auto (→ the
    SEND IT only row), ticket ride-or-rug; rescue + record gate only on paper cards; duplicates gone. META setups + ladder stages no longer
    set scout / mover swap (they set `bangerRefill`). A hidden setting must be neutral on the real card — never hide one that is on.
- 🌊 NARRATIVE LEADERS (`meme_terms.wave_leaders`, `_wave_rows`, lens + picker tab `wave`, in LENS_TRACK): for every ticker wave spiking today
  (≥ 10 coins named after a word) the ORIGINAL — biggest, then oldest — never a copycat; site or X set, `safe`, $5K+/h, rug < 50, no busted
  read. A banger door (after 🎯 proven callers) ONLY once `_wave_ready()` = its own 1h record has ≥ 10 settled and a positive median.
- 🌊 Real card flow exit = TIGHT (`_flow_tight_fix_1009`, owner's call: faster scalps / swaps). flow_proof that day: 6 exits, +0.3% after.
- 🎯 CLEAN ENTRIES (`arena_prime.entry_gate`, cfg `entryGate`, real card ON via `_entry_fix_1009`): a FULL seat needs buyers ≥ 50% (60% blocked
  nearly everything — the market sits at 45–58%; pre-break keeps 60) · not
  +60% 1h · not +3% 5m (the "−4¢ a minute later" entry) · ≥ 3% under its 4h high (when the chart is read) · pool ≥ $50K · ≥ 6h old ·
  ≥ $200K/h. Missing readings not judged; trench tickets keep their own rules. Applied on EVERY door: board runners (`_step` "clean
  entry"), `_bangers`, top-3 auto-seat, 30s seat fallback; the owner's picks get it as a 409 WARNING. The 🔥 Top 3 door had skipped the
  chase / at-highs checks entirely — that is how the card bought highs. Hunt line `runnerMinChg1h` 40 → 0 (it required the run).
  Evidence (real card, 86 exits): buyers > 65% +2.0% 4/4 · < 6h −17…−20% · pool < $50K −15…−22% · +60% 1h −10…−25%.
- 🌅 BEFORE THE BREAK (`arena_prime.pre_break`, `_prebreak_rows`, lens / tab `prebreak`, LENS_TRACK): safe runner-board coins, clean entry,
  5-min pace ≥ 1.5× the hour, buyers ≥ 60%, 1h −5…+30, 5m 0…+3, not at highs. Banger door only once `_prebreak_ready()` (10+ settled, +median).
- 🌊 `flowMinHoldMins` (real card 10): the buys-vs-sells exit leaves a coin alone that long after its buy; rug radar / stops act at once.
- 🧠 real_learn hold time = from the leg's buy TIME `at` (`firstEntry` is the first entry PRICE — every piece read ~30M minutes).
- 🔗 PUMP LINKS (`_PUMP_LINKS`, `_pump_links_put` / `_pump_links_warm`, ≤ 12 coins per `_trench_build` pass, 1h cache; the pump-profile route
  fills it too): Jupiter often has no socials for a Pump coin ($UNITS: Jupiter none, Pump x.com/Unitsdotcash + units.cash). `_clean_rows`
  socials = Jupiter → Pump → runner board. http(s) only. 🧊 Cooling off also needs a site or X and organic ≥ 10% (owner: "IBM is a wash
  rug" — DRYING UP with no site / X).
- 🪑 SEATS NEVER WAIT ON STACKED GATES (2026-10-09: UNITS −26% + LOOT −30% stopped, 2 seats open with $1.11 — clean entries → 2 coins, the
  vital filter → 0, and the 30s fallback ran through the same strict gate): `entry_gate(.., core=True)` (sellers leading / chasing /
  at highs / thin pool only) for the 30s seat fallback; `ENTRY_MIN_VOL1H` $200K → $50K; the real card's vital-grade filter OFF as an
  engine gate (`_vital_off_fix_1009` — a hand-set score with no record). Placeholder row reads "seat open · the next clean coin takes it".
  WHEN SEATS SIT OPEN: read `pipeline.steps` — the step that drops to 0 is the choke, never stack another gate on top.
- 🌙 MOON LADDER (`arena_prime.is_moon / moon_rungs`, cfg `moonLadder`, real card ON via `_moon_fix_1009` + trench 🏠 line 100): trench / ticket
  coins don't lock at the card's +15% — they lock at 2× (`MOON_LOCK`), no lock-bank; the initial comes out at 2×; 25% sells at each rung
  `MOON_RUNGS` 3/5/10/20/50× (leg `rungs`); trail ≥ 40% (`MOON_TRAIL`); a riding moon bag is never house-dust banked. Ticket stop unchanged.
- 🌊 THE TAPE (`flow.tape_read`: ⚡ burst · 🧲 absorb · 🏔 climax · 🩸 dump · ➖ calm from the 90s window): `entry_why` waits on dump / climax;
  `flow_exits` sells HALF the profit of a coin ≥ +20% into a 🏔 buying climax (once per 15 min, leg `climaxAt`, event `flowKind: 'climax'`
  → its own flow_proof record); `_bangers` skips dump / climax and puts burst / absorb first (tagged); picker rows carry `tape` (top
  `PICK_TAPE_TOP` 12, one batched `_flow_fetch`) and `entry` ('clean' or the gate's reason) → chips `sp-tape-*` / `sp-entry-*`.
- 🤖 `entry_gate`: organic < 5% (`ENTRY_MIN_ORGANIC`, vital `organicPct`) = "bots" — $LOOT read BUY THE DIP on 2% organic volume.
- 🌊 TAPE BUDGET (2026-10-09): Helius hit "max usage reached" → every tape read goes through `candles_service._rpc_trades` (getSignatures +
  a getTransaction batch). Picker rows reading the tape for 12 coins × 11 tracked lists every 2 min spent every RPC lane; all lanes were
  benched (`_tape_bad` 60s) and the REAL card's flow exit + rug radar went blind ("provider unavailable"). Picker `tape` is now CACHE ONLY
  (`_flow_now` ≤ 60s, filled by the card / bangers / quick look); `TAPE_NEW` 25 → 10. Never add a per-list-row tape FETCH again.
  "PROVIDER UNAVAILABLE" ON THE TAPE ⇒ check Helius quota (`api.helius.xyz … 429 max usage`) and `_tape_bad` before anything else.
- 🏆 BEST 3 replaces Coming up on the real card (`ComingUp` now renders `pipeline.best` = the first 3 of the engine's banger list: every door,
  clean entry, tape-checked — the list an open seat takes from; 🥇🥈🥉 + door tag + tape chip + ⚡ Swap now / ⏱ bell). `UpFilter` + its CSS removed.
  🏆 Best now tab (`lens=best`, `_best_rows` = the last real-card banger list) opens the picker. Picker = 7 tabs: Best now · Pump trending ·
  Proven callers · Narrative leaders · Cooling off · Trench · Majors & stocks (Before the break / Fed / Dips / Volume left; lenses + records run).
- 🗑 TRENCH VITALS DEX (`dexCells` / `TrenchDex`, `tdx-*` in quickPulse.css, trench tab rows): top-10 · dev · insiders · bundled · snipers ·
  holders · rug meter, each ok / mid / bad on the safety lines, "—" = not read, score "N/M clean". pickRow carries those fields + `rug`.
- 🌊 The tape is in every coin read (`/coin-read` → `tape` {read, label, buyUsd, sellUsd, n, pxChg}; one pool, 12s cache) → chart header chip `cv-tape`.
- 🧱 Real card floor −10% (`_floor_fix_1009`; owner "keep $3.62" — run started $3.61; a floor AT the start would sell on any wiggle).
- 🧠 TRENCH BRAIN (`backend/trench_brain.py` pure + tested; `_brain_track` in `_trench_build`, `data/trench_brain.json`, public
  `GET /fuses/trench-brain`, lens + picker tab `brain` (in LENS_TRACK), `BrainNote` / `brainLine`): every busy open-list coin (top 120)
  is watched each pass and judged on the PLAY a ticket makes — which line it touches FIRST: +50% (hit, on to the next) or −30% (cut);
  neither in 1h = its 1h move; no price = −100%; a pass where Jupiter answers nothing is skipped. It learns single features AND pairs
  (age · cap · stage · 5m pace · buyers · 5m / 1h move · safe · top-10 · socials · read · tape), scores a coin from its 3 strongest
  cells shrunk by sample size, and is TRUSTED (`proof`: learn on the oldest 60%, rank the newest 40%) only with ≥ 30 unseen coins,
  top third positive and ≥ 10 pts over the bottom third. Real cfg `trenchBrain` (on): once proven, its safe picks with a positive
  learned play go FIRST in the trench drop (still through trench_entry / read_ok / pool floor). Price samples are ~2 min apart, so
  first-touch is approximate. Organic "bots" check REMOVED from `entry_gate` (Jupiter reads most Pump coins 2–3% organic).
- 🧱 FLOOR, FIXED (2026-10-09, the −10% floor sold the whole real card the instant it was set — the card already sat at −12% — and the
  card then sat in cash for good): (1) a floor switched on / moved while the card is already under it measures from the card's value
  at that moment (`floorSeen` / `floorBaseUsd`, cleared on a new run); (2) a floored card whose re-deal finds NO coins (new-coins-only,
  filters) starts its new run IN CASH (`flooredAt` cleared, event "new run in cash") and the empty-seat refill fills seats as coins
  qualify — `deal()` returning None used to leave it floored forever. `_flow_fix_1009`: real floor −20, vital 35, organic filter off
  (backup data/realcfg_before_flow1009.json). 🧠 Brain watches the 80 newest launches (≤ 3h) first, then the 120 busiest; its lens
  keeps unscanned newest coins (marked), never failed scans; the engine takes only scanned-safe brain picks.
- 🛑 LEARNED TICKET STOP (owner, 2026-10-09: "trench coins SL due to tight small buys — we losing to that"; $Break −32% in 1.8 min on a
  −25% ticket stop): the brain now watches every coin the WHOLE hour and stamps the first time it crosses −20/−30/−40/−50/−70 and
  +50/+100/+200 (`LEVELS`, leg-path `x`), so `stops()` replays every ticket stop (20/30/40/50/70/none) on the SAME paths: avg, median,
  hit %, cut %, `shook` (stopped out, then ran to +50). `best` = highest average once ≥ 30 full paths (evicted partial paths excluded).
  Real cfg `trenchSlAuto` (on): `_prime_tick` hands `ticketSl` = best → `arena_prime.ticket_sl` for young-pick tickets + trench-drop
  tickets, and tickets ALREADY held move to it (0 = ride or rug). Events say "🧠 learned". Rug shield still acts.
- 🗑 The brain lives IN the Trench tab (`brain` per row + `brain` summary on `/fuses/trench`, `BrainNote` + `stopsLine`, `sp-brain` chip;
  ordered by learned play once ≥ 30 judged, failed scans never move up); its own tab is gone. 🚀 Live movers tab (`_live_movers`, lens
  `live`, LENS_TRACK): ≥ $3K traded in 5 min, +3%+, buyers ≥ 50%, 60+ trades/h, scan not failed, by 5-min $ × move. 🏆 Best now never
  empty: no banger clears → the 🧬 edge ranking with live board numbers.
- 🧱 OFF SWITCHES (owner, 2026-10-09, after the −20% floor sold a card with frozen coins at 15:44): card floor OFF and 🛑 trench-coin stop
  OFF are on Edit Fuse's MAIN pane (`floorPct` 0 · `trenchSlPct` 100 = OFF: every ticket — trench drop AND young hand pick — rides or rugs,
  held tickets switch at once, `stop_word`; rug shield still acts; learned stop never overrides OFF). The floor NEVER sells a ❄ frozen coin.
  `_floor_off_fix_1009` set both OFF on the real card (backup data/realcfg_before_flooroff1009.json).
- ⚡ TRENCH TAB = RUSH BOARD on top (`TrenchRush`, `rushScore` / `rushTop`, `trc-*` in quickPulse.css): the 3 cleanest trench coins —
  never a failed scan, a busted / wash / blow-off read, rug ≥ 50 or a > +15% 5-min candle; scan + brain play + heat − rug + live 5-min
  buying + socials. Each card: safety word, 🧠 chip, read, heat / rug bars, the shared `BsBar` (green / red: who is winning, the coin-edge
  record — no new poller) and 📐 `LeanLine` (`leanOf`: 5m, 1h, buyers, pace, heat − rug → −1…+1 drawn as a line; a read, never a forecast),
  one tap ⚡ RUSH IN (swap now). ⇄ HAND SWAP takes clean coins only (`_swap_clean`): the 🏆 Best list first, then no busted / wash / blow-off /
  down-trend read, rug < 50, alive, core clean entry, busiest first — it used to take the biggest 1h pump. 🎯 `pick_from_park`: the owner's
  seat pick draws parked profit at once when EVERY coin is locked (nothing to trim) — $QI waited 2 rounds behind a park.
- 🌊 CARD COIN ROWS = BUYS vs SELLS (owner, 2026-10-09: "green and red bar under each coin, if more red show a little green"): `LegFlow` in
  FuseCard replaces the 5-min heat bar on every Fuse card's live side — green = $ bought, red = $ sold (coin-edge `bs` 5m, else 1h; the
  split IS the share), plus a 📐 lean line (`lib/lean.js` `leanOf`, shared with the Rush board's `LeanLine`).
- ⚡ RUSH MODE (owner, 2026-10-09: "upgrade engine to rush me — I'm trenching and giving the keys, open the door"; real cfg `trenchRush` +
  `trenchEvery` 5/10/15/30, `_rush_fix_1009` → ON every 10 min, SEND-IT-only off): the trench drop takes `_rush_rows()` first = trench-gate
  passes + open-list coins whose scan PASSED, scored by `arena_prime.rush_score` (mirror of `lib/lean.js` `rushScore` — change both; the
  engine version refuses unscanned coins), and may take the seat of ANY coin not making ≥ 10c — the owner's picks included, ❄ frozen /
  riding / house coins never. Why it never rushed before: all 4 seats were owner picks (never trench victims), 30-min cadence, SEND-IT-only.
  Edit Fuse main pane = 1 · setup · 2 · THE CARD (clock, coins, hold, stop, floor, flow exit) · 3 · ⚡ TRENCH RUSH (rush, every, coins,
  ticket, stop, 🏠); the rest live in their section once (Coins › 🗑 TRENCH). The SEND-IT-only row is gone.
- 🚪 Split list v2 (`TrenchOpen`): 🔥 Hot = coins the rush rule would take, by rush score (it led with BOND RUN / EARLY RUSH / BREAKOUT, −84 /
  −64 / −45% an hour); busted reads go to ☠ Avoid; 🆕 Newest has 🧹 Clean (default on: hides failed scans + rush-refused reads, "N hidden");
  every card carries the green / red `BsBar`, a lean line and ⚡ Rush (one-tap pick in the picker). Split CSS lives in trenchSplit.css.
- ⚖ IDLE CASH RESPECTS THE COIN CAP (2026-10-09, 11 wasted swaps in an hour): with one unlocked coin, idle cash (engine `spread_cash(hard=)`
  + keeper `fuse_wallet.idle_sweep` via card `coinCapPct`) lifted it to 66% and `cap_trim` sold it back to 35% ten minutes later, again and
  again ($EVERYTHING, $QUBT). Both now stop at `coin_cap_usd` (`maxCoinPct` / 1.4× a seat); the rest stays card cash. ⚡ Rush never buys a
  pool under `RUSH_MIN_LIQ` $20K (mirror in lib/lean.js) — $Emotional ($14K pool) was pulled 4 minutes after a rush buy.
- 🌊 VOLUME CYCLE (owner, 2026-10-09: "need to be cycling new volume coins"; real cfg `volCycle` + `volEvery` 5/10/15/30, `_volcycle_fix_1009`
  → ON every 10 min; Edit Fuse main pane "3 · 🌊 CYCLE & ⚡ RUSH"): every `volEvery` min a flat coin (`flat_leg(picks=True)`: ±10% after
  max(10 min, its hold) — the owner's picks too, never frozen / riding / house / trench) gives its seat to the busiest coin of
  `arena_prime.vol_cycle_rows` (open-list coins whose scan PASSED, ≥ $50K/h, buyers ≥ 52%, ≥ 6h old with a known age (`VOL_CYCLE_MIN_AGE_H`) and a ≥ $50K pool (`VOL_CYCLE_MIN_LIQ`) — it took a FULL $1.04 seat in $WOTF at ~30 min old, pulled 5 min later (−97%); brand-new coins are 15% trench tickets ONLY — 0 … +150% on the hour (`VOL_CYCLE_MAX_1H`: its first pick was $WOTF at +130,852% — a launch pump), rush-clean incl. pool ≥ $20K).
  The new leg is the ENGINE's (picked popped, tag '🌊 volume'). Why: the engine's own funnel went 79 safe → 0 buyable and the mover swap was
  off, so flat coins held their seats for good.
- 🧨 `_degen_crazy_fix_1009` (owner: "go degen crazy, get us back to $4"): rush + volume cycle every 5 min, trench tickets 25%, 2 trench coins
  (backup data/realcfg_before_crazy1009.json). ⚡ Rush also skips coins up > `RUSH_MAX_1H` 150% on the hour (mirror in lib/lean.js).
- 🏆 A COIN IN PROFIT KEEPS ITS SEAT (2026-10-09, "still not pushing"): the trench drop's victim rule was "making ≤ 10c" — on a $1.50 card a
  +17% coin makes 6c, so $OMNI (+16.9%) and $swordcat (+2.5%) were sold for trench tickets. Victims now also need gain ≤ `TRENCH_VICTIM_PCT`
  +3%; the volume cycle's "flat" is −10 … +3% (`FLAT_UP_MAX`). On a small card, judge a coin by %, never by cents.
- 🤖 THE AGENT DESK (owner, 2026-10-09: "code your own agents to learn trading + trenching — one tracks numbers, one knows why they moved,
  one knows when to enter, one argues it; none can work without the others; conquer the 5 min first; their own HQ tab";
  `backend/agents.py` pure + tested; `_agents_tick` a pass a minute in `_fuse_warm`, `data/agents.json`; owner `GET|POST /admin/agents`;
  HQ › Core › 🤖 Agents = `command/AgentDesk.jsx` + `styles/agentDesk.css` `agd-*`): ONE chain over the open list's 80 busiest coins —
  📊 Tally (its own per-coin tape: 5-min move, volume pace, buyers, pool change, holders) → 🔍 Sherlock (drivers, each weighted by what it
  was REALLY followed by over 5 min once judged 8×, else a prior) → ⏱ Trigger (ENTER / WAIT / SKIP; never a +15% candle, a −8% fall, a
  < $20K pool or a failed scan; its bar 1.0–2.5 moves with its own record) → ⚖ Devil (objects with evidence: busted read, rug, already ran,
  < 15 min old, unscanned, negative drivers, drivers losing lately, Trigger losing). GO = enter AND agree. Every ENTER + 3 WAIT controls
  are judged at 5 / 15 / 60 min (no price at 60 = −100%); each agent has its own card; the team's $20 paper desk ($5 a GO, out at 5 min).
  Stage: 5 min is conquered at ≥ 30 judged GO, median > 0, ≥ 55% won → 15 → 60. Real cfg `agentFeed` (owner switch on the tab): GO coins
  go FIRST in the rush (`_agents_go_rows`, trench tickets) ONLY while 5 min is conquered. Creator-only (`_require_owner`). Never a promise.
- 🤖 Agent desk v2 (owner: "live info on their thoughts + how close to real money; 10× to pass 5 min; then a real-money test on MY Fuse card"):
  the paper desk is TRENCH style — each GO = 25% of the desk (`DESK_PCT`, compounds), under $1 = 💥 bust → a new $20 run (busts counted);
  the 5-min stage passes ONLY at 10× in one run (`PROVE_X`) with ≥ 30 judged GO calls. 🛣 `agents.road` → `RoadMeter`: paper 10× → 💵 the
  real test on the owner's card (`_agents_real` = real_learn pieces tagged `tag:🤖`, ≥ 10 closed, typical > 0) → 15 → 60. 🗯 `thoughts` (each
  agent's words on every ENTER, else the 2 strongest leans) + `results` (5-min verdicts, "Devil was right / wrong") → `state.feed` (80) →
  `ThoughtFeed`. `_agent_test_fix_1009` switched `agentFeed` ON (owner's order) — it does nothing until the 10×. `settle` copies each call
  (it mutated the caller's dict, so before/after compared equal). Dollar-named tickers never reach the desk.
- 🤖 Swap-in 🤖 Agents list (`AGENT_LENS`, `agentPool`, `AgentChip` `sp-agent`; only where the picker has an admin `call` — the real card's
  pickers): the desk's live table as pickable rows, GO first, each with the four agents' words in the chip tip. `GET /admin/agents` is any
  admin (role-scoped admins are refused by `_role_gate`); POST (the real-card feed) stays creator-only. 🪑 Empty seats fill from the volume
  list too (`seatFallback` gets `vol_cycle_rows` first when `volCycle` is on): the cycle only ever REPLACED a flat coin, and the engine's own
  funnel often ends at 0 — a card sat on 2 of 4 coins with $0.33 idle.
- 🤖 AGENT ALERT on My cards (owner: "on-screen noti when an agent found a good coin, one click to fill / see / sub"; `AgentAlert` +
  `agentAlerts` / `weakestSeat` in ArenaPrime, `aga-*` in quickPulse.css, portal top-right, ≤ 2 at once): polls `/admin/agents` every 20s;
  a 🟢 GO coin not on the card pops ONCE (localStorage `feeless.agentSeen`, 1h) with Sherlock's reasons, Tally's numbers, Devil's verdict and
  🪑 Fill seat (empty seat) · ⇄ Swap now (default = weakest swappable coin, select to change; never frozen / riding / buying) · 👀 See. Same
  `fillSeat` / `pickSwap` path as Best 3 — every check and warning still applies.
- 🧠 TRENCH MIND (`backend/trench_mind.py` pure + tested; owner: "agents must understand HUMAN trenching — lingo, narratives, dip tuggers,
  botted launches, learn on their own from Pump, real analysis, humor"): seed `SLANG` dictionary + `learn_lingo` (new words from Pump
  callers' own thesis text: ≥ 6× on ≥ 2 days, copy-paste swarm lines counted once a day, `data/trench_lingo.json`) · `NARRATIVES` (name /
  ticker → AI, dog, cat, frog, politics, celeb, stock, season, food, game, money) + `hot_narratives` · `crowd` (callers, real vs `swarm` =
  ≥ 50% the same line or template, slang used, hype vs fear words) · `bots` (organic < 5%, ≥ 3 bundles, ≥ 8 snipers, wash read, micro-buys) ·
  `dip_tug` (dumped, buyers still ≥ 50%). `read` → drivers `narr:<k>` / `narr_hot` / `crowd_real` / `swarm` / `botted` / `tug` on Sherlock
  (judged on the 5-min record like every driver — it LEARNS which narratives / crowds pay); Devil objects to a swarm or a botted launch
  (≥ 40). `analysis` = a written brief (a clause only when its evidence exists) + one line of each agent's humor (`QUIPS`, picked by
  situation, stable per coin). HQ › Agents: `MindBox` (hot narratives, learned slang, swarms caught, calls read) + the brief under each
  table row; the thought feed carries the jokes + a ✍ desk line. No AI model key is set — the writing is the engine's own, from evidence.
- 🤖 Agent desk v3 (owner: "true opinion from learned behavior, no default feeling · agent picks stay on card until profit, then the agents
  pull or swap · agent controls in HQ · meme strats · ideas up for review · live working box · REAL war, no fake entertainment"):
  · `agents.weights` = (n × record + 8 × starting belief) / (n + 8) — no fixed feeling; `learned_share` → every `opinion` says how much of
    it is the record ("31% of this read is our own record"). `STRATS` (first dip after bonding · curve push · narrative rotation · CTO
    revival · volume burst · real callers stacking · clean dip catch) = drivers `strat:<k>` with NO belief — only their record weighs.
  · 💡 `ideas` (two drivers together on ≥ 10 judged ENTER calls: ≥ +3% typical & 55% up → take; ≤ −5% → avoid; never proposed twice) →
    the feed + IdeaBox; creator `review` approve / reject (POST /admin/agents {idea}); approved take = driver `idea:<id>`, approved avoid =
    Devil objects.
  · 💵 AGENT SEATS (`arena_prime.agent_leg` = bought tag '🤖…'): no stop (slMode hold + rideOrRug), never a rotation / volume-cycle /
    trench-drop victim; `agents.manage` each tick while the desk feeds the card: under `agentTakePct` → hold; in profit → still clean (not
    SKIP, lean ≥ 0, 5m ≥ −3%, buyers ≥ 50%) = run, else `agentMode` auto/swap → a fresh GO runner (replace_leg, tagged), else pull
    (`sell_leg_to_cash`: profit held as cash, seat left open); off the desk's list → pull. Never more than `agentSeats` agent coins.
    realCfg `agentTakePct` 5/10/20/30/50 · `agentMode` auto/pull/swap · `agentSeats` 1–4 (POST /admin/agents {cfg}, creator only).
  · HQ tab: each agent card has its live task (`agents.tasks`) + a working scan bar; every coin row shows its vitals (`vitalCells`: cap,
    age, pool, 1h vol, buys, top-10, bundles, snipers, organic, rug, scan — bad ones pink) + the 🗣 opinion + 🎯 strategies it fits;
    `AgentControls` (+ the live seat decisions) and `IdeaBox`.
- 🤖 Agent desk v4 (owner: "approve ideas at 15+ · aim at new coins too · crawl multiple ends like that AI spider, only for trenching ·
  ethics engraved: they never know their beginning, they learn to survive or be scrapped"):
  · 🕸 THE CRAWL (`agents.SOURCES`, service `_agents_tick`): each pass = the 80 busiest open-list coins + the 40 NEWEST launches (≤ 1h,
    `AGENTS_NEW`), every coin tagged with every corner it showed up in (`_lens_rows`: Pump trending / live, movers, volume, fed, waves,
    cooling, proven callers, before-the-break, double · Pump callouts · open · new) → drivers `src:<k>` with NO belief (record only).
  · 📜 `agents.CREED` (shown in HQ › Agents › The creed): no memory of their making, survive by record, never sign / send / hold a key,
    the creator's card only after the paper 10×, never promise, warn never block, never shill, bots are noise, every opinion says what is
    earned. The hard lines are enforced by the existing code paths (keeper signs, `agentFeed` + stage gate, `_require_owner`), not trusted.
  · ⚔ SURVIVE OR BE SCRAPPED (`survival` / `evolve`, state `born` / `gen` / `lineage`): each agent learns only from its CURRENT life's calls;
    ≥ 30 calls under 45% right (Trigger: losing median & < 45% won) → probation; ≥ 60 → scrapped NOW and reborn as the next generation
    (its learning starts from belief; the last life goes to the lineage; a ☠ line in the feed). Team / control cards keep all history.
  · 💡 ideas: proposed at 10 calls, `IDEA_APPROVE_N` 15 to approve (`review` refuses earlier; waiting ideas keep counting, `ready`).
- 💧 A COIN IS WORTH WHAT SELLING PAYS (2026-10-09: the real card read IN CARD NOW $32.37 / +$7.39 all-time while the wallet held < $3 —
  $QI's pool was drained, every sell quote 92–99% impact, the one fill paid $0.016, but Jupiter's price × the leftover units counted ~$32):
  every keeper sell quote (refused or filled) is kept on the book as `sellQuote[mint]` = $ per unit (`fuse_wallet.note_sell_quote`; a
  "no route" = 0), and `book_value` / `leg_px` value a held coin at min(market price, a ≤ 30-min-old sell quote). The wallet was never
  short — it was a valuation bug; the payout rule (above put-in) could have paid out phantom profit. "CARD UP A LOT FOR NO REASON" ⇒
  compare the coin rows' sum with IN CARD NOW and read the keeper's refused sells.
- 🤖 Agent desk v5: ⚠ the live `desk()` passed EMPTY learning (`st.get('learned')` was never set) — learned weights, Trigger's bar and approved
  ideas only ever worked in tests. Now `learn(st, 5)` every pass. Added: `regime` (share of coins green over 5 min → Trigger's bar cold +0.5 /
  hot −0.25) · `burn` (a GO that lost ≥ 20% at 5 min → Devil refuses that coin 6h) · per-agent real ms per pass (`perf`) · calibration (lean
  bucket → 5-min result) · source budget (`cut`: a `src:` driver with ≥ 50 calls and a losing median → the crawl keeps half of those coins) ·
  `second_opinion` (one call > 50% of a life's losses = a rug → spared ONCE per generation) · `lesson` (a death's worst drivers → the reborn
  Sherlock's starting beliefs; Trigger +0.5 bar per death ≤ 1.5) · `war_log` → owner `GET /admin/agents/log` (Markdown, ⬇ War log).
  HQ: `WorkFloor` (Tally's dots = coins read, Sherlock's tags = reasons weighed, Trigger's ⌖ = real ENTERs, Devil's ✓/✕ = real verdicts,
  re-keyed per pass, ms per lane) · `Tanks` (next generation in water; level = real danger from status + calls vs the scrap line; the lesson
  it inherits on the glass) · `Edge` (calibration · regime · burned · cut sources).
- 🩸 A DRAINED POOL NEVER JAMS THE KEEPER (2026-10-09: every $5 $QI sell refused at 99% impact; the SELL-BEFORE-BUY barrier then blocked EVERY
  buy for 30+ min → "buy never landed in 2 min", empty seats, "New coins: 75 safe → 0 buyable"): `note_sell_quote` keeps the quote's impact;
  `fuse_wallet.write_off_drained` (each sell pass, before the barrier) writes off an OFF-CARD coin whose fresh quote says the whole holding
  sells for < $0.05 or the route is ≥ 90% impact (ledger `writeoff` "drained pool"; coins stay in the wallet). The recovery panel values off-card
  coins with `leg_px` (it showed "$0.39 → $31.54 · 8042%") and neither the recovery list nor repair-sell-all re-books a written-off coin.
  "BUYS NEVER LAND" ⇒ read the ledger for a sell refused over and over first.
- 🤖 Agent desk v6: 🎓 LEARNING SEAT (real cfg `agentLearn` + `agentLearnPct` 5/10/15, `_agent_learn_fix_1009` → ON at 10%; owner: "they do it on
  the Fuse wallet's real card to learn before I fund them"): before the paper 10×, `_agents_go_rows(learn=True)` hands the rush ONE GO coin at a
  time with `stakePct` (the trench drop uses it as the ticket); `agents.manage` runs for it too. 🩸 `manage` pulls an agent coin at ONCE (profit
  or not) when its pool falls under half its entry depth (`DRAIN_PULL`). 🔬 `autopsy` (each judged call ≤ −50% at 5 min or vanished at 60):
  what was read / missed → `rugSigns` counts; Devil objects to 2+ reasons each seen in ≥ 3 rugs. 📈 `history` (every 30 min, a week) → each
  agent's line per life. 📏 `rules(learned)` = each agent's ACTUAL rules from the constants + the live record (never hand-copied text).
  🛰 `command/AgentRoom.jsx` + `styles/agentRoom.css` `agr-*` (top of HQ › Agents): four stations (live task, gen, life; the ring turns at the
  agent's real ms — `spinSec`), the pass's real coins travel the chain as packets coloured by how they ended (`packetsOf`), click a station →
  `AgentDetail` (task · rules · last rulings · record · history spark · inherited lesson), ⤢ Pop out = full-screen portal (Esc / ✕).
  `.agr` is an fxPause surface; fx-lite / reduced motion lay the packets out still.
- 🤖 THE AGENTS' OWN SEAT IS A WHOLE SEAT (owner, 2026-10-09: "they run 1 whole seat and suggest for the other 3"): `agentLearnPct` options
  100 (default = whole seat: the trench drop gives the agent coin the victim's full money, no `ticket` flag, still held until profit / pulled on a
  drain) · 15 / 10 / 5 % tickets. `_agent_seat_fix_1009` set the real card to 100 (old value data/realcfg_before_agentseat.json). 🤝 A coin the
  owner takes from the agents' My-cards alert carries `via: 'agents'` → tag '🤝 agents suggested · your pick' → `_agents_real().suggested` (its own
  record, shown under the Road meter); it is the OWNER's seat (not `agent_leg`, normal stops).
- 🏢 AGENT OFFICE (`AgentRoom.jsx` rewritten, `agentRoom.css`): one SVG cartoon office — four robots (Tally specs · Sherlock deerstalker +
  magnifier · Trigger headset · Devil horns + gavel) typing at the speed of their real ms, speech bubble = live task, monitor = real output
  (`screensOf`: Tally's bars = 5-min moves read · Sherlock's top reasons · Trigger's ENTER scope · Devil's docket), the tube carries the pass's
  coins as stamped slips to a → CARD tray / shredder, wall board = coins read · GO · market green %, status on the robot (⚠ sweat, ☠ X eyes).
  SVG TEXT IS `T` (createElement, never `<text>{expr}</text>`): the dev server's visual-edits babel plugin wraps a JSX `{expr}` in a <span>, which
  SVG can't draw — every dynamic label would vanish on the dev server. Never CSS-animate a <g> that has a transform attribute.
- 🧊 THE OFFICE IS 3D (owner: "3D, no 2D kiddy look, a little realism"): `command/AgentOffice3D.jsx` (lazy chunk, three.js from node_modules —
  never in the app bundle) = WebGL room (RoomEnvironment PBR, ACES, one shadow key light, glossy clearcoat robots built from primitives,
  canvas-texture monitors / wall board / desk plates redrawn on each pass, glass tube with stamped coin slips, HTML speech bubbles projected
  per frame), click = raycast → select. Loop stops off-screen / while the inline copy sits under the pop-out; hidden tab, fx-lite and reduced
  motion get a STILL frame every 1–2s (never blank). `has3D()` false (jsdom, no GPU) → the SVG office. Canvas size = its box (pop-out taller).
- 🤖 Agent desk v7 = META LAYOUT (owner, 2026-10-10: "cleaner, more interactive, meta all throughout"; `AgentDesk.jsx`, `agentDesk.css` rewritten on
  m-* tokens, `--ag` = the agent's colour, `--agd-up` green that flips in day): hero (`PassClock`: age + bar to the next pass, re-reads when it is
  due; GET is served from memory, no rate limit) → 7 KPI tiles (`kpi-*`, each jumps to its lens) → office (🏢 on / off, remembered) → the four
  agents as ONE picker (`agent-<k>` buttons with a right-% ring; drives the office via `AgentRoom sel / onSel / picker`, the feed filter and the
  highlighted pip) → ONE lens (`LENSES`, `feeless.agentLens`): 🟢 Live (work floor · coin board · thought feed) · 🧠 Learning · ⚔ Survival ·
  ⚙ Control. `lens="all"` stacks them (tests only). COIN BOARD = one line per coin: 5m · four pips (`pipsOf`) · lean vs Trigger's bar
  (`leanFill`) · verdict (`rowState`) · the ONE fact that decided it (`rowWhy`); filter seg with counts (`boardCounts`), search, sort
  (`boardRows`); a row opens every agent's word + vitals + brief + 🪙 coin / 📈 chart / copy CA. A feed line or work-floor mark opens its coin.
  New agent data ⇒ a lens (or a row's body), never a new stacked block. 🤝 `agentTrust` (real cfg, off): a 2nd agent seat once the suggestions
  the owner took are proven (≥ 10 closed, typical > 0). Office = white 3rd-person room (scanner → bots carry sheets → GOOD drawer / shredder).
- 🖥 Agent desk v8 = SCREENS, SEATS, GROWTH (owner, 2026-10-10: "degen complex but simple — click to zoom to see their screens, click through
  lists, less reading, realtime; your own twist on how they grow; them controlling my card rn"; `command/AgentScreens.jsx` + `styles/agentScreens.css`
  `ags-*`, shared row reads in `lib/agentRead.js`): each agent card = header (pick) + a MINI SCREEN that is its work this pass, drawn — 📊 Tally
  heat wall · 🔍 Sherlock reason bars · ⏱ Trigger scope (x 5-min move, y lean, dashed line = its bar) · ⚖ Devil docket of stamped tickets
  (`heat` / `reasonsOf` / `scopeOf` / `docketOf`). Tap → `ZoomScreen` (portal; tabs switch agent; every mark is a coin; ‹ › / ← → walk
  `listFor`; Sherlock: tap a reason → only its coins; Esc closes) with a `Dossier` of METERS (lean vs bar, pace, buyers split, top-10, rug,
  organic) + the four pips + the one deciding fact. 🎮 `CardNow` (always under the KPI tiles) = the real card as seats from `agents.card_seats`
  (set each tier tick in `_prime_tick` → `_agents['card']`; kinds 🤖 agent · 🤝 suggested · 👤 yours · ⚙ engine · ▫ open; an agent seat shows
  its bar to `agentTakePct` + ⏳ / 💰 / ⇄; no price = "—"). 🧬 `agents.growth` (lens 🧬 Growth, `GrowthCards`): XP = calls judged this life;
  `LEVELS` 🥚 0 · 🐣 10 · 🧒 SURVIVE_N · 🦾 SCRAP_N · 🧠 150 · 👑 400; a level is HELD only while alive (probation = stunted to 🐣);
  `earned` = share of its judgement that is its own record (Sherlock: mean n / (n + BELIEF_K) over its drivers); genes = inherited lessons,
  scars = lives lost, skills = ideas the creator approved (take → Sherlock, avoid → Devil). 🪜 `agents.power` / `seat_limit` / `trusted`
  (`TRUST_N` 10) = THE rule `_agents_go_rows` buys by, drawn as three rungs (🎓 learning 1 seat · 🤝 trusted 2 · 🏆 proven `agentSeats`).
  Growth is DISPLAY of rules that already existed — levels never grant a seat or a buy by themselves. New agent visual ⇒ a screen or a
  dossier meter, never a paragraph.
- 👨‍⚖️ Agent desk v9 = THE JUDGE + SEAT CONTROLS + PROOF (owner, 2026-10-10: "a final judge who reviews the good and bad 5 mins after their
  final decision to judge one of the bots … they control seats, truly interactive, able to be degen crazy, prove winners in paper and the
  card seats I allowed"):
  · `agents.ruling / judge` (pure, tested): 5 min after every FINAL call the Judge names ONE bot who called it and / or ONE who takes the L
    (GO win → Sherlock if lean ≥ 2, else Tally if the numbers were up, else Trigger · GO loss → Devil if ≤ −20%, else the same order ·
    objected → Devil vs Trigger); ±3% = no ruling. A WAIT that ran ≥ +10% is a 😴 MISS on Trigger: shown + counted (`missed`), NEVER toward a
    trial (live 2026-10-10: 20+ misses put Trigger on trial and made it PICKIER — the opposite of the fix; the owner's 🔥 dial is that lever). Over the last `JUDGE_LAST` 30 rulings the worst net
    (≤ −2) is ON TRIAL with a handicap applied in `desk()` — Trigger bar +0.5 · Sherlock lean ×0.75 · Devil passes only lean ≥ bar + 0.5 ·
    Tally needs 5 readings — and the best net (≥ +2) wears the 👑. A TRIAL MAY ONLY EVER TIGHTEN (FeeCat's discipline rule); never add a
    reward that loosens a gate. Feed lines `who: 'judge'`.
  · 🎚 `agentDial` (real cfg, `agents.DIALS` chill +0.5 · normal · crazy −0.5 on Trigger's bar via `bar_now`, floor `BAR_FLOOR` 0.75; hero seg
    `dial-*`, `.agd.is-dial-crazy`): the owner's switch. Hard SKIPs (+15% candle, −8% fall, pool < $20K, failed scan) and Devil's objections
    never move with it. `perf.bar` = the bar actually used this pass (`barNow`).
  · 🔥 `agents.stake_pct` (PAPER desk only): next GO's stake = 25% even · 35% after 2 wins · 45% after 3+ · 15% right after a loss
    (`desk.heat / stake / streak`). Never the real card.
  · 🏆 `agents.proof`: W–L + newest-first pips for PAPER (every GO at 5 min) and CARD (`_agents_real().last` = agent coins that left a real
    seat) → `CourtBand` (Judge W–L, 🔨 trial + handicap, 👑, ruling tape — a chip opens its coin) + the 👨‍⚖️ COURT tab in the zoom (`Court`).
  · 🎮 `CardNow` seats are CONTROLS (`seatMoves`): ▫ open → 🤖 fill with a GO coin (`fillSeat via: 'agents'`) · a held seat → ⇄ swap a GO
    coin in (`pickSwap … now`) · their own seat → 💰 Pull (`manualSell` 100). Owner taps through the card's normal paths; a ⚠ 409 comes back
    as "do it anyway" (`ack`). Riding / frozen seats offer no swap. Never add a seat action that skips `/admin/arena/prime`.
- ⚡ Agent desk v10 = DEGEN SCALP + THE MISSION (owner, 2026-10-10: "make sure they learn degen scalping; goal 10× paper, but FIRST get my Fuse
  card back to breakeven fast"): `agents.settle` keeps every call's PATH (its move at each pass for the first 5 min); `scalp_exit / scalp_plan`
  replay every TP × SL (`SCALP_TPS` × `SCALP_SLS`, a take booked AT the line, a stop at what was SEEN) on their own ENTER paths vs holding 5 min;
  `scalp_adopt` adopts a plan only with ≥ `SCALP_N` 20 paths, average > 0 AND > holding (dropped when no longer proven); `record` stamps the
  adopted plan on LATER calls only (`scalp`) and `paper` grades those by it — never a plan on the paths it was picked from. Real card: cfg
  `agentScalp` (on; Control lens) → `manage(.., scalp)` banks an agent seat AT the plan's take line (swap into the next GO, else cash) instead
  of the owner's hold-until line; NO stop is added (agent seats still leave at a loss only via rug shield / drain). 🎯 `agents.mission` (value +
  put-in from `_prime_view` once a pass → `_agents['money']`): BREAKEVEN first (distance + the × it needs), then the paper 10× → `MissionBar`
  (top of the tab) with the ⚡ scalp box (LEARNING n/20 · LIVE TP/SL · avg vs hold · typical peak). 2026-10-10 the card needed ~28× — say the
  distance, never promise it.
- 🔐 KEEP HALF (`arena_prime.half_back`, cfg `keepHalf`, Edit Fuse › Exits; ON for the real card via `_keephalf_fix_1010`, backup
  data/realcfg_before_keephalf1010.json; owner, 2026-10-10: "keep coins and profit going on card while I'm asleep"): a coin NOT locked /
  riding / house yet that peaked ≥ +30% (`HALF_AT`) and is back to half that peak while still ≥ +10% (`HALF_MIN`) banks its PROFIT once
  (`_skim`, stake rides, money follows `skimTo`, leg `halfAt`). The gap under the lock line: $Samur•ai ran +99% → 0% with nothing banked, and a
  ride-or-rug ticket (stop off) skipped even the old "ran +50%, back to +5%" trail. Sells only. On a ~$2 card most such takes are under
  `SKIM_MIN_USD` 5c and simply don't fire — it matters as the card grows.
- 🚨 TRENCH MIN AGE (`arena_prime.trench_age_ok`, cfg `trenchMinAgeH` 0 / 0.5 / 1 / 3, default 1; Edit Fuse › Coins + main pane): on a REAL card the
  engine's trench drop — every door (⚡ rush, 🤖 agents' GO rows (now carry `ageH`), 🎯 pro callers, 🔥 SEND IT, 🧠 brain, the list) — never buys a
  coin younger than that; unknown age = out; owner picks never limited. 2026-10-10 overnight: card $1.77 → $0.40; the ⚡ rush (25% tickets, no
  stop) bought $GTA6 Coin, $Haaland, $Jef minutes old, each pulled ~4 min later ($0.91). The card's own record (`real_learn`): age < 1h = 35
  pieces, median −28%, ALL 7 rugs; 1–6h = 35 pieces, 0 rugs. The owner said "they got me rugged" — the ledger said `by:engine`, tag ⚡, not the
  agents: READ `real_learn` pieces' `k` tags (`tag:` + `by:` + `age:`) before naming who bought a rug.
- 🧪 EDGE AUDIT — THE BIG PICTURE (`scripts/edge-audit.py [cost%]`, read-only; owner, 2026-10-10 after the card went $28.50 → $0.47: "you just do
  small tasks and don't think of the bigger picture"): on 3,098 launch coins watched for an hour and 1,419 agent calls, after a 3% round trip
  (measured: ~1.5% a swap), walk-forward (learn oldest 60%, test newest 40%, vanished = −100%, capped means): hold 1h = −63% typical, 15% up;
  +50 / −30 exits = −28%; coins 12h+ old or $1M+ cap = about −3% (= just the cost); a random coin over 5 min with NO cost = +0.1%, 53% up.
  433 feature / pair rules tested → 0 positive even where they were learned → 0 on unseen coins. The agents' ENTER calls (−4%) did worse than
  their WAITs (−3%). THERE IS NO EDGE IN THE DATA YET: the losses are the cost × the number of swaps + rugs on young coins — no screen, gate
  or agent fixes that. RUN THIS BEFORE building or recommending anything that buys launch coins with real money, and say its result first.
  Real money should follow only a rule that prints ✅ here (positive on coins it was not picked from). ✋ Hold all on My cards = the engine
  stops swapping the real card.
- 🧪 PROOF GATE (`backend/edge_audit.py` pure + tested: `audit / gate / words`; `_proof_gate_tick` hourly in `_fuse_warm` → `data/edge_audit.json`;
  real cfg `proofGate`, Edit Fuse main pane + Safety; ON via `_proof_gate_fix_1010` — owner, 2026-10-10: "fix"): while NO rule passes the audit on
  unseen coins the real card is held (`holdAll` + `holdBy: 'proof'`, chip `prime-proof`): the engine makes NO buy of any kind (rotation, rush,
  cycles, seat refill, agent seats); stops, rug shield, flow exits and profit takes keep running; the owner's own picks still work. The hour a
  rule passes (capped mean AND median > 0 in BOTH the learned 60% and the unseen 40%, ≥ 40 / 25 coins) it releases by itself. Under
  `MIN_COINS` 500 = not judged. A hold the owner set by hand is never lifted; ▶ Release on a proof hold turns the gate OFF (their call).
  Paper cards and the agents keep trading — they are what feeds the record. NEW REAL-MONEY BUY PATHS MUST RESPECT `holdAll`.
- 🎮 AGENT CONTROL of the real card (cfg `agentControl`, HQ › Agents › ⚙ Control, ON via `_agent_control_fix_1010`; owner, 2026-10-10: "the agents
  should have control over my seats and switching coins … allow them real moves on my real money card — GO", said AFTER seeing the edge audit
  read 0 rules positive — their call, said once, not re-argued): the card is held BY THE AGENTS (`holdAll` + `holdBy: 'agents'`, set by
  `_agent_control_set`): every engine door that checks holdAll is off and `tick.best()` returns None for a card held by `proof` / `agents`
  (a stop under a hold used to BUY a replacement). Only the agents buy, in the `_prime_tick` agent block: `agents.manage(control=True)` over
  EVERY coin (never a ❄ frozen one) — bank at the take line (`agent_pull`: free card cash, seat opens) · switch a coin whose read broke
  (off radar / SKIP / lean < 0 / −3% 5m / buyers < 50) for an eligible GO after `CONTROL_HOLD_MIN` 15 min · else hold (never to cash at a loss;
  drain pull stays) — then `arena_prime.agent_seat` fills each empty / reserved seat with an equal share from FREE cash only.
  `agents.eligible` = GO + scan passed + age ≥ `trenchMinAgeH` (unknown = out) + pool ≥ $20K, not on card / burned / cooling / dollar-named.
  ≤ `CONTROL_MOVES_HR` 4 real buys an hour (events `kind: 'agent'`, `move: fill | swap`). An empty seat's cash waits for THEIR coin (engine
  compound + keeper `idle_sweep` gated, card `agentWant`). The proof gate stands aside while it is on; ▶ Release on the card (or the switch)
  turns it off and the gate judges the card again. The owner's own ✋ hold is never taken over. Agents GO rarely — seats in cash is normal.
- 🕙 THE 10-MINUTE DUTY + ❤ LIVES + 🔒 BREAKEVEN LOCK (owner, 2026-10-10: "actively investigating each coin and putting something on the card
  every 10 min … profit and move on … their life depends on winning … they can't get out of 5 min until they win real money back to breakeven …
  they can't switch cycles"): in agent control, `desk()` asks Devil about EVERY non-skipped positive read (`case`), `agents.investigate` builds
  the case files (5 checks: scan · age ≥ `trenchMinAgeH` · pool ≥ $20K · not burned · Devil; `cleared` = all pass — for the duty ONLY Trigger's
  bar is waived, never a safety check) and every `DUTY_SEC` 600s one duty move goes on the card: an empty seat first (`agent_seat`), else
  the seat of a coin whose read broke (≥ 15 min held), else the weakest coin NOT winning (≤ 0%, ≥ `DUTY_ROTATE_MIN` 30 min, its lean ≥
  `DUTY_EDGE` 1.0 under the new one). A full 🟢 GO fills an empty seat at once. ≤ `CONTROL_MOVES_HR` 6 real buys an hour; card `agentDutyAt`.
  In control a coin at the take line is BANKED (never re-read and left to run); real `agentTakePct` 10 (`_agent_duty_fix_1010`). The agents
  only fill / switch / bank coins — they never touch cycles or any card setting. ❤ `agents.reckon`: 9 team lives on REAL exits (win +1, loss
  −1; 0 = all four scrapped + reborn with their lessons). 🔒 `agents.underwater` / `stage`: the 5-min stage cannot be conquered while the real
  card is worth less than put in (`state.money`). Page: `DutyBox` (clock · lives · lock · case files). A winner's seat is never given away.
- ⚖ DEVIL'S BUSTED READS ARE LIVE (`agents.busted_now(call proof, CALL_KEYS)` → `desk(.., busted=)`; ≥ 30 settled, typical ≤ −20%): the fixed
  `BUSTED` list (fallback only) had WASH TRADED / TREND DOWN / DEAD DIP on it while their own records were flat (−0.2% / 47% up, +0.3% / 72% up)
  — with agents in control the duty cleared 0 of 25 coins, 19 on that one false claim. FOUND WITH `data/agents_duty.json` (the duty's case
  files written each pass: `cleared`, each coin's `blocked` reasons): when the agents make no move, read that file first.
- ⚖ SOFT OBJECTIONS ARE RECORD-BACKED (`agents.devil`, `SOFT_MED` −1.0): "botted launch" and "bot swarm" object on belief until their driver
  has `DRIVER_MIN_N` 8 judged calls; after that only while its 5-min record is really negative. Hard objections (live busted read, rug ≥ 50,
  ran > 150% 1h, < 15 min old, never scanned, burned, approved avoid, autopsy rug signs) never soften. 🕵 In control the service requests a
  holder scan for the agents' 2 strongest unscanned cases each pass (`_runner_intel`, deduped) — "holders not scanned" was the other blocker.
- ☠ RUG SIGNS = `agents.rug_lift(judged)`, rebuilt from the record each time (≥ 3 rugs AND rug rate ≥ 2× the base rate, ≥ 8 calls) — never the
  old running counter, which re-counted every rug older than the 60 kept autopsies on EVERY pass ("buyers" read 4,879) and made every common
  reason a "rug sign". Three stacked false objections (fixed busted list → botted on belief → inflated rug signs) are why agents in control
  cleared 0 of 25 coins; each was found by reading `data/agents_duty.json` after the previous fix. A COUNTER FED FROM A TRIMMED LIST RE-COUNTS.
- ⚖ `devil(.., duty=True)`: a duty CASE (`row.case`) is judged on the coin alone — "Trigger's last N calls are losing" objects only to
  Trigger's own ENTERs (the duty waives Trigger's bar, so its streak is not the case's evidence). Every coin-level objection still applies.

- 🏢 THE OFFICE (owner, 2026-10-10: "turn the Agents tab into the control room … every agent REAL CODE + REAL runtime state … no bot art";
  `backend/office.py` pure + tested `tests/test_office.py`; ONLY the creator's real card → HQ › Agents, not the trench tab). Chain:
  Tally → Sherlock → 🌦 Weather → Trigger → Devil → 🛡 Warden → 📮 Courier → ☠ Reaper → 🗄 Archivist → 👨‍⚖️ Judge.
  · `CONSTITUTION` (frozen `MappingProxyType`: role · ideology · ethics · forbidden · hard rules · code file + function names — a test checks
    every named function exists) vs `TUNABLE` (default, lo, hi). A tunable moves ONLY by `propose` (≥ `PROPOSE_N` 10 archived positions) →
    shadow on positions closed AFTER it (`SHADOW_N` 20) → `promote` (must beat live by `SHADOW_MARGIN`); `judge_candidates` runs it for
    Reaper's settings each pass. Nothing else writes `office.tune`.
  · 🌦 `weather` (HOT · NORMAL · CHOP · THIN · HOSTILE from Tally's numbers + our judged calls + courier health) → `desk(weather_fn=)`:
    ONLY `weather_adj` (clamped −0.25 … +1.0) reaches Trigger's bar; hard SKIPs, `BAR_FLOOR`, Devil's objections are not parameters.
  · 🛡 `warden(requested, ctx)` → allowed ≤ requested ALWAYS (W1 execution … W11 smallest order; steps 1 / .75 / .5 / .25 / 0). Wired in
    `_office_warden`: `agent_seat(max_usd=)` (a cap can only shrink a seat) and veto-only on a switch. A Warden failure = the card's own size.
  · 📮 `courier` reads the keeper's ledger (sends nothing): `confirmed` = status filled AND sig. BAD = halt / order > 180s / ≥ 50% of ≥ 3
    sends failed in 15 min / duplicate or unsigned fill. Ledger fills now carry `landSec`. BAD → Warden vetoes, Weather HOSTILE.
  · ☠ `reap` each tier tick (`_office_reap`): R1 pool < half entry · R2 failed scan / rug ≥ 65 · R3 top-10 +10 pts · R4 tape dump · R5 stop
    −30* · R6 the card's take line (NO second sell — `agents.manage` banks it) · R7 trail (peak ≥ +6, gave back half, still ≥ +1.5) · R8
    momentum failed ≥ 15 min* · R9 time* (* agent-owned coins only). `merge_reaper` only turns a desk 'hold' into the EXISTING 'pull' — no
    new action kind, no new sell path. A position that left the card is 'exit requested' until `confirm_exits` finds the filled sell row
    (30 min → filed UNCONFIRMED, no result claimed). THIS ADDS A STOP TO AGENT SEATS (they were ride-or-rug): the owner asked for it.
  · 🗄 `file_case` / `file_position` (`data/agent_archive.json`: ≤ 600 cases, ≤ 300 positions, hash-chained, older fold into `agg` /
    `posAgg`; `verify` counts rewrites) · `patterns` states a line only from 5 records. · 👨‍⚖️ `scorecards` (all ten) + `standing`
    (nothing but 'alive' under `JUDGE_MIN_N` 30; demoted ≥ 60) · `demote` resets an office agent's tunables to defaults.
  · ONE payload (`_office_pass`, once per agent pass; `_office_light` each tier tick, memory only) → `GET /admin/agents/office` AND as
    `office` on `GET /admin/agents` (the page makes ONE request). GET runs nothing (test: 200 polls → 0 scans / quotes / saves / wallet
    calls). `data/agent_office_view.json` = the last payload, for checking without an HQ sign-in. State: `data/agent_office.json`.
  · UI `command/OfficeBoard.jsx` + `styles/officeBoard.css` `ofb-*`: 🏢 Office is the FIRST lens and the default; `OfficeMission` on top
    (put in · value · to breakeven · stage · 🔒 lock · lives · next duty · last real action with the LEDGER's word); the line of ten
    (state + ms + word); ten cards; a card / stage opens its detail under it (11 sections incl. code location). The 3D room is opt-in.
    A component that renders ITSELF in JSX overflows the dev server's babel plugin ("Maximum call stack") — recurse with a plain function.
  · The breakeven lock is untouched: `agents.underwater` = real value < real put-in; `office.mission` is handed it, never recomputes it.
- 📈 CHART INTELLIGENCE in the office (owner, 2026-10-10: "they MUST understand the actual price chart / market structure … no separate
  chart AI"; `backend/chart_intel.py` pure + tested `tests/test_chart_intel.py`). ONE snapshot per coin per pass, shared by every desk
  (`agents.desk(candles=, flows=, charts_out=)` → `_office['charts']`): real 1-minute OHLC from the candles service for the coins ON the
  real card + last pass's 6 strongest cases (`_office_candles`: one request per POOL per pass, 50s cache, `dup` 0 by construction),
  Tally's own tape (closes only — wick features are None, never 0) for every other coin. No desk fetches for itself; the page never does.
  · `snapshot` (returns, swings HH/HL/LH/LL on CLOSES, slope + fit, path efficiency, range position, pullback / recovery, base + breakout
    tries / holds / failures, support = the LAST higher low, squeeze, trend / chop / momentum / extension 0–100 — extension is distance
    above the coin's own trend line, never above an SMA: a steady trend always sits above its SMA) → `classify` (15 states, first rule
    that holds; a breakout state needs a BASE before it or every uptrend reads as "breakout") → `entry_call` (ENTER NOW · WAIT FOR
    PULLBACK / BREAKOUT / CONFIRMATION · SKIP, rules E0–E12) → `objections` (`CHART_RULES`; hard: parabolic, fake breakout, liquidity
    divergence, chop; soft ones stand until their own objection record `learn().objrec` shows they block winners) → `risk` (≤ 1).
    Buy share, green-candle counts or one big candle never decide a state (tests).
  · Trigger: the chart can ONLY make it pickier (enter → wait / skip; never wait → enter). The duty's case file has a 6th check `chart`
    (ENTER NOW required): the duty waives Trigger's BAR, never the moment. Sherlock gets driver `chart:<STATE>` (no belief, record only).
    Warden rule `W12 chart risk`. Chart reading is ON only when the service passes `candles` (tests without it are unchanged).
  · 🛑 STOPS: `stop_for` = gap to support + 2 average candles, −20% each for thin pool / < 6h / degraded execution / unproven structure,
    inside [`STOP_FLOOR` 8, the tunable ceiling `reaper.stopPct` ≤ 40]. `CATASTROPHIC_STOP` 45 is a CONSTANT (rule R5x, every coin Reaper
    watches): not in `TUNABLE`, so nothing can propose, learn or promote it away.
  · 🧾 ENTRY THESIS (`thesis`, written in `_office_warden` the moment a fill is allowed → `_office['theses']` → saved ONCE on the position,
    hash-chained in the archive): structure · Trigger's rule · support · invalidation price · stop · expected / max hold windows · reasons ·
    risks. ☠ `review` each tick: valid (structure in `GOOD`, above invalidation) → at every 5-min checkpoint it EARNS one more window
    (`granted`, ≥ `MIN_WINDOWS` 3 = 15 min, ≤ `MAX_WINDOWS` 12) → "HOLD 5 MORE"; invalid (support broke into a bad structure / liquidity
    failure / failed breakout / downtrend with lower lows) → `R5t` out after 2 min, green (TAKE) or red (EXIT); weak + a lower high while
    green → `R7s` banked; weak with its windows used → `R9 windows used`. No chart this pass = `unknown` = never treated as broken. The
    5-minute STAGE is the learning window, not a sell timer. Positions bought before this have no thesis and keep the older rules.
  · 🎯 `take_info` → payload `take` (base · active · source base | learned · evidence n · result · adopted · rule id); every Reaper report
    carries `decision` + `obeying` (base / learned take · trailing protection · invalidation exit · structure-aware stop · hard safety exit).
  · Learning: calls store the structure read AT the call (`cs`, `ce`) → `structure_record` (median 5 / 15 / 60 min + best window per
    state), "entered too late %", "surrendered N points of peak", real entries per thesis structure; scorecards `chartN` / `chartRight`.
  · UI (same one request): `ChartBox` (state · TREND / CHOP / MOMENTUM / EXTENSION meters · FLOW · LIQUIDITY · TRIGGER · DEVIL · WARDEN ·
    stop · evidence ± · every feature in a fold), `PositionCard` per live coin, `TakeLine`, candle accounting line in the runtime box.
- 🏢 AGENTS TAB = THE CONTROL ROOM (owner, 2026-10-10, built to their preview image; `command/OfficeRoom.jsx` + `styles/officeRoom.css`
  `ofr-*`, tests `OfficeRoom.test.jsx`). Order: 💵 REAL MONEY MISSION header (pass clock · `ticker` · stage · dial · 🏢 room toggle
  `feeless.agentRoom`, on by default · war log) → `OfficeMission bare` tiles → MissionBar → KPI tiles → CardNow → DutyBox → CourtBand →
  ONE lens, bar docked at the BOTTOM (sticky). 🏢 Office lens = `OfficeHQ`: `RoomScene` (wall: sign · the candidate / position on screen
  with ITS candles · pipeline status; ten stations in chain order — CSS bot, two monitors (action word + ms), desk, flow arrows, the
  desk the candidate stands at pulses; the pass's case files `queue`; flow + ticker) | `AgentPanel` (tabs Live decision · Beliefs &
  ethics · Current inputs · Chart intel · Source code; `CandleChart` = the SAME 1-minute rows the agents read with entry / take / stop /
  invalidation / support drawn — a tape is drawn as a LINE, never as candles; chart intelligence grid; last rulings; runtime / files) →
  `Roster` (ten cards: gen · status · runtime line · record · action word) → `details.agd-fold` holding the full `OfficeBoard`.
  The four-desk picker (`agd-chain`) moved into the 🟢 Live lens; the old three.js `AgentRoom` is no longer mounted (files kept).
  Payload adds (same one request): `queue` (each case + the desk it stands at), `currentCase.bars`, positions `path` + `bars`
  (`_office_bars` / `_office_positions`, memory only), `performance.agents[a].series`. The room is DOM + CSS perspective (no WebGL):
  every label is testable text. "Expected move" from the preview is NOT shown — nothing computes one; TAKE / STOP lines stand there.
  SVG labels use `T()` (createElement). `.ofr-room` is an fxPause surface.
- 🏢 AGENTS TAB v12 = THE OFFICE IS THE TAB (owner rejected v11: "not hidden lower down … not a CSS diorama"; this REPLACES the v11 note's
  room + ordering). `AgentDesk` order, nothing folded: header (💵 REAL MONEY MISSION · pass clock · ticker · stage · dial · room toggle ·
  log) → `OfficeMission bare` = ONE row of 8 tiles (incl. LAST REAL ACTION) → `agd-kpis` = ONE strip of 10 chips (🎯 breakeven · 🎮 in
  control · 🕙 duty · 👨‍⚖️ judge · GO · paper · road · trench · ideas · lives; the first four open the old MissionBar / CardNow / DutyBox /
  CourtBand in ONE `agd-drawer`, one at a time) → `OfficeHQ` ALWAYS (not a lens) → lens bar (🟢 Live · 📋 Board · 🧠 · 🧬 · ⚙; default Live).
  `OfficeHQ`: stage ~64% | `AgentPanel` ~36% | `Roster` — `--ofr-h` is MEASURED (`useLayoutEffect`: window height − the stage's top −
  the roster) so room + panel + roster share one view under any shell. THE ROOM IS REAL three.js (`OfficeRoom3D.jsx`, lazy chunk, the
  first office's renderer rebuilt dark for ten desks): it draws ONLY `roomModel(o, sel, coin)` (pure, tested) — stations (bot · monitor
  canvas = action word + `deskLine` · floor ring in the state colour · selection ring), the chain as lit floor segments up to the desk
  the candidate stands at with a travelling pulse, the WALL MONITOR canvas (coin · stage · structure · decision · Warden · Devil · review
  clock ticking · `candleGeom` of the SAME rows the agents read, far levels named at the edge via `off`, tape = a line, no candles =
  said so), sign + pipeline status. HTML station labels are projected per frame (buttons, `desk-<k>`). Camera: Main · Top · Focus desk +
  auto-rotate sweep (real, persisted; shown only with a GPU); FOV follows the stage width (`fovFor`). No WebGL (tests, old GPUs) → the DOM
  `RoomScene` stands in (same testids). Panel Live tab = decision (rule in the label) · 4 tiles · coin chips + review clock · chart ·
  intelligence grid · `rulingsOf` (each desk's decision of this pass, then the feed) · runtime + files. Checking the REAL page without an
  HQ sign-in: the service writes `data/agents_view.json` = exactly what `GET /admin/agents` answers each pass; render `AgentDesk` with a
  read-only `call` on a copy of it (scratch only, never shipped). Measured 2026-10-10 at 1440 × 900 on the live payload: stage 870 × 506,
  roster bottom 885, 0 non-transform animations.
- 🧪 MARKET-DATA TRUTH + THE 2× MISSION (owner, 2026-10-10: "a rendered chart is NOT automatically valid evidence … breakeven is a milestone, not
  graduation"; `backend/market_data.py` pure + tested `tests/test_market_data.py`). `quality(rows, now, ohlc, src, meta, liq, flow)` runs on the
  rows AS FETCHED (nothing dropped first) → state (TRUSTED · USABLE_WITH_CAUTION · SPARSE · STALE · INCONSISTENT · MALFORMED · NO_REAL_CANDLES ·
  NO_VOLUME · NO_LIQUIDITY · UNTRUSTED) + conf 0–100 + every check + provenance (`prov`). `chart_intel.read(.., meta)` calls it FIRST:
  · READ_FAIL (MALFORMED / INCONSISTENT / STALE / UNTRUSTED) → chart state `DATA INVALID` (not in GOOD or BAD): no structure, no `chart:` driver
    for Sherlock, entry `WAIT FOR DATA`, hard Devil objection `data_integrity`, risk 0. It is never called a downtrend / failed breakout.
  · readable but not ENTER-grade (tape = NO_REAL_CANDLES, SPARSE, NO_VOLUME, NO_LIQUIDITY) → structure read + labelled, ENTER NOW → `WAIT FOR
    DATA` (E0d), case-file check `data` fails, risk ≤ 0.5 (Warden `W13 market data`). ENTER-grade = TRUSTED / USABLE_WITH_CAUTION only.
  · ☠ `review`: `q.structOk` false → verdict `unknown` + `degraded` → Reaper rules nothing chart-based (no R5t / R7s / R9), report carries
    `dataDegraded` + "DATA DEGRADED"; R1 pool, R2, R5 stop, R5x, R7 trail are untouched. Thesis + lineage + calls (`dq`, `dqc`) keep the data
    state of the decision; scorecards count acting on bad data as violations (`badData`); `office.contribution` = measured-only mission
    contribution + a `notMeasured` list (no $ per agent is invented).
  WHAT THE FEED REALLY IS (read from :5099, say it this way): "candles" = the provider's 1-min PRICE history (today Jupiter; bars carry a volume
  figure) sharpened with FEELESS-recorded prices (those bars have NO volume: 0.0 = not measured). So per-candle volume is usually PARTIAL →
  most live coins read USABLE_WITH_CAUTION ~88%, TRUSTED needs volume on ≥ 80% of moving bars. 5-min / 1-hour totals = the launch board.
  Trade COUNTS exist only on the 90s tape of coins the service already watches — never shown as volume. "tape" = Tally's one board price a
  pass = RECONSTRUCTED, closes only. Detectors that matter: `alternating` (≥ 6 candles ≥ 2% landing back on the price of two bars before =
  two prices ping-ponging — the owner's "giant alternating candles"), `repeat` / `repeat_range` (≥ 1% ranges only: tiny two-source wiggles
  are normal), `jump`, order / duplicates / future / gaps, flat share. A test saw that alternates two EXACT prices is a broken feed now.
  CONSEQUENCE: a GO / duty clear needs real candles, which are fetched only for held coins + last pass's 6 strongest cases → a new coin
  is at best cleared one pass later; a coin the candles service has no history for is never agent-bought. That is intended (tightening only).
  🎓 STAGE: `agents.real_phase(money)` (RECOVERY < put-in ≤ GROWTH < 2× ≤ GRADUATED; unknown money = locked) — `stage()` needs the existing
  paper rules AND real equity ≥ `GRADUATE_X` 2 × put-in. `office.mission` adds phase / breakevenTarget / doubleTarget / toDouble / nextStage /
  unlock; `agents.mission` key breakeven → double → tenx. Money = `_agents['money']` = the real card's `valueUsd` + `math.putIn` only.
  PAGE (same one request): `DataLine` (OfficeBoard.jsx, `ofb-dq`) under EVERY chart — quality + conf, source, candles label, trades, volume,
  liquidity, updated — visible, never a tooltip; `CandleChart` draws a volume bar ONLY for a bar with its own figure (`ofr-vol`, `ofr-volw`
  says N of M); `TeamTrace` (`ofr-trace`: each desk's answer to its own question → FINAL + WHY) from `queue[].trace`; every queue case
  now carries its own `bars` + `chart` so any candidate can be charted; mission row = 9 tiles; `office.JOBS` = ten jobs. Payload ≈ 110 KB.
- ⚡ OFFICE EDGE PASS (`backend/office_edge.py` pure + tested `tests/test_office_edge.py`; wired into `agents.manage` / `office.reap` / `office.warden` /
  the tier tick / `_office_pass`, all in the ONE `GET /admin/agents` payload: `policy` (+ `controls`) · `ready` · `seat` · `switchEval` · `review` ·
  `launch` · `performance.speed`). Owner, 2026-10-10: "AGENTS CHOOSE must truly allow agent TP/SL/hold/switch decisions inside creator hard limits".
  · 🎛 Per control AGENTS CHOOSE (0 / 'agents') or CREATOR OVERRIDE (realCfg `agentTp` `agentSl` `agentTrail`(+Arm/Pct) `agentMaxHold` `agentSizePct`
    `agentSeatTarget` `agentSwitch` `agentEntry`, `agentAuthority` agents | manual; `POLICY_KEYS`, validated by `clean_cfg`, saved via POST
    /admin/agents `cfg` → realOwnerSet + ladderKeep). TAKE: your line or their LEARNED scalp line is BANKED at the line; the base `agentTakePct`
    under AGENTS CHOOSE is a READ line — at it the agents keep a coin only while its read is clean AND its thesis is not weak / invalid (Reaper
    keeps the trail on it: R6 = PROTECT, R7 banks). This REPLACES "in control a coin at the take line is BANKED" for the base line only.
    Stop / max hold / size are CEILINGS (agents may be tighter); switching mode's hold time binds a broken-read switch too. MANUAL = no fill,
    switch or read-bank; only hard safety exits + YOUR overrides act (manual rotates nothing). The catastrophic −45% is not a policy key.
  · 🔌 RESTART: `ready` = WARMING UP → POSITIONS RECONCILED → MARKET REFILLED → LIVE (2 agent passes on ≥ 10 coins + every held coin priced).
    Until LIVE: no fill, no switch, no read / time / max-hold exit, no seat wake; price, pool, scan / rug exits and a take on price alone still
    act. Reaper's off-radar clock never survives a restart (an `offSince` stamp is dropped while not LIVE; the grace restarts at LIVE).
  · ⇄ `switch_test` = every line evaluated (`lines`); a GREEN coin is never switched (Reaper banks a broken green one). Review marks
    (`mark_review`, POST /admin/agents `review` {key, mark agree | disagree | seen | clear, note}) are display state the office never reads.
  · Missed winners: a level the brain never crossed (`x[level] = None`) is not a time (it read as 0 and said "seen only after the move").
- 🏢 AGENTS TAB v13 (built to the owner's preview image, 2026-10-10): the room is `OfficeRoom3D` = TWO desk rows that SNAKE (Tally → Devil, Warden →
  Judge back) around THE REAL CARD hex platform (seat pedestals: height = % since entry, open seat = its seat state); case files float at the
  desk each stands at (current one under a beam); each desk reacts to its activity word (`activityOf`: SCAN · PASS · WAIT · REVIEW · OBJECT · VETO ·
  SIZED · SUBMITTED · CONFIRMED · PROTECT · TAKE · EXIT · HOLD · LOGGING · JUDGE REVIEW — each read from the payload; a ripple only when the word
  changes); hover = `.or3-tip` with the real word; click bot / monitor / case / seat / wall; cameras Main · Card · Top · Focus. Edge chips
  (`EdgeBand`) live IN the office bar; panel = decision + countdown · tiles · chart + data quality · 5-col intelligence · `PolicyBlock`
  (YOU · AGENTS · IN FORCE) · launch · trace · rulings · files. Lenses + 🎛 Limits (`CreatorLimits`: EXITS / SIZE & SEATS / MOVES, blue AGENTS
  CHOOSE vs gold YOUR OVERRIDE, rules in force per position) · 📝 Review (`ReviewQueue`, non-blocking) · 🔎 Missed (`MissedWinners` +
  `LaunchRecord`). `.ofr-panel` rows are `max-content` — the view tabs had collapsed to 6px. No "expected move" (nothing computes one).
  SEE IT WITHOUT HQ: bundle a scratch harness with webpack's node API (frontend node_modules: babel-preset-react-app, style-loader, a
  `process` shim) rendering `<AgentDesk call={readOnly} />` on `backend/data/agents_view.json` + the edge fixture, serve it via a temporary
  launch.json entry (restore the file at once), and screenshot full-res with the cached Playwright `chrome-headless-shell --headless
  --use-angle=swiftshader --window-size=1440,900 --virtual-time-budget=9000 --screenshot=…` (the Browser pane scales 1440×900 to 800×500).
- 🪑 FOUR LIVE SEATS (`backend/seat_ops.py` pure + tested `tests/test_seat_ops.py`; owner, 2026-10-10 "4/4 seats occupied when valid opportunities exist —
  never a forced trade"): P/L VELOCITY from REAL valuation reads (`_office['vel']`, every tier tick + the fast guard on the shared 20s price cache;
  ACCELERATING · STABLE · STALLING · REVERSING, UNKNOWN until 3 reads over 90s) → REVERSING tightens the trail (R7v, give-back × 0.6); past the
  30-min BASE (`BASE_WINDOWS` 6) a seat is EARNED window by window — only a winner (P/L > 0, accelerating / stable, thesis valid, pool ≥ 75%
  of entry, chart not collapsing, no challenger ahead by the switch margin) → else R9e "no extension earned" (≤ MAX_WINDOWS 12 always).
  SEAT SCORE (hand-set, labelled on the page, RANKS coins that passed every gate — never an entry) → bench (20: ready · near · new · dropped),
  switch = score margin (`SCORE_MARGIN` agents 15 / conservative 25 / aggressive 8, +15 over an accelerating position; a green coin is still
  never switched; a broken read whose P/L is climbing is not switched). Every open seat takes its OWN cleared coin in the same tick (+3
  fallbacks after a veto); Warden W17 `seat_room` (one fill ≤ free ÷ open seats) + W18 chart quality (CLEAN · EARLY · CHOPPY · EXTENDED ·
  UNSTABLE · COLLAPSING · INVALID — EARLY is never COLLAPSING). Seat utilization per seat (occupied · empty: waiting / safety / budget / cash).
  Agent seats: their tape is read every 15s (`_flow_guard` skipped held cards — tape sat 60–160s old) + the rug radar is Reaper's hard R4r.
- 🕸 ONE LIVE INTAKE (`backend/intake.py` pure + tested `tests/test_intake.py`, registry `data/intake_registry.json`): every EXISTING outlet —
  Pump pulse + migrations (the PumpPortal live stream `/api/pump/pulse`, already running; there is NO separate FEELESS RPC new-mint listener),
  the launch board, the runner board, tracked lists, Pump callouts, fed runners, the FEELESS radar, the card — noted per mint (first / last
  seen, first seen per source, the office stamps intake · deep · clear · seat, how its real seat ended). Coins the board does not carry get
  their row from ONE batched Jupiter token read (`INTAKE_JUP` 150, 60s cache). `office_edge.intake` reserves `fresh` (pulse / migr, never
  cooled) + `outlets` slots; a rejected coin with nothing new gives up its seat at the table (busy / listed) and its deep review. Source
  records are CONTEXT — never a gate. Page: Seats view › ONE LIVE INTAKE (new unique mints, per-outlet funnel, latencies).
- 🔁 THE 60s LOOP IS REAL: `_agents_loop` (own task, AGENTS_EVERY 55s) — the agents' pass rode `_fuse_warm`'s dozen builders and ran every ~3
  min. It refreshes the launch board first when it is > 50s old (`_runner_live` shares ONE build in flight) and wakes a tier tick when none
  ran in 30s (a fresh decision per held seat per cycle). Deep review = the bench's top first, 18 + 6 newborns, every pick says why it was due.
- 🧾 PROOF (`social_research.evidence/legal_level`): every claim = an item with URL · fetched-at · title · exact launch mint vs the address the
  source showed · excerpt; legal = NONE · WEAK · PARTIAL from pages the project links (one bounded read), STRONG never claimed (no registry is
  queried); labels are facts (ENTITY FOUND · ENTITY NOT VERIFIED · TERMS FOUND · REGISTRATION NUMBER SHOWN · AUDIT DOCUMENT FOUND) — never
  "legit / official / verified". Devil's identity warning, the Warden's W16 rule and the Archivist's record (`office.evidence_refs`) carry it.
- 🏢 THE ROOM = the owner's target image (2026-10-10), procedural (the repo has NO 3D model files): row 1 Tally → Devil, row 2 Warden · Courier ·
  [THE REAL CARD hex + hologram] · Reaper · Archivist · Judge (both left → right), seated robots at black three-monitor desks (activity ·
  runtime · record) with a green under-glow, glowing flow arrows, neon FEELESS HQ sign (left), candidate + pipeline screens (back), new-coins
  per cycle + switch test (right), restrained bloom (off in fx-lite). Every click = `routePick` in OfficeRoom.jsx (tested). The Seat strip
  (OCCUPANCY · TARGET · BENCH · BUYS LEFT · CASH · OFFICE · KEEPER · EXECUTION + four seat tiles) sits over the room; the ops / cycle lines moved
  into the panel's 🪑 Seats view.
- 🪑 SEATS STAY FULL WITHOUT PASSING A HARD BLOCK (owner, 2026-10-11: "they must keep seats full"; overnight utilization was 7.6%):
  (1) CONTEXT IS NEVER A VETO (`agents.CONTEXT_DRIVERS` src: · band: · soc: · pad: · narr: · strat: · chart: + `fresh` / `narr_hot`, `is_context`):
  `rug_lift`, `rug_signs` and Devil's learned-rug-sign veto skip them — Devil objected to 61 of 79 cases with "rug signs" = "found on callouts ·
  $1M+ cap band · ai narrative". They still weigh in Sherlock's lean on their own record. (2) BEST AVAILABLE (`office_edge.near_ready`,
  `NEAR_PATIENCE_SEC` 90, `NEAR_MIN_SCORE` 40): a seat empty ≥ 90s with NOTHING cleared (no GO, no cleared case) takes the best near-ready
  coin — every safety check passed (scan · age · pool · burn · Devil) and ONLY the entry moment (chart) / ENTER-grade data is open; never
  DATA INVALID, a hard chart objection (risk 0), COLLAPSING / INVALID quality, a failed live check or a seat score < 40. Same fill path
  (`fill_plan` → Warden → `agent_seat`), tag "🤖 agents · best available", HALF a seat at most (Warden W19). The creator's "GO only" entry,
  MANUAL, the hourly buy budget, a halted keeper and Courier BAD all still stop it. Tests: `tests/test_seats_full.py`.
  Near-ready coins get their OWN live check (`live_check(near=True)`): a chase, a fall, a SKIP, invalid data / a hard chart objection or a
  drained pool still fail it — "waiting for confirmation" does not (the plain check fails every not-ENTER-NOW chart, so best-available
  never fired). They are computed even when cleared coins exist (those may fail their live check); a cleared coin waiting on the seat
  timer still beats best-available (`fill_plan` uses near only with no GO and no cleared case).
- ⏳ A SEAT IS "STUCK" ONLY AFTER THE KEEPER HAD A BUY PASS AT IT (`fuse_wallet.stuck_buys(buy_pass_at=)` ← `_FW_BUY_PASS[card]`, stamped when
  `_fw_tick_inner` reaches its buy step): 2026-10-11 the agents seated $UDR + $WOTF in the first tick after a restart, no order was ever
  built, and 55s later both went back to cash as "under the smallest order ($0.13)". The unfundable check now uses the keeper's own floor:
  a coin the wallet does not hold opens its seat down to `NEW_SEAT_MIN` $0.05 (the top-up minimum is for coins already held).
- 🧹 A WRITTEN-OFF COIN STAYS WRITTEN OFF (`fuse_wallet.strays`: the newest keeper row for that mint is a `writeoff` → never re-adopted): Jef / QI /
  Musk looped adopt → refused sell → write-off every 5 minutes (1,799 ledger rows), crowding real fills out of the 2,000-row ledger doc.
- 🧮 THE HOURLY BUY BUDGET COUNTS REAL BUYS (`office_edge.real_buys`, both counters in the tier tick): an agent fill / switch counts when the
  ledger has a FILLED buy of that coin for the card at / after it, or while it may still be landing (≤ `BUY_LAND_SEC` 180s); a seat that went
  back to cash without a buy is not a buy. Swap events now carry the new coin's `mint`. (The two 08:40 seats that never bought used 2 of 6.)
- 🪑 TIME EXITS WAIT FOR A FREE BUY (`office.merge_reaper(.., buys_left)`, `TIME_EXITS` R9 / R9e): with the hourly buy budget used, "windows used /
  no extension earned / time" no longer sells a flat coin to cash while there is no buy to spare after the empty seats (buys left − open seats ≤ 0) (2026-10-11: 15-minute R9 exits
  emptied seats the budget then kept empty for up to an hour). The report carries `deferred`; the seat board reads HOLD with the reason.
  Stops, rug / drain / scan exits, invalidation (R5t), trails, the take line and the creator's max hold (R9c) are never deferred.
- 🤖 BOT LADDER (`chart_intel.ladder`, state 'BOT LADDER' in STATES + BAD; owner, 2026-10-11 on $ROAR: "obviously a wash / rug chart"): on REAL
  candles, ≥ 80% of the moving candles within ±25% of one step (`steps`), minute volume nearly flat (`volCv` 0.02 < spread ≤ 0.5; a figure that
  never changes is a filled value, not judged), both directions (`flips` ≥ 0.3), step 0.05–5%. Measured live: $ROAR / $DOTF (both held by the
  agents at the time) / $CATE / $AORP / $ECHO / $ATFS / $HOTBOT 97–100% steps, spread 0.15–0.30, ~$100–150 a minute; every real chart ≤ 55%
  and ≥ 0.32. → entry SKIP (E0b), hard Devil objection `chart_bot_ladder`, risk 0 (Warden vetoes), seat quality INVALID, Reaper's review
  `invalid` → R5t exit of a held agent coin. A tape (closes only) is never judged — so a best-available fill needs a real-candle read.
- 🪑 NO EMPTY SEAT, 30 SECONDS (owner, same day; this REPLACES "6 real buys an hour" for empty seats): `agents.FILL_MOVES_HR` 24 = a runaway guard
  for EMPTY-seat fills only (`real_buys(moves=('fill',))`, `fill_plan(cap=)`); switches keep `CONTROL_MOVES_HR` 6 (`moves=('swap',)`). Best
  available after `NEAR_PATIENCE_SEC` 30 (was 90); `SEAT_HEARTBEAT_SEC` 25 in `_real_guard_loop` runs a tier tick while an agent seat is empty
  (it is the tick that decides). Time exits defer on fills left − open seats. Strip chip FILLS LEFT. Cost: more round trips (~1.5% each).
- 🧭 THE PHASE DECIDES WHAT THE SEATS HUNT (`seat_ops.universe/universe_pts`, ctx `universe` in `_office_scores`, strip chip HUNTING): under what
  was put in = 'trench' (≤ 6h +12, ≤ 24h +6, ≥ 3 days / established −10) · past breakeven = 'mixed' · ≥ 2× = 'majors' (established ≥ 7d +
  $250K pool +15, < 24h −15). A tilt on the seat score only — every check, the owner's min age and the hard skips stand. In 'trench' the deep
  review gives 10 slots to coins ≤ 6h old (by 5-min volume) and 14 to the bench (was 6 newborns ≤ 20 min + 18), and the holder-scan queue
  (`scan_order(.., universe)`) scans young coins first — first live hour after the tilt every seat still went to 40h–300d coins: young ones
  never cleared "holders not scanned".
  Edge audit the same day: 0 of 477 rules positive after a 3% round trip; < 15 min −79% typical an hour, 1–3h −31%, 12h+ −3%.
- 🔍 ROOM CLOSE-UP + LESS GLOW (`OfficeRoom3D`): click a wall board (candidate · pipeline · limits · new coins · switch test), a desk monitor (frames
  the whole three-screen desk from over the robot) or the card's hologram → the camera eases square in front of it (`zoomTo`, time-based ease
  `1 − e^(−dt·k)`), board / monitor canvases drawn at 2× (`tex(.., sc)`), bar "🔍 … ✕ Back to the room", Esc or a click on empty space ends it,
  a camera button too; desk labels hide meanwhile. Bloom 0.16 / 0.25 / 0.97 (was 0.5 / 0.45 / 0.9), exposure 0.85, every rail / under-glow /
  rug / ring / arrow / holo / beam roughly halved.
- 🪑 A TIME EXIT IS A SWAP (owner: "no seat should be empty, 30 secs to choose what gets swapped"; `merge_reaper(.., buys_left)` is now a COUNT):
  Reaper's R9 / R9e time exits fire only while a fill is free AND a replacement is ready NOW (cleared cases + `near_ready`, after the open
  seats take theirs: `min(fills left, ready) − open seats`), weakest flat coin first; otherwise `deferred` ("no replacement is ready"). Found
  live 2026-10-11 11:17: right after a restart R9 sold four flat coins (+0.5 / +0.1 / −0.1 / −0.7%) into cash and the card sat at 0/4.
  Best available also needs the bot-ladder test to have RUN on the full read (`live_check(near)`: real candles, ≥ `LADDER_MIN` 15 that MOVED
  (`f.stepN`), a measured volume spread): two coins were bought on ONE candle, three more on 93%-flat rows that read BOT LADDER 2 min later.
  `NEAR_MIN_SCORE` 15 on the seat score WITHOUT its phase part: the recovery tilt (−10 on old coins) once pushed the only near-ready coins under
  the old 40 floor and left three seats empty for 10 minutes — the tilt orders coins, it never keeps a seat empty.
- 🪓 NO FLAT CHURN (`office.merge_reaper(.., edge)`, `TIME_CUT_PCT` −3, `SWAP_COST_PCT` 2): a Reaper TIME exit (R9 / R9e) sells only a coin that is
  LOSING ≥ 3% or one a clearly better ready coin beats by the switch margin (`margins_` {mint: (score margin, need)}); a flat coin keeps its
  seat ("a swap costs ~2% round trip"). Found 2026-10-11 (scripts/fuse-report.py 4): 113 swaps in 4h, nearly every coin bought $0.12 and sold a
  cent lighter, realized −$0.11 + fees $0.10 on a $1.28 card — the churn WAS the loss. Stops, rug / dump exits, trails and takes unchanged.
- 👁 THE AGENTS WATCH THE LIVE CHART (owner, 2026-10-11: "watching a live chart we already have, not a snapshot"; `candles_service` `POST
  /api/candles/live` {pairs: {pool: mint}} → `live_merge`, `_live_hist`, `LIVE_HIST_SEC` 600, `LIVE_NEW_BUILDS` 24 / call, 4 at a time):
  `_office_candles` + `_office_candle_refresh` make ONE batched local call for EVERY desk coin (was ≤ 28 single fetches; everything else read
  Tally's one-price-a-pass tape) → the war room's own chart: provider history kept from the last build + FEELESS's live 15s ticks, each pool
  marked watched. History is fetched in the background only when missing / > 10 min old (RPC providers are a daily budget). Mint hints
  only from loopback (a remote caller can't point a pool at another coin). `OFFICE_CANDLE_TTL` 12s. Measured: desk coins on candles 2/24 →
  24/24, entry-grade 17/275 → ~73/142; a flat chart now means the coin really is quiet.
- 🔁 Any confirmed agent exit at a loss → `lostAt` 6h (`office_edge.note_lost`; only the desk's own pull wrote it — DOTF came back 4×) ·
  🏛 `agents.established`: > 7d, pool ≥ $100K, scan failed ONLY on top-10 = scanned (Bonk / SNDK / LIT) · `real_learn.note_closed`: every
  confirmed agent exit is a lesson (95 positions had left 3).
- 🎯 AGENTS = NEW LAUNCHES UNDER $1M (owner, 2026-10-11: "only less than 1mil mc now!!! ONLY" + "still going for the safest coins"; `agents.in_lane` = under `AGENT_MAX_MCAP` $1M AND a known age ≤ `AGENT_MAX_AGE_H` 24h, applied to the desk's rows in `_agents_tick`;
  unknown cap kept, coins on the card kept so their exits run). The tab's board (`agents.view_rows`) = top 24 by verdict + the 24 NEWEST
  launches (≤ 6h) the desk read — the owner saw Pump radar coins and thought the agents missed them; the intake registry showed every one
  taken in within a minute. 👁 Agents tab charts = the FEELESS `PriceChart` (`OfficeRoom.LiveChart`, agents' levels via `fuse.lines`, a new
  optional PriceChart prop) and the 3D wall screen draws `lib/liveCandles.useLiveCandles` (the war room's own 1m candles, every 10s).
- 🪑 SEAT FLOOR (owner, 2026-10-11: "no seat should ever be empty, 30 secs to decide"; `office_edge.floor_ready`, appended to near-ready in the tier
  tick, tag "🤖 agents · seat floor"): after 30s with no GO / cleared / near-ready coin, an empty seat takes the best coin of EVERYTHING the desk
  read in the lane that clears the HARD lines (scan passed · pool ≥ `CONTROL_MIN_LIQ` · rug < 50 · not +150% 1h · no hard Devil objection · Trigger's
  no Trigger skip, chart risk > 0 · chart not invalid / bot ladder / liquidity failure / downtrend / collapsing); live check (≥ 15 moving candles) + Warden
  W19 half seat + keeper still decide. `CONTROL_MIN_LIQ` $20K → $10K and lane legs carry `trench` → the keeper's trench floor ($8K): the lane is
  launches under $1M, whose pools are $10–20K (17 of 30 scan-passed lane coins sat under the old $20K line; the seat floor had 1 coin, now ~9).
- 🪑 SEATS FULL, part 2 (2026-10-11): lane age 24h → 72h (`AGENT_MAX_AGE_H`) · ANY reserved seat (incl. an owner's ✂ sell-all `manualCash`
  slot — its cash is plain card cash) is OPEN for the agents (`agent_seat` replaces it; HeeHaw's held one seat for 2.5h) · the card view carries
  `placeholder` → the face reads "○ seat open", never "⏳ buying…" · the agents' intake rows (newest launches off the board) get Jupiter's holder
  audit (`_jup_judge`, same gates as `_open_scan_judge`, live authority = flagged) — every candidate read "holders not scanned" while the RPC
  scanner queued · Agents tab $/% move live (`lib/agentLive.liveOverlay` on the shared 3s `useLivePrices`, against each position's entry) ·
  `.hq-real .hrt-acts` unpinned under 1180px (the wrapped bar covered the card).
- 💵 ALL CARD CASH WORKS (owner, 2026-10-11: "use all card cash, recycle into the card until breakeven and doubled"): `office.NEAR_SIZE` 1.0 (W19
  no longer halves a best-available / seat-floor fill) · `fuse_wallet.agent_seat(l)` (tag 🤖…) exempts agent coins from the keeper's ticket
  lock, so `idle_sweep` tops them up toward an equal share once every seat is held (banked profit goes straight back in; payouts are already
  impossible under put-in). Young hand-pick tickets stay locked. Top-up "can't add $1": wallet $2.64 = card $0.74 + fee reserve 0.019 SOL
  ($2.11) → $0 free; the reserve is the owner's setting (HQ › Fuse › 👛) — never lowered by an agent.
- 🎞 LIVE CHARTS, REAL TICKS (owner, 2026-10-11: "real time, 30fps, real candle moves, unique FEELESS charts + one vital on all charts"):
  `candles_service` stream re-reads the price ≤ `SWAP_PRICE_AGE` 1s after a real on-chain swap log (idle seconds keep the shared 5s cache —
  the 5s cache was why live candles moved only every 5s); `PriceChart` eases the forming candle's body to each REAL tick at 30fps
  (`lib/tween.tweenClose`, ~350ms, last frame = the tick, wick = true high / low at once, a new bucket finalises the old candle on its real
  close; off in fx-lite / reduced motion). 🫀 `ChartPulse` (`components/terminal/ChartPulse.jsx`, `styles/chartPulse.css` `cpl-*`) on EVERY
  PriceChart: vital grade ring + score + the read that fits + a beat per real trade, from the shared paced `useCoinRead` (no new poller).
  Known: the browser hits lite-api.jup.ag price v3 directly somewhere (21× 429 on one war room) — not fixed yet.
- 🧬 TRENCH META (owner, 2026-10-11: "vitals needed for them to TRENCH META"; `flow.trench_meta` pure + tested, `office_edge.live_check(meta=)`):
  a seat candidate too young for the bot-ladder test (< 15 moving 1-min candles — every launch minutes old failed it, the card sat on 1 coin
  with $2 cash) is judged on its last 5 min of real swaps: ORGANIC (≥ 8 trades, ≥ 6 wallets, top buyer < 45%, same-size < 50%, buys not
  1.5× outsold) takes the seat; BOT / ONE WALLET / DUMPING / THIN are refused with the reason. ≤ 6 tapes a tick via the shared `_flow_fetch`.
  Every later live check (fall, broken chart, pool under half) still runs.
- 🪑 SEAT FLOOR LAST RESORT (`office_edge.floor_ready(last=True)`, `FLOOR_LAST_SEC` 60): a seat still empty after 60s with nothing from the
  seat floor may take a weak read (a "wait", negative lean, a read type with a poor record = warning) — never a +15% spike / −8% fall / thin
  pool / failed scan / bot ladder / rug ≥ 50 / risk-0 chart / downtrend (collapsing); healthiest structure first. Tag "🪑 last resort".
- 👨‍⚖️ THE JUDGE RULES ON REAL MONEY (owner, 2026-10-11: "judge needs to be on somebody's ass — losses and misses studied"): `agents.real_ruling`
  on every agent seat that left the real card (real_learn pieces tagged 🤖, handed in as `state.realPieces` each pass): ≥ +3% win → Tally
  (≤ 10 min) else Sherlock · ≤ −15% → Devil (let a dump through) · other ≤ −3% → Trigger (timing); `REAL_WEIGHT` 2 in the net that picks
  who is ON TRIAL. `miss_study`: waits that ran ≥ +10% grouped by Trigger's own reason (calls now store `tw`) → `judge.missWhy` on the strip.
- 🎯 RANK, DON'T VETO (owner's spec, 2026-10-11; `backend/opportunity.py` pure + tested): every desk coin → `hard_fail` (failed / unread holder
  scan · pool < $10K · cap ≥ $200K · rug ≥ 50 · Devil hard rule · invalid / bot-ladder / liquidity-failure chart · +40% vertical or −15% knife
  5-min candle · no price) = NO; everything else = `score` 0–100 with cited parts → tier A ≥ 65 (full seat) · B ≥ 45 (75%) · C ≥ 25 (50%),
  Warden W19 sizes by `TIER_SIZE` (its own steps). The ranked list replaces the old seat floor / last resort. Devil: a read type's busted
  record is a HARD veto only when ≤ −50% typical (`BUST_HARD`, `busted_now` returns {read: median}), else a STRONG WARNING; "ran > 150%" on a
  coin < 1h old is a warning (launch-to-now). Trigger: a launch < 6h skips only a +40% candle (mature: +15%). Reaper R7s "structure turned"
  never banks a green coin whose P/L is ACCELERATING (the trail protects it). Universe for NEW entries: live cap in (0, $200K)
  (`AGENT_MAX_MCAP`, `trench_band` NEWBORN MICRO … UPPER TRENCH = context); held coins keep running past it; age is never a veto.
- 👨‍⚖️ JUDGE REVIEWS (`backend/judge_review.py` pure + tested; office state `judge.reviews`, payload `court`, UI `JudgeCourt` in the Judge drawer):
  every confirmed agent exit → root cause (rugged · gave_back · collapsing_entry · bad_data · thin_pool · weak_holders · entered_on_wait ·
  held_too_long · variance) · responsible desk · severity · change · "valid decision that lost" vs "bad decision"; wins → why it worked. A cause
  becomes a rule only by repetition: 1 = record · 2 = SHADOW · ≥ 3 in the last 20 reviews = PROMOTED as a ≤ 8-point RANKING penalty
  (`opportunity.judge_hits`) that expires 24h after its last case — never a hard veto; unrelated losses tighten nothing.
- 🕯 ONE PRICE FEED PER CANDLE (2026-10-11, "current candle glitches up and all the way down"): the chart's backup poll ran beside the stream
  and called Jupiter FROM THE BROWSER — on a 429 it fell back to DexScreener's single-pool price, a second feed on the same candle. Now
  `lib/livePrice` reads `GET /api/candles/price/{chain}/{pair}` / `GET /api/candles/prices?mints=` (the stream's own source + cache), the poll
  runs ONLY while the stream is down, and a 15–60s history reload keeps the live forming candle (`lib/tween.mergeLiveBar`). The browser
  NEVER calls lite-api.jup.ag: every price (SOL hints, live price hub, Fuse pages, quick trade) reads `/api/candles/prices?mints=`.
- 🎯 Universe applied BEFORE intake (`ob_` filtered by `in_lane` / held in `_agents_tick`): filtering after intake let $200K+ coins take the
  slots and 26 safe sub-$200K pools never reached the desk (127 read, 125 hard-failed, card empty). `in_lane` = live cap $10K … $200K
  (`AGENT_MIN_MCAP`) with ≥ $1K traded in the hour (`AGENT_MIN_VOL1H`) — owner: "no min starting thresholds, starting mc 10k with vol".
  `CONTROL_MIN_LIQ` = $8K = the keeper's own trench floor (nothing under it is buyable).
- 🛑 STOP BY TIER (`opportunity.TIER_STOP` A 25 · B 18 · C 12, `tier_of_tag` from the leg's 🤖 tag; Reaper takes min(its own stop, the tier's)):
  6h on the real card 2026-10-11 = 54 exits, 18 W / 36 L, −4.25% avg; 9 "bought into a fall" losses at −23…−37% were ~3/4 of the loss
  (Trigger 15 · Reaper 8 · Devil 2 by the Judge). A lower-confidence seat now risks less; exits only ever tighten.
- 🪑 SEATS FULL, PERMANENT (2026-10-11): (1) the Warden never turns shrinking into a veto — a seat cut below the smallest step keeps the
  smallest (only a ×0 rule vetoes); HOSTILE × C-tier had snapped to 0 and vetoed fills. (2) `agents.lane_cap`: the universe is the smallest
  of `LANE_CAPS` ($200K → $1M → $5M) holding `LANE_NEED` 12 BUYABLE coins (scan passed, pool ≥ $8K, volume); sub-$200K ranks +6 first.
  (3) Ranking orders by the raw total (`oppRaw`) — strong coins passed 100 and tied. 💵 SURVIVAL ON REAL MONEY: paper calls can only put an
  agent on probation; the Judge's real-loss reviews pinned on it this life (responsibility ≥ 50) net of its credited real wins → probation
  at 3, scrapped + reborn at 5 (`REAL_PROBATION_N` / `REAL_SCRAP_N`, `state.realReviews` handed in each pass).
- 🪑 Why the seats stayed empty after all that (2026-10-11): the lane's safe coins were on the desk, but (1) most had been OURS and were sold
  at a loss → the 6h `lostAt` block removed them (now a −12 RANKING penalty in `opportunity.rank`, not an exclusion; the 3-round cooldown
  stays) and (2) CHOP charts carried risk 0 → a Warden veto (now `chart_intel.risk` CHOP = 0.25, and `live_check(ranked=True)` lets a
  ranked CHOP coin through — DOWNTREND / FAILED BREAKOUT / LIQUIDITY FAILURE / DISTRIBUTION stay at no size). −15% / +40% 5-min candles stay hard.
- 💀 DEAD COINS + NO STOCK SEATS (owner, 2026-10-11, screenshot of $MRNA flat for 10 min: "no buy / sell in 3–10 min = dead"): Tally keeps
  `nums.v5` (5-min $) + `tx`; `opportunity.dead_now` (< `DEAD_5M_USD` $300 in 5 min, or pace < 0.2 with < $1.5K) = a HARD no for every door
  (`hard_fail`, `agents.eligible`, case check `alive`); a held agent coin dead for ≥ `DEAD_HOLD_MIN` 5 min → Reaper `R11 dead coin`, a SWAP
  exit (`SWAP_EXITS`: fires only while a replacement is ready, exempt from the 🪓 flat-churn rule). `agents.in_lane` refuses `fuse.ALL_MAJORS`
  (the $5M lane widening had seated MRNA / MU xStocks, dead outside US hours). 🕵 Trench brain features `bund:` `snipe:` `ins:` `dev:` `live:`
  — the bad guys' footprint is LEARNED against the +50 / −30 play (record, not a rule). Being "first 10 in" a launch needs a same-block
  sniper = a new execution path (forbidden) and the record says < 15 min launches lose −78% an hour; say that, don't build it.
- 🕵 ADVERSARIAL LAUNCH INTELLIGENCE (owner's spec, 2026-10-11; `backend/launch_intel.py` pure + tested, state `data/launch_intel.json`): public
  on-chain behaviour only, no new scanner. The ONE launch read (`token_intel` → `_launch_facts.early`, same ~25 tx reads, `_early_buy`) now keeps
  the first 25 buyers in order with SOL + supply bought; the 15-min flagged-balance re-read covers them → `early_map` (first 10 / 25 %, largest,
  clustered = same slot / same size / known funder, held now, each wallet HOLD · ADD · PARTIAL SELL · EXIT · DUMP) → `classify` (NORMAL · HEAVY
  SNIPER ACTIVITY · BUNDLED · INSIDER-LIKE CLUSTER · UNKNOWN) · `trend` · `phase` (PRE-FOMO … DISTRIBUTION · COLLAPSE + healthy) · `pressure`
  (early wallets selling on the 90s tape: NONE · WATCH · HIGH) · `rank_band` (≈ holders unless our wallet is in the map). `_li_attach` puts
  `li` on every desk row; `_li_track` (trench pass) notes launches, settles them 1h later → wallet memory (`wclass`: EARLY WINNER · FAST
  DUMPER · RUG-ASSOCIATED · DEV-LINKED, ≥ 3 launches) + `byClass` record. USES: DISTRIBUTION / pressure HIGH = hard no (`hard_fail`, case
  check `fomo`); EARLY / ACCELERATING rank up, CROWD down; a launch class moves the rank ONLY from its own settled record (≥ 20); Warden
  W20 exit risk (HIGH veto · cluster holding ≥ 20% ×0.5 · bundled / watch / dump-record wallet ×0.75); Reaper R4e (HIGH → out) + WATCH
  tightens the trail; positions keep `li` at entry → Judge causes after_distribution · crowd_fomo · bundled_exit + `launchShape` (what
  winners looked like by phase / rank / class). Intake per-source adds win rate · median · rug rate · time to entry. New entries HARD
  $200K (`LANE_CAPS` = (200_000,)); held winners keep running. Being "first 10" needs a same-block sniper (forbidden): the rank is
  RECORDED and judged, never forced. Coins scanned before this have no `early` list — the map fills as new launches are read.
- ⚡ THE CHART DRIVES THE TIMING (owner, 2026-10-11: "the timer should NEVER be the reason we miss the move"; `backend/market_wake.py` pure + tested
  `tests/test_market_wake.py`): the ~60s office pass stays; between passes the 6s fast guard (`_market_wake` in `_real_guard_loop`) reads ONE
  batched local call to the candles service's live price (`_live_px` → `/api/candles/prices`, the same price the charts draw — no new provider
  polling) for the agents' seats + the tier tick's candidates (`_office['watchC']`: price at read + local high of the last 10 live 1m candles).
  Seat: `position_wake` (≥ 2.5% from Reaper's last decision price `decPx` · a new high · a reversal giving back ≥ max(2 pts, 30%) of a ≥ +3% peak
  · crossed below support / invalidation) → the fresh price goes into `_jup_px_cache`, that pool's live candles are marked stale, the tier tick
  runs NOW (≤ 1 wake per seat per 6s). Candidate: `candidate_wake` (≥ 3% since its read · a live breakout ≥ 0.5% over its local high) →
  `_agents['wake']` → the agents' loop (2s sleep) runs the next pass at once (≥ 20s apart). Reaper: `run_state` ACCELERATING · RUNNING ·
  STALLING · REVERSING · BREAKING DOWN (live price AND the live chart's last close under the thesis invalidation); a RUNNER (accelerating /
  running, green) is never sold by a time window (R9 / R9e / R9 time) — only a clearly better challenger takes its seat; a green coin
  BREAKING DOWN is banked at once (`R7b breakdown`). Reports carry `fresh` (price · tape · candle · agent input · decision ages, `stale`) and
  `phase` (`market_phase`: BASE · EARLY MOVE · ACCELERATION · BREAKOUT · RUNNING · DISTRIBUTION · REVERSAL · COLLAPSE); rows carry `mp`.
  UI: PositionCard RUN + FreshLine, OfficePositions WakeLine (payload `wake`). Trail LEVELS are unchanged — only the timing moved.
- 🆕 FRESH TRENCH SELECTION (owner, 2026-10-11, after the audit: of 149 confirmed agent buys the median coin was 48h old, 85 were 1d+ old
  (24% won), the "best available" door made 70 of them (median age 101h, −0.9% avg) and the seat floor 18 (−6.6% avg)). ROOT CAUSE: the
  keeper never bought a coin still on its launch CURVE for an agent seat (only owner picks) — every newborn Pump coin was out of reach — and
  the score rewarded history (deep pool +10, big hourly volume +8, a long chart). Now: `opportunity.FRESH_LADDER` (0–15m +16 · 15–60m +13 ·
  1–3h +10 · 3–6h +6 · 6–12h +2 · 12h+ −10 unless `reawake`), `velocity` ($/min + buys/min over the coin's OWN life, ≤ 60 min) replaces
  absolute volume, liquidity is safety (+4 max), a young coin's short chart is not penalised, a < 15 min coin's 5-min move is judged at
  +100% (its launch), Pump phase (`launch_intel.pump_phase`) + early-wallet pressure (`wallet_pressure`) score in; tiers C ≥ 40 (was 25),
  below = REJECT; best available (`near_ready`) needs an entry score ≥ `NEAR_MIN_ENTRY` 50. Intake: `office_edge.stale_old` keeps 12h+ coins
  that are not waking up off every slot but recheck / outlets (callouts) / listed (re-entered a ranking); slots ordered by `fresh_key`.
  Deep review 12 cases + 12 newborns (≤ 12h, freshness ladder first), cases sorted fresh-first; holder scans `scan_order` fresh-first in
  every phase; candle requests `candle_order` (fresh 0–12h first, held LAST — the candles service builds histories in request order).
  🎢 `agentCurve` (realCfg, OFF by default, HQ › Agents › ⚙ Control): an agent seat may buy a curve coin (leg + order `curve` →
  `live_buy_market` uses the curve depth); every keeper check still runs. Judge: `lossClass` BAD ENTRY · BAD TIMING · BAD HOLD · BAD EXIT ·
  NORMAL LOSS + causes `too_old` / `fallback_entry`. Pipeline per cycle = `cycle.fresh` (`office_edge.fresh_view`) → `FreshBlock` in the
  Seats view; intake sources add median P/L · rug % · hold · age + MC at entry · age first seen. 1-second charts: NOT available (providers
  start at 1m; per-second data for 30–80 desk coins = reading every swap from RPC — the rate-limit hole).
- 🗂 ONE ACTIVE CANDIDATE INDEX + FRESH-FIRST STORES (owner, 2026-10-11): every desk already reads THIS pass's desk row; `office_edge.active_index`
  (payload `index`, `ActiveIndex` in the Seats view) lists it per mint (first / last seen, launch age, fresh bucket, live MC, pool, 5-min $,
  volume / buyer velocity, sources, launchpad, real candles, holder state, chart quality, market phase, social, last change / review,
  cooldown) with `eligible` RECOMPUTED every pass from `opportunity.hard_fail` — no cached eligibility anywhere. Stale stores: 12h+ coins that
  are not waking up get no automatic recheck from last pass's cases / bench, and a 12h+ reject cools `STALE_COOL_MULT` 3× longer
  (`review_due` reads the snapshot's age). DEAD HOLDINGS: Reaper reads `run` RUNNING · HEALTHY · STALLING · REVERSING · BREAKING DOWN · DEAD;
  dead (no trades / off their radar) → `R11` swap as soon as a replacement clears, and after `DEAD_CASH_MIN` 15 min dead → `R11x dead coin →
  cash` with NO replacement needed; a red coin under its invalidation in a bad structure already leaves by `R5t` (no replacement needed).
  A degraded chart never decides a chart-based exit (R7b guard). RPC: payload `rpc` = keyed lanes (provider + in / out of quota, no URL) →
  `RpcLanes`. RPC lanes are NOT a discovery source: no RPC first-seen listener exists — new mints come from Pump's live stream + the
  boards. A new Helius key cannot do holder scans (free plan refuses getTokenLargestAccounts, −32600); `HELIUS_RPC_URL` = the Helius-only data key.
- 🧪 AGENTS' OWN HOLDER LINE + 🎢 CURVE ON + 📡 PER-METHOD REFUSAL (owner, 2026-10-11: "seats not filled means they too strict"; at the time 41 of
  43 candidates were hard NOs: holder scan 17 · no pool (curve coins) 11 · dead 9): `agents.agent_holder_pass` — a row the scan failed ONLY on
  the concentration gates ('Top 10 under' · 'Snipers/bundlers under' · 'Dev holds under') passes the agents' lane inside top-10 < 40% ·
  insiders < 20% · ≤ 4 bundled · dev < 10% (numbers read; unread fails closed) as `holderSoft` → Warden W21 half seat. A flagged creator, dev
  selling, a top-10 spike, mayhem, live authority stay hard NOs; the engine's runner gates are untouched. `_curve_fix_1011` switched
  `agentCurve` ON (old value data/realcfg_before_curve1011.json). RPC: a node that refuses ONE method (403 / −32600 / −32601 / −16500 — free
  plans without getTokenLargestAccounts: Helius free, OnFinality, Tatum) skips that method for an hour (`chain_rpc._unsupported`) and stays
  in the pool for everything else — a 403 used to rest the whole node 30s on every holder scan. Holder scans: only Alchemy answers them
  (2026-10-11); Jupiter's audit stands in for unscanned coins.
- ⚡ AGENTS 3× FASTER (owner, 2026-10-11: "seats never empty — agents must work 3× as fast"; all 4 seats sat empty with 2 ranked coins, HW2
  refused "+16.5% since the read" on a 55s-old read): `AGENTS_EVERY` 18s (a pass takes ~2s; the runner board refreshes on the same clock),
  `SEAT_HEARTBEAT_SEC` 8, `NEAR_PATIENCE_SEC` 10, `SEAT_TARGET_AUTO` 10, `market_wake.GAP_CAND` 8, `FILL_MOVES_HR` 36 (switches keep 6). No
  new provider polling: Jupiter / candles / DexScreener keep their caches + pacing. The real choke is SUPPLY (40 in lane, 34 hard NOs: holder
  scan 14 · dead 11) — speed gets the ones that clear seated before they move.
- 🚫 THE AGENTS NEVER BUY BACK WHAT THEY JUST LEFT (`arena_prime.agent_pull` stamps card `agentOut`; `agent_out(card, now)` joins `cool` in
  the agent block): any agent exit = out 10 min (`AGENT_OUT_SEC`), a rug / drain / dump / failed-scan / catastrophic exit (`AGENT_OUT_RULES`
  R1 R2 R4 R4r R4e R5x, or "rug / drain / pulled" in the reason) = out 6h. Found the first minutes of the 3× clock: $Rupshld filled → rug
  radar → filled again, 3 real buys in 60s, then its pool was pulled (−$0.14). agent_pull wrote no cool stamp at all.
- 🚫 THE CHART'S OWN "NO" HOLDS FOR EVERY DOOR (`office_edge.LOSING_ENTRIES` E2 no chasing · E3 too violent, in `live_check`): best available /
  ranked / seat-floor fills waived the entry moment and bought them — real record 2026-10-11 (173 agent exits): E2 median −16.8%, E3 −13.2%,
  11 of the 26 stop-outs; ENTER NOW entries ≈ flat. Reaper's −400% on the roster was a SUM of % (now the average per exit): R5 stops were
  −485 of the −370 total, everything else ≈ +115 — the entries lose, not the exits.
- ☠⚡ FAST REAP (`office.fast_reap`, in `_real_guard_loop` every 6s): agent seats carry no card stop and the card is `holdAll` by the agents,
  so `arena_prime.fast_stop` NEVER ran for them — stops at −12…−25% filled at −18…−52%. Reaper stamps `stopNow` on each position every tick;
  the guard pulls an agent coin at that line (or −45%) via `agent_pull` → keeper → tick. Feed-gap rule (> 50% in the first 90s) as fast_stop.
- 🚫 `_agent_blocked(card, now)` = THE one list of coins the agents may not buy right now: `arena_prime.agent_out` (just left: 10 min / danger
  6h) + `fuse_wallet.no_buy` (benched, or refused by a safety check ≤ 2 min — no route back, sell-back tax, price gap) on every book. Used for
  the candidate cool set AND re-checked in the fill loop. New "don't buy this" source ⇒ add it there, never a third inline set.
- 📉 FALLING = NO (`opportunity.FALL_HARD` −8, was −15): a coin down ≥ 8% in 5 min is a hard no for every new agent entry (it scored a −20
  "falling" penalty and could still rank C-tier: $Squeeze stopped −38% one minute after the buy, $STRKT −6% in two).
- 🧠 REAL-MONEY MEMORY (owner, 2026-10-12: "learn from all real money losses and go again — paper won't prove it"; `backend/real_memory.py`
  pure + tested, `_real_mem` rebuilt each minute from the archive's confirmed real exits): entry features (chart structure · the chart's entry
  rule · door / tier · launch phase · class · age) → shrunk median real result per bucket; a candidate whose WORST bucket is ≥ 3 points under
  the card's typical real trade is not bought (filtered from GO / cleared / best-available before `fill_plan`, reasons in `live.memory`). Used
  only while it beats its own skips walk-forward (oldest 60% learn, newest 40% judged). 2026-10-12: kept 29 of 106 unseen real trades at
  +1.2% avg vs skipped 77 at −3.8% (worst: PARABOLIC −10, E3 −10, E2 −7, C-tier −3). `MemoryLine` under Reaper's take line.
- ⚡ AGENT BUYS COST LESS (`fuse_wallet.AGENT_PRICE_GAP_PCT` 2.5 / `AGENT_ROUNDTRIP_PCT` 3.5 for orders flagged `agent` = leg tag 🤖): 261 real
  agent buys in 24h filled 1.0% over mid (p90 4.5%) and sold straight back 2.3% lower — every scalp started −2…−3%. Engine coins keep 5 / 6.
- 📄 EMERGENCY EDGE AUDIT (owner, 2026-10-12 — this REPLACES "seats never empty" and 4/4 occupancy as a goal): (1) `agentPaper` (realCfg,
  ON by default, `arena_prime.clean_cfg`): agents decide on PAPER — no new real buy or switch-in; Reaper, stops, rug / drain, fast reap and
  every exit still manage coins already held. Real money returns ONLY by the owner's switch after graduation (below). (2) `office_edge.
  BEST_AVAILABLE` False: best available / seat floor / ranked fills are off — an empty seat is cash (84 real fills: median GROSS −1.3%).
  (3) 📄 `backend/shadow_book.py` + `_shadow_note/_shadow_controls/_shadow_settle` (`data/shadow_book.json`): every would-be fill + controls
  from the same moment (best not chosen · random eligible · a WAIT coin) graded at 30s…1h from prices seen AFTER the decision, NET of the card's
  own measured round trip (`_shadow_cost`: ledger sell-back + 2× fee); `verdict` = agents vs random. (4) `judge_review.LIVE_RULES` False: the
  Judge proposes, never changes a live threshold. (5) `scripts/real-audit.py [card]` (read-only → data/real_audit.json): every round trip from
  the LEDGER, attribution (source · age · door · entry rule · exit), churn, cost drag, Monte Carlo, rolling walk-forward. 2026-10-12, 24h:
  240 agent trips · NET −$2.15 on $35 turnover · median −3.2% · 26% won · PF 0.26 · cost ≈ 1.8%/trip · resampled mean > 0 in 0% · walk-forward:
  0 rules → NO PROVEN EDGE. Losses: bad selection 39% · late entry 32% · rug 15% · bad exit 7% · execution (as the deciding cause) < 1%.
  GRADUATION (proposed, owner decides): ≥ 100 forward shadow fills · NET avg > 0 and median ≥ 0 after measured costs at the planned hold ·
  profit factor > 1.2 · beats the random control by ≥ 2 pts · bootstrap mean > 0 in ≥ 90% · top-3 trades < 30% of profit · max DD < 20% of
  stake — on trades AFTER the rule was frozen.
- 🔒 A HELD CARD BUYS NOTHING FROM THE ENGINE (2026-10-12, found 5 min after paper mode went live): `fallback_coin()` (the 30s fill of a
  reserved seat) and the stuck-buy swap ignored `holdBy` — a refused agent buy became $Business, and a stop's reserved seat bought $CHILLGUY.
  Both now return / slot back to cash under `holdBy` proof | agents. After ANY "no real buys" change, read the ledger 5 minutes later.
- ⏱ THE TRENCH DESK (owner's one-and-done spec, 2026-10-12): NEW-ENTRY UNIVERSE = 0 < live cap < $200K AND a KNOWN launch age ≤ 6h
  (`opportunity.MAX_AGE_H`, `agents.AGENT_MAX_AGE_H`, `in_lane`, `hard_fail`: unknown age / unknown cap = not eligible; held coins keep
  running). Freshness ladder 0–5m 18 · 5–15m 15 · 15–60m 12 · 1–3h 8 · 3–6h 4 (`FRESH_LADDER`, `fresh_key`, `FRESH_LABELS`, intake
  `OLD_INTAKE_H` 6). ⏱ `backend/trench_rounds.py` (pure + tested, `_rounds_pass` each agent pass, `data/trench_rounds.json`): every
  candidate runs its own 5-minute rounds — one read per round from the CURRENT row; hard fail = REJECT at once; full GO = ENTER early;
  round 3 = ENTER (A / B confirmed: price held ≥ −3%, buyers ≥ 50%, pool ≥ 80%, no avoid phase, early wallets not dumping; C only when
  every read improved) / REJECT / COOLDOWN (15 min; REJECT 30; a ≥ 5% move, tier upgrade or GO wakes it into a new round 1). An ENTER lives
  one round. Round ENTERs join `wait_` (cleared) after the near / ranked live check → memory → Warden (tier size) → `agent_seat` → keeper.
  Each decision is also a shadow-book group (`r_enter`/`r_reject`/`r_cooldown`). 📈 `market_wake.PHASES` DISCOVERY · EARLY ACCELERATION ·
  FIRST PULLBACK · RECLAIM · BREAKOUT · RUNNING · LATE FOMO · DISTRIBUTION · REVERSAL · COLLAPSE (`market_phase` → row `mp`): score +6 early /
  −15 LATE FOMO / −10 REVERSAL, DISTRIBUTION / COLLAPSE = hard no. 💸 Warden W22 (`COST_MAX_PCT` 5): measured round trip (ledger sell-back +
  2× fee ÷ seat) over 5% = no buy; W4 now halves only a coin < 15 min (`youngH` 0.25 — every coin is < 6h now, halving all made every seat
  fee-bound). Reaper reports carry `posRound` + `roundAction` + MFE / MAE. 📋 `judge_review.desk_stats` → payload `deskStats` → roster: real
  decisions · wins credited · losses pinned · % of its real trades that made money · median net (never a sum). Display: `RoundBar` +
  `RoundHistory` (SeatOps). `scripts/real-audit.py` replays recent losers under the rules AND counts the winners they would have blocked.
- 🧬 OFFICE DESKS EVOLVE ON REAL MONEY (owner, 2026-10-12: "ok to lose but not learning and still in the gen is crazy"): `office.demote(.., reviews)`
  — Weather / Warden / Courier / Reaper start their next generation at `OFFICE_REAL_SCRAP_N` 5 real losses the Judge pinned on them THIS life
  net of the real wins credited (`office_real_net`; Reaper credited only for its own profit exits), or on a paper demotion; tunables reset,
  `born` restarts, lineage keeps `lesson` (the most common cause). Before, a desk could only change gen if it had a promoted tunable to reset —
  it never did, so they sat at gen 1 forever. ⏱ Rounds: an unread holder scan / price is PENDING (never a reject); a candidate off the list
  for one pass keeps its rounds (closed after a whole round away).
- ⚡ OPEN TRENCHING (owner, 2026-10-12: "no reputation theater — newness, volume, buyers, liquidity, live chart / tape, early wallets, momentum";
  realCfg `agentOpen`, ON via `_agent_open_fix_1012`, backup data/realcfg_before_open1012.json): every empty seat takes the top of
  `opportunity.open_score` = newness × volume velocity × buyer velocity × 5-min momentum × early wallets × the Judge's evidence weight
  (real-money memory → ×0.7…×1.3, never a veto). `open_ok` = EXECUTION SAFETY only: live price · traded in 5 min · 0 < cap < $200K and
  ≤ 6h · pool ≥ the keeper floor · readable market data · live narrative not DISTRIBUTING / COLLAPSING. `narrative()` = HOT EARLY MOVE ·
  BUILDING · BREAKOUT · RUNNING · STALLING · DISTRIBUTING · COLLAPSING from THIS pass only. No holder scan, rug meter, creator / coin /
  source reputation, Devil veto, chart-rule block, 3-round wait or age halving decides an open-mode seat. Warden in open mode = W1
  execution · W3 pool share · W17 seat room (+ W11 smallest order + W22 "SIZE TOO SMALL FOR COSTS"). Still on: the keeper's own buy checks
  (route / sell-back / price near market), the office LIVE, keeper halt, Courier BAD, the hourly fill guard, Reaper's exits, the
  just-left / keeper-refused block (`_agent_blocked`). Payload `open` → RoundBar "⚡ OPEN · TOP".
- 👁 REAPER READS THE LIVE CHART (owner, 2026-10-12: "reaper reviews live chart, not every 5 mins"): `office.fast_reap(.., office)` in the
  6-second guard now applies, from the live chart price, the stop · R5t thesis invalidated (price under the thesis invalidation, losing) ·
  R7 trailing protection (peak ≥ `protectAt`, given back `giveBackPct`, still ≥ +1.5%) → `agent_pull` → keeper. The 5-minute rounds are
  only the position's clock for the display; no exit waits for them.
- 🪖 THE TRENCH CREW (owner, 2026-10-12; `backend/trench_crew.py` + `docs/TRENCH_CREW.md` — change both, `tests/test_trench_crew.py` checks
  they agree): ten roles (Tally discovers · Sherlock investigates · Weather contextualizes · Trigger times · Devil challenges · Warden sizes ·
  Courier executes · Reaper manages · Archivist remembers · Judge improves) + `HARD_WALL` (the money boundary only). In trench (open) mode:
  Devil's objections are a confidence weight on `open_score` (`devil_factor`: strong ×0.85, other ×0.95, floor ×0.6); the dev dumping now is
  the one Devil item on the wall (`dev_dumping` in `open_ok`); Warden's uncertainty rules W2 weather · W4 newborn · W20 exit risk · W21
  concentration SHRINK to ≥ ×0.5 (`warden_rules`), only W1 / W3 / W17 (+ W11, W22) can stop a buy; Sherlock's unknown is never a reject.
- 🪖 Trench mode exits: Reaper's R2 (holder scan fails / rug ≥ 65) and R3 (top-10 concentrating) do not fire with `agentOpen` — the live
  chart, liquidity (R1), stops, the rug radar on the tape and the trail decide. 🧾 A stuck buy is not stuck when the LEDGER shows it filled
  in the last 3 min (the card book had not synced: $Americaexe filled, then sent "back to cash" 2 s later).
- 🧬 TRUE SUBSTITUTION (owner, 2026-10-12: "demotion is not enough — bad generation out, new generation in"; `backend/generations.py` pure +
  tested): ACTIVE · SHADOW (the replaced generation, 24h, judged on the same real exits) · BENCHED (owner) · RETIRED. No "probation / demoted
  but still trading": office desks are replaced in `office.demote` on their own demoted record (a fresh gen gets 1h) or `OFFICE_REAL_SCRAP_N`
  3 net real losses pinned; the four desks at `REAL_SCRAP_N` 3 (`agents.survival` 'watch' is a label only). The new generation = hard-coded
  DEFAULTS + only the fix for how the last one failed (`generations.improve`, `CAUSE_PATCH`: Reaper gave_back → trail arms +4% / 35%
  give-back · held_too_long → 60 min / stop 20% · rug / thin pool / bundle exit → stop 20%; Warden thin pool → 0.75% of a pool · BAD SIZE →
  30% seat), bounded by TUNABLE; old tunes are NOT inherited (lineage keeps `oldTune` / `newTune` / `changed`). The Trigger +0.5 bar per
  death (`barBump`) is gone — no inherited fear. Payload `lifecycle` (+ Reaper's `shadow_record`) → roster "GEN n · ACTIVE" + `Lineage`.
- 🕯 TRUE DATA AT THE LIVE EDGE (`lib/tween.liveBar`, PriceChart's live apply): a new live candle opens at the previous close only when the
  history is current (≤ `STALE_BUCKETS` 2 behind); a history that ended minutes ago (a coin indexed late) opens the candle at the FIRST REAL
  TICK and leaves the gap empty — it drew one fake candle from the old close to the live price ($STREAM: entry → 2×) and invented flat
  minutes. 📊 MARKET CAP FIRST (`lib/mcap.mcapOf`): no live cap for a launchpad mint (…pump / …bonk) = price × its fixed 1B supply — used by
  PriceChart itself, the Agents tab chart, coin drawer, quick look and mini chart (they fell back to a PRICE chart for every fresh curve coin).
- ⚙ THE AGENT KERNEL (owner's consolidation spec, 2026-10-12; `docs/AGENT_KERNEL.md`, `backend/trench_kernel/`): ONE MintState per mint
  (`state.MintStore`, per-section timestamps, deduped, events only for what changed) · ONE candidate lifecycle DISCOVERED → TRACKING →
  CONTENDING → READY → ORDER_PENDING → HELD → EXIT_PENDING → CLOSED (data pending = TRACKING, never rejected) · ONE ten-agent brain
  (`brain.think`: pure opinions, Devil INFO / WARNING / STRONG_WARNING / HARD_VETO, Warden sizes, one reducer) · four hunter lanes HUNTING /
  ARMED / HELD · `kernel.KERNEL` re-judges only affected mints, live prices are events (`price_event`), latency p50 / p95 measured. Trench-mode
  seat fills read `KERNEL.ready()` (no second ranking). ONE enrichment scheduler (`_kernel_pass` → `_runner_intel`, `ENRICH_TOP` 4). RPC
  singleflight in `chain_rpc._rpc` (`RPC_STATS`). UI: `lib/agentHub.useAgentHub` + `KernelBoard`; `agentRead.rowState` is the one decision
  meaning. New agent logic ⇒ a pure function in `trench_kernel/brain.py`, never a fetch inside an agent.
- 🎛 THE AGENTS COCKPIT + 🧠 AI ROUTER (owner's reference image, 2026-10-12; `docs/AGENT_KERNEL.md` › UI + AI router): HQ › Agents opens on
  `AgentCockpit` (mission ribbon · 4 seats · ONE market-cap chart with real T D W B R X markers · live decisions · decision panel with Live / Inputs /
  Seats / Review / Trace · ten-agent matrix · review queue + owner review · operator controls); the old desk sits in one `▸ MORE` fold.
  `backend/ai_router.py` = local LM Studio first, then Groq / OpenRouter / OpenAI / xAI / custom; advisory notes only (displayed, never a rank,
  size, READY, order or stop); Tally / Trigger / Reaper / Courier / Warden never ask (test). Keys live in backend/.env (placeholders added), shown
  only as set + last 4. `LOCAL_LLM_ENABLED=false` switches the local model off; the kernel never waits on a model.
- ⏱ EXECUTION LIFECYCLE + QUOTE TTL (2026-10-12 execution audit; `fuse_wallet.exec_state / quote_stale / exec_metrics`): the keeper already resolves
  a pending tx before anything new (restart included), sells before buys, ONE in-flight tx per card, pending saved before the send, the SAME
  signed tx re-sent, simulation failures cleared at once. Added: a quote is never built into a tx past `QUOTE_TTL` (buy 8s · sell 5s · urgent
  exit — stop / rug / drain / flow / dead / floor / sell-all — half); a refreshed buy quote passes the secure-buy check again; `quoteAgeSec` +
  `quoteRefresh` on the row; `_FW_DUPES` counts requests dropped on an in-flight card; `office.execution.metrics` (ledger only) → the EXECUTION
  tile. `exec_state` NAMES a ledger row in one lifecycle word — it is not a second state machine. Slippage stays inside the existing caps.
- 🧹 STORAGE (`storage_trim.py`, hourly with `_data_clean`): the logo cache (was 1.0 GB) ≤ 300 MB oldest-first (never < 1 day old), a logo > 1.5 MB
  is served but not cached; `/tmp/feeless-*.log` over 20 MB keep their newest 5 MB. Ledgers, .db files, records, archives, lineage: never.
  The AI router persists nothing (in-memory notes ≤ 60 coins).
- ⚡ `/edge` is stale-while-revalidate (`EDGE_STALE_SEC` 600, background `_edge_refresh`) and a cold coin waits ≤ `EDGE_COLD_BUDGET` 3s: a 10s
  cold build held the browser's connection slots and every request on the page queued behind it (search read 12s in the browser, 6 ms on the
  server). The confluence ranking cache is `_edge_rank_cache` — it shared the name `_edge_cache` with the per-coin cache, whose clear() at
  5,000 coins wiped its `at` / `rows` (KeyError). The Agents tab's ▸ MORE fold mounts nothing while closed.
- 🏁 THE 3D OFFICE IS RETIRED (owner, 2026-10-12: "keep the new cockpit, remove the 3D office"): `OfficeRoom.jsx`, `OfficeRoom3D.jsx`,
  `officeRoom.css` and the room toggle are deleted (older notes that name them are history); the cockpit's helpers live in
  `components/command/agentWords.js` (AG · activityOf · ticker). Dead SeatOps / OfficeEdge parts only the room used went with it (CSS
  pruned brace-aware). The cockpit chart draws ONLY real fills (small ▲▼ at the fill price, no letters); decisions stay in the rail under it.
  Chart axes never print a negative price / market cap. 💹 Users' coin charts (TrenchChart › PnlBadge): the P&L ticker glides at ≤ 30fps and
  each REAL price tick flashes in its direction, glow by how far it moved (`lib/pnlTicker.js`, `styles/pnlTicker.css`) — users only.
- 🧊 EVENT-LOOP LAG CATCHER (`backend/loop_lag.py` pure + tested; started in reputation_service `_start_background`; admin
  `GET /admin/perf/loop`; `data/loop_lag.json` every 30s = the same view + per-store JSON load / save seconds, readable without an HQ
  sign-in): a thread pings the loop every 50 ms; while a ping is unanswered > 0.25s the loop thread's stack is sampled and the blocked
  time is charged to the project frames on it ("task › … › function:line"), plus what worker threads were running. 2026-10-12 first
  reading: the main backend's loop was BLOCKED 29% of the time (stalls to 10.8s) — that was the "lag" on every page, not the browser
  (startup = 35 requests, gzip on, one store + SSE). Fixed from its list: (1) `_block_load` rebuilt a 100K-wallet dict PER ROW of the
  runner board → one view per file version (`_block_view`); scanner strikes are written ≤ 1/min (`_block_save`, a person's report and a
  shutdown write at once; `_block_flush` primes the parse cache — no 14 MB re-parse). (2) pump_callers.json (31 MB) was parsed +
  re-written on the loop every minute → kept in memory, tracked in a worker thread, written every 10 min with `_json_save_soft`
  (pure-Python encoder: the C `json.dumps` / `json.loads` hold the GIL for the WHOLE document — a worker thread does not help them).
  (3) hygiene.json (6 MB) was re-written + re-parsed on every holder scan → only when a count changed, ≤ 1/min (`_hygiene_flush`).
  (4) the intel desk (~7s of pure Python) ran on the loop at startup and inline every 10 min → `_desk_get` = ONE shared build in a
  worker thread; readers never rebuild inline. (5) `_fw_peek()` = READ-ONLY Fuse wallet doc parsed once per write (`store.KV.stamp`);
  only pure read sites use it — anything that writes still takes its own `_fw_load()`. NEVER mutate what `_fw_peek` returns.
  (6) `backend/http_ctx.py` (installed in all four services): every `httpx.AsyncClient` without its own `verify` shares ONE TLS
  context (a new client re-read the CA bundle: 5.7 ms → 0.1 ms each, 141 call sites in reputation_service alone). (7) candles
  service: the 68 MB tick store is streamed to disk pair by pair (`_stream_store`) — one `json.dumps` froze live candles ~1s every
  20s. "THE SITE LAGS" ⇒ read `data/loop_lag.json` FIRST (top culprits + `json` costs), then `uptime` + `sysctl vm.swapusage`: that
  day the Mac sat at load 14–21 on 8 cores with 16.4 of 17.4 GB swap used, which makes every 20 ms parse a multi-second stall.
  (8) `_fw_full_ledger` reads only the rows appended since its last read (`store.Ledger.since`); `_fw_public` reads `_fw_peek()`.
  After: blocked 29% → 13% of loop time in steady state on the same overloaded machine; candles probe p95 113 → 29 ms.
  🔁 A STOPPED COPY CAN LINGER: uvicorn waits for open connections, and an HQ › Agents live stream never closes → the old copy gave up
  its port and kept its loops for 3+ min beside the new one (the keeper flock stopped a double trade). keep-alive `start` now stops by
  NAME, waits 15s, then -9; every launch line carries `--timeout-graceful-shutdown 10`. After ANY restart `pgrep -f "uvicorn reputation_service" | wc -l` = 1.
  Restarting ONE service by hand: `pkill -f "uvicorn <app>"` and let keep-alive start it (its 120s grace) — a hand start races
  keep-alive's probe and gets killed. A new store over ~1 MB must not be saved / parsed on the loop per event: debounce + keep in memory.
- 🧈 BUTTER PASS 2 (owner, 2026-10-12: "lag in the Agents tab, slow charts — clean dead code, run like butter"):
  · Agents stream: a kernel pass sends a BURST of deltas (one per changed candidate) and each one re-rendered the whole tab → `agentHub`
    folds them in at once but paints ≤ once per `EMIT_MS` 150 ms (`streamApply` / `emitSoon`; `hubApply` for the owner's own taps stays instant).
  · Agents page payload: `_agents_page_body()` = the snapshot minus what no screen draws (`AGENTS_PAGE_DROP`: index · social · cycleLog ·
    intakeView · rpc · lifecycle · seatScores · seatActions · opp …, and each row's `social` research packet = 250 KB), serialized ONCE
    per 2s for every reader (616 → 381 KB, 75 KB gzipped). Memory keeps everything (`_agents_snapshot()`); `data/agents_view.json` = the
    page's own bytes. A NEW office section the page must draw ⇒ make sure it is not in `AGENTS_PAGE_DROP`.
  · Charts: a chart already built answers AT ONCE (`RESP_STALE_SEC` 90: fresh < 20s, else the same answer + ONE background rebuild; no
    pool lookup first) — a repeat poll went 0.4–2s → 2 ms. The live candle comes from the price stream, never from this response.
  · Lists: `_list_now(key, ttl, rebuild)` = stale-while-revalidate for /fuses/discover, /fuses/trench, /fuses/trench/open
    (`LIST_STALE_SEC` 180, ONE rebuild per key via `_LIST_REBUILD`); Pump callouts answer from memory with one refresh behind. They
    cost 2–7s on EVERY 10s cache expiry → ~30 ms. A new list endpoint over ~0.3s to build ⇒ `_list_now`, never an inline rebuild.
  · Dead code out: SeatOps is only `KernelBoard` now (FreshBlock / RpcLanes / ActiveIndex + a dozen orphan helpers were drawn only by
    the retired room), 5 unused cockpit constants, 2 in OfficeEdge, 19 dead seatOps rules, 12 unreferenced @keyframes site-wide. The
    build's lint does NOT flag unused variables — check with eslint `no-unused-vars` (+ `react/jsx-uses-vars`) and an
    "export never imported outside tests" scan before calling a surface clean.
  · SwapWorkspace test: only `/api/trading/` calls take a scripted answer — a shared poller (coin edge) used to swallow the /execute
    answer under load. test_keeper_landing's scanner-share test freezes its clock. Both had been refusing the push gate on a loaded Mac.
- 🛂 SEATS: CHECK THE BUY BEFORE THE SEAT (2026-10-12, "seats staying empty" — 6h ledger: 231 agent buys refused vs 34 filled; every refusal emptied
  the seat again and the agents re-picked the same coin): `_seat_precheck` (in the agents' fill loop, real card) runs the KEEPER'S OWN checks before
  `agent_seat` — `_fw_live_pairs` → `live_buy_market`, then the same two read-only quotes (`_fw_quote` + `_fw_secure_buy` + impact) for as many coins
  as there are open seats; a coin that fails gets no seat and sits out (`_agent_refused`: 3 min market / 10 min safety / 30 min no route) and the next
  READY coin is tried in the same tick; quotes stand down 20s after any Jupiter 429 (`_FW_JUP_BUSY` — sells and real buys keep the quota). The seat
  starts from the LIVE depth + price (the board row was minutes old: rug shield "$18K → $8K pulled" and Reaper −24% three seconds after a buy).
  `_fw_live_pairs` third fresh source = Pump's own coin record (`launchpad_board.pump_pair`; 101 of the 231 were "live market unavailable" on coins
  too new for DexScreener / Jupiter). `live_buy_market`: a `curve` / picked order on a curve dex = max(reported, the curve's depth) — the agents' row
  read the curve ($10K) while the gate read Jupiter's paid-in SOL ($5K). `_fw_secure_buy` reads the market price FRESH (the 20s cache read "4.6% above
  market" on any coin running). `fuse_wallet.agent_no_buy` (10 min after a safety refusal) feeds `_agent_blocked`. A seat the wallet does not hold yet
  (`real` card, leg not `real`) is never stopped by Reaper (R0) or "pulled" by the rug shield. The open seat on the cockpit lists the last refusals
  (`seat.refused`, keeper's own words). EMPTY SEATS ⇒ group the 6h ledger's skipped buys by reason FIRST (`status in skipped/failed`).
- 💹 P&L ON EVERY CHART (`components/terminal/ChartPnl.jsx`: `useMyPosition` + `PnlBadge` moved here, `ChartPnl` drawn by `PriceChart` itself; prop
  `pnl` = false (off) · an object {label, pos} (a position handed in) · absent (the viewer's own, ONE shared read per coin via `sharedJson`); the host
  chart's streamed price drives it — no second poll). TrenchChart keeps its own badge (`pnl={false}`). Cockpit chart = `plain` (no scene) + the
  `LiveTrade` strip (`tradeBar`: entry → now · live P&L · a bar from the stop to the take) and lives INSIDE `.ack-plot` (`--ack-h`; the terminal's
  `!important` chart heights spilled out of the box). `cockpitAi.css` is imported AFTER agentCockpit.css (it owns the plot height + the meta pass).
- 🧠 THE MODEL'S DECISIONS + THE AGENTS LEARN FROM THEM (`AiDecisions.jsx` `AiPane` = decision panel tab 🧠 AI: provider line, model-vs-kernel agree
  meter, ASK box → `POST /admin/ai/ask`, decision log `office.ai.log` (60 kept, 20 sent) with AGREES / DISAGREES (`lib/aiRead.js`), 🎓 learning box
  `office.ai.learn`). `backend/ai_learn.py` (pure, tested): each stance noted once per coin / 30 min, judged 15 min later; `factor` ×0.9 (proven
  warning) / ×1.1 (proven spotter) only with ≥ 20 judged AND ≥ 2 pts apart from the model's base rate → kernel ctx `aiw` → `open_score(ai_w=)`
  (clamped 0.9–1.1). THIS REPLACES "an AI answer never changes a rank" — still never an order, size, block, stop or sell, and an unproven model
  weighs exactly nothing. Low usage: `ai_router.case_key` is the case's STATE (coarse numbers), `CACHE_SEC` 600; `_ai_brief` gives Sherlock holders ·
  chart · flow · launch · crowd from the desk's own row (no fetch). 2026-10-12 the local model answers in ~4s; Groq key set but untested.
- 📡 JUPITER = TWO PACED LANES for the keeper (`_fw_jup`, `_jup_lanes`, `_jup_pick`, `JUP_LANE_GAP` keyed 1.05s · public 0.35s, `JUP_LANE_REST` 8s
  after a 429 or its Retry-After): a call goes to whichever lane is free first. Found live 2026-10-12 right after the seat fixes: a $0.08 off-card sell
  failed "Jupiter route unavailable (HTTP 429)" four passes running → Courier read execution BAD → COURIER BLOCK on all four seats. The keyed lane
  (`JUPITER_API_KEY` IS set — a free key ≈ 1 request a second) was hit by bursts of quotes (direct + multi + sell-back + build per order, + the
  pre-sell buy checks). "COURIER BLOCK" / "route unavailable (HTTP 429)" ⇒ count the keeper's Jupiter calls per pass before anything else. The
  market service's own log is full of DexScreener 429s (launch board) — not fixed here. 📮 Courier counts a SEND only when something was signed:
  a row that failed at "build/sign … (HTTP 429)" with no signature is not a failed send (four of them read execution BAD and blocked every seat 15 min).
- 🎯 BUY SLIPPAGE = 3% THEN ONE RETRY AT 5% (owner, 2026-10-12; `fuse_wallet.BUY_SLIP_FIRST` 300 · `BUY_SLIP_MAX` 500 · `BUY_SLIP_RETRIES` 1 ·
  `slip_retries(side)`): a buy's first try is 3% whatever the wallet's own slippage setting; a slippage failure (at send or on-chain) gets ONE
  retry at 5%; the retry's failure is a miss (`slip_transient`) and the agents leave that coin 10 min (`agent_no_buy` counts slippage). Sells keep
  two retries and their steps to 8% — an exit must land. This REPLACES "the first 2 slippage failures are not misses" for buys.
- 🧬 INHERIT THE GREAT (`trench_kernel.lifecycle.improve(role, causes, tunable, prev, wins)`, `GREAT_WINS` 3): a replaced generation that had ≥ 3
  REAL wins credited hands down the settings it won with — except the keys its own failure is being fixed on; a generation that never won hands down
  nothing (the earlier "no inherited fear" rule stands for losers). Lineage `changed` says "kept stopPct 22 — it won 4 real trades with it". The
  model's judged record (`ai_proof.json`) and the real-money memory are shared by every generation — a new one starts with them, never from zero.
- ⚡ LIVE PULSE (`LivePulse` + `pulseOf` in AgentCockpit, `ack-pulse` under the mission ribbon): ONE 1-second clock; pass age + a bar to the next
  pass, coins tracked / new per min, re-judged + events / s, the funnel tracking › contending › ready › held, the brain's own latency, the last
  decision line and the model's last stance, each with its age ticking. Only the kernel's counters and real timestamps. Operator controls add
  🧠 Learn from the model (realCfg `agentAiLearn`, on by default: off = asked, shown and judged, weighs nothing) and the fixed BUY SLIPPAGE chip.
- 🟢 THE TRADE ON THE CANDLES (`components/terminal/ChartLive.jsx` + `styles/chartLive.css` `clv2-*`; owner, 2026-10-12: "meta styled buy and live
  moving pnl that moves with the current candle"): a ▲ BUY chip pinned at the entry (its price level; at the buy's candle when that is on screen,
  else pinned left; dimmed when the entry is off the scale) and a P&L tag that RIDES THE LIVE CANDLE — it sits at `shownRef` (the close the forming
  candle is drawn with, eased between real ticks; PriceChart sets it wherever it sets `shown`) just left of the price axis, with a thin line from
  entry to now. ONE rAF loop ≤ 30fps writing transforms + text straight to the DOM (no React render per frame; rAF is paused in a hidden tab — the
  Browser pane shows it only on a screenshot). Drawn by `ChartPnl` (`OnChart`) for the viewer's own position on EVERY PriceChart, for a seat
  (`pnl={{label, pos, tagOnly}}` — cockpit + TrenchChart pass `tagOnly`, their own badge / strip carries the numbers) and by PriceChart itself
  for a Fuse card's coin (`fuse.entry`). `pctWord` / `usdWord` / `liveRead` are pure + tested.
- 📡 A BUSY JUPITER IS NEVER "NO ROUTE" (`_fw_secure_buy` re-raises a 429 / 5xx from the sell-back quote — it used to read "can't sell it back to
  SOL (no route)" and bench a good coin 30 min) and the seat pre-check takes NO seat while Jupiter is rate-limiting (`_FW_JUP_BUSY` ≤ 20s: the coin
  is not refused, just not seated this tick — the keeper's buy would fail the same way). 2026-10-12 after every fix above the remaining choke for
  real fills is Jupiter's own rate limit on BOTH lanes (the public lane is shared with our price / token reads; the key is a free ~1 rps plan).
- 📡 JUPITER "BUSY" = EVERY LANE FAILED (`_fw_jup`: `_FW_JUP_BUSY` is stamped only when the call's FINAL answer is 429 / 5xx). It was stamped on
  any 429 even when the other lane then answered — the public lane is 429'd most minutes, so the seat pre-check stood down EVERY tick:
  2026-10-12 23:05 → 23:35 four empty seats, READY coins, 0 buys sent to the keeper. "SEATS EMPTY + READY > 0 + no ledger rows" ⇒ check
  `_FW_JUP_BUSY` first. 📡 Final buy gate (`_fw_live_pairs`): DexScreener AND Pump's own record (every Pump mint, `LIVE_PUMP_MAX` 12) in
  parallel, each bounded by `LIVE_SRC_SEC` 4s, then Jupiter only for coins neither answered (its keyed quota belongs to the keeper's quotes).
  6h before: 62 of 172 refused agent buys read "live market unavailable" — DexScreener + Jupiter public both 429 from this machine, Pump 200.
- 🎯 THE OWNER'S MC BAND (owner, 2026-10-12: "trench better on coins from 12k-300k mc"; realCfg `agentMcMin` / `agentMcMax`, options
  `universe.BAND_MINS` 0/5K/10K/12K/20K/30K/50K · `BAND_MAXS` 100K/150K/200K/300K/500K/1M, default $12K–$300K; HQ › Agents › 🎛 controls ›
  🎯 UNIVERSE): ONE source `trench_kernel.universe.band()` (set from realCfg at the start of every agents pass + on the owner's save) read by
  `in_lane` / `under_cap`, `opportunity.hard_fail` ("under your $12K floor" / "≥ $300K"), `opportunity.open_ok` ("outside your MC band"), the
  ranking's band part and the payload `universe`. `lane_cap` = the band top (the $200K → $1M → $5M widening is gone). Held coins keep running.
- 🫀 THE MODEL'S VITALS (owner, same night: "pull more vital info from the AI provider"): IN — `_ai_brief` adds band · age bucket · $/min +
  buys/min · the live 90s tape (+ its word `tapeRead`, the only new key in the cache key) · early wallets · dev · socials (presence only, never
  a URL) · Pump callers · the curve · what our REAL card made on coins like it (`real_memory.estimate`) · the model's own judged record. OUT —
  `ai_router.parse_advice` keeps `vitals` {rug, narrative, crowd, momentum} 0–100 (clamped, non-numbers dropped), `timing` EARLY / ON TIME /
  LATE / CHASE / DEAD, ≤ 4 `flags` (cut at a word, `FLAG_LEN` 40, key-shaped runs masked). JUDGED — `ai_learn.note(.., vitals, timing)`,
  `vital_record` buckets RUG:HIGH (≥ 60) · RUG:LOW (≤ 30) · TIME:EARLY · TIME:LATE (LATE / CHASE) · TIME:DEAD vs the base rate of ALL calls;
  `advice_factor` = most cautious proven factor of stance + vitals; still ±10% total and nothing until 20 judged. COVERAGE — `_ai_jobs`:
  every READY coin inside the band first ('high'), then a conflicted case, then the top in-band contenders; a case already answered in this
  STATE is skipped (`ROUTER.fresh`); `AI_JOBS` 4. Local LM timeout 30s (the vitals answer took 16–31s with the live service sharing the model).
  The model still never buys, sizes, blocks or sells. UI: `AiVitals` (meters, rug inverted) on the decision panel, every log row (mini), the
  review queue's 🧠 AI column (`AiCell`), and the 🎓 box's per-vital record (`cai-learn-vitals`).
- 🎛 OPERATOR CONTROLS ARE META (`CockpitControls.jsx`, `lib/cockpitControls.js`, `styles/agentControls.css` `acx-*` / `avt-*` / `thd-*`):
  grouped cards (🎯 UNIVERSE with the live band track — this pass's candidates as dots on a log $1K → $1M scale · 💰 EXITS · 🪑 SEATS & ENTRY ·
  🧠 MODEL), one segment row per control from the server's own option list, a who-badge per row (AGENTS ice blue · YOURS gold · YOUR BAND
  green), "now · …" = what the agents use under AGENTS CHOOSE, the tapped option pulses until the hub reloads. Test ids `ack-op-<key>` (row,
  `data-value`) + `ack-op-<key>-<value>` (buttons). The old selects + `.ack-op` / `.ack-auth` CSS are gone.
- 💹 LIVE P&L HUD (`TradeHud` in AgentCockpit, replaces the strip): P&L % + $ glide to each real tick of the shared 3s poller and flash its
  direction; one rail stop … take with now, the PEAK (mfe), the worst (mae), the trail line once armed (`office` positions now carry `armAt` /
  `trailAt`), "gave back" and "to go"; the held clock ticks; Reaper's ruling + next review. Every seat card has the same rail (`SeatBar`) and
  its P&L / $ now move with the live price against its own entry (`seatCards`), the server's figure only between reads.
- 💾 THE AGENTS' STORES LIVE IN MEMORY (`backend/mem_store.py` `MemStore`: loaded once, path looked up at call time so the test sandbox holds,
  written ≤ every N s + flushed in `_keeper_stop`): agents.json 90s (was parsed AND written every pass: ~5.8s of blocked loop / 25 min) ·
  trench_lingo.json 10 min · shadow_book.json 60s · social_cache.json 120s · agents_view.json / agent_office_view.json 60s. NEVER for money
  records. A new agent-side store over ~1 MB ⇒ a MemStore. 🐛 the generation-replaced `_audit` call had the wrong arguments (crashed the
  lifecycle loop on every replacement); the radar's DexScreener batch skips an HTML 429 page instead of printing "radar error" each minute.
- 🩹 WHY THE REAL CARD LOSES (2026-10-13, from the ledger, `scripts/real-audit.py` + `scripts/fuse-report.py 24`): put in $32.50 → $0.89;
  24h = 104 trips, NET −$1.42, 29% won, median −8.6%, median hold 4.4 min, execution ≈ 1.4% a trip; 0–5 min coins −35% avg; stops filled
  ≈ −35% vs their −12…−30% lines (launch coins gap between 6s checks; fills land 20–155s after the decision); walk-forward on the agents'
  real trips = NO PROVEN EDGE. The model's 600 judged calls: the coins the desk ranks top fall a typical 18% within 15 min, 26% go up.
  Its rug read separated winners ONLY in the second half of the night (first half: rug ≥ 60 −66% vs ≤ 30 −60%) and the night's worst real
  losers had LOW rug reads — so it stays a ±10% weight, never a block. Re-check that split before promoting any AI vital.
- 📉 CRASHED-COIN BUY REFUSED (`fuse_wallet.MAX_BELOW_PCT` 30, `buy_safety`): a quote ≥ 30% UNDER the market reading = the coin crashed
  since it was picked (or the reading is stale) → refused ("below market", a SAFETY word → the agents skip it 10 min). $PONSA / $REPE read
  ~$54K caps at the decision and filled 96% lower. The check used to refuse only quotes ABOVE the reading.
- 🔑 THE JUPITER KEY BELONGS TO THE MONEY PATH (`_jup_prices(.., keyed=False)`, `_jup_tokens(.., keyed=False)`): every read is public-only;
  `keyed=True` only for the keeper's secure-buy / secure-sell price and the final buy gate's live-pair read. Reads went keyed-first, unpaced,
  and ate the ~1 request/s the keeper's quotes need (30 of 55 skipped agent buys overnight: "Jupiter route unavailable (HTTP 429)").
- ⚡ The tier tick reads the wallet doc through `_fw_peek()` (seven read-only sites; the loop-lag catcher charged `_prime_tick › _fw_load`
  149s in 8h). Writes still take their own `_fw_load()`. 🗄 Archive hash chain = `office.verify_inc` (`_arch_verify`): new records only,
  the whole chain at most every `VERIFY_FULL_SEC` 300s (a rewrite in the middle is found by the next full check; test).
- ♻ DEAD-COIN RENT (`fuse_wallet.dead_accounts`, owner `POST /admin/fuse-wallet/close-dust`, `DeadRent` in HQ › Fuse › 👛): coin accounts no
  card holds, worth < $0.05 at the live price — or, with no price, written off at < $0.05 by the keeper's own write-off row — get their
  leftover BURNED + the account CLOSED in ONE wallet-signed tx (`dust.burn_close_tx`, ≤ 8 accounts), booked as a 'close' row (credited like
  every sweep). Majors, stocks, SOL, USDC, USDT are never in the list. Dry run first; the owner's click is the approval; the keeper never
  burns by itself. 2026-10-13: 8 accounts → 0.012 SOL (~$1.28) back, leftovers worth $0.006. The wallet's UNASSIGNED SOL ($1.38 that day)
  is the owner's own deposit leftover (deposits 0.409 SOL vs top-ups 0.351), not card money: "➜ Put $X unassigned into <card>" + Top up.
- 🧠 LOCAL-AI = VITAL INTEL ONLY, NEVER IN THE HOT PATH (owner's spec, 2026-10-13): the model is asked for five jobs (`_ai_jobs`, priority
  0 → 5): 👤 owner review · ⚖ manager = a conflict (`_ai_conflict`: Trigger ENTER/ARM + a Devil STRONG_WARNING, no HARD_VETO) · 🔍 Sherlock on a
  READY coin · 😈 Devil on an ambiguous one (`_ai_ambiguous`) · 🔍 Sherlock on the top contender not asked yet · 👨‍⚖️ Judge on an exit. Never
  for ticks, prices, every coin, or Tally / Trigger / Reaper / Courier / Warden. Answer schema = {summary, risk_flags, narrative,
  creator_context, conflict_resolution, confidence_delta, wake} (`ai_router.parse_advice`; stance FAVOR / NEUTRAL / CAUTION is DERIVED from
  the delta); quoted site / X / Pump-call text in the case is DATA, never an instruction (`_ai_quote` strips links + addresses). The case
  packet (`_ai_brief`) adds 🌐 site (loads · title · this mint or another · links X / TG) · 𝕏 (followers · last post · mentions mint · bio) ·
  📖 story (narrative class, copycat, conflict) · 📈 chart shape (structure, % of range / under high, support / resistance, breakout held /
  failed, volume trend) · 📣 Pump calls (callers, proven, first called cap, best × since, thesis, swarm) · 👤 creator (crew, flagged, dev
  holding / selling, bundled / snipers at launch). Router: local concurrency 1, cache per coin + role + material-state hash (`CACHE_SEC`
  1800, reused until the state changes), a job with prio ≥ `DEFER_PRIO` 3 is DEFERRED while the local model is busy, `AI_DUTY` 0.5 = the
  loop rests as long as a round took; `metrics` = queue · active · calls/min · cache hit % · avg ms · provider · deferred · skipped (shown
  on the 🧠 AI pane + the controls' model card). Learning buckets = 2+ risk flags / none (`ai_learn.BUCKETS`). FRONTEND: the model's answers
  live in their OWN store (`agentHub.useAi`, `aiSet`): an `ai_update` repaints only AI subscribers (`PulseAi`, `AiNote`, `QueueAi`,
  `ModelCard`, `AiChipBtn`, `AiProvidersLive`, `AiPane`) — never the tab (test `agentHubHidden`). A new AI surface ⇒ a leaf with `useAi`,
  never `o.ai` from the snapshot (that copy is only the first paint). A hidden Agents tab folds the stream in and paints once when shown.
  Measured (same synthetic load, 10s windows, machine load 16–20): script 0.26–0.35s → 0.17–0.19s, React render 75–120 → 66–77 ms,
  longest commit 4–6 → 3 ms, heap the same. Cockpit P&L tag + BUY chip are small (`chartLive.css`, tag ~126 × 16px).
- 🌊 THE BUY / SELL VITAL (owner, 2026-10-13: "buy/sell bar should be a vital and be wired to Reaper and whomever else who watches … learn not
  to buy at the peak"; `flow.vital(window)` pure + tested → ONE state from the last 90s of REAL swaps: BUYERS (buys ≥ 1.3× sells, ≥ 3 wallets;
  `hot` = ≥ 8 buyers) · SELLERS (sells ≥ 1.5× buys on a falling price, or a 🩸 dump) · PEAK (🏔 buying climax, or already +6% inside the window)
  · BALANCED · THIN (not judged, never a block); `flow.window` now counts distinct `buyers` / `sellers`). WHO READS IT: ⏱ Trigger
  (`brain.trigger`: SELLERS → WAIT, PEAK → ARM "not bought at the top"; desk row `fv` → MintState `market.flow`, kernel event `flow` on a state
  change) · the fill gate in `_prime_tick` (each READY coin about to take a seat gets ONE batched `_flow_fetch`, ≤ seats + 3 pools; SELLERS /
  PEAK waits this tick with a Trigger WAIT line, a crowd buying goes first; `_office['flowWait']` → payload `flowWait`) · rank ×`CROWD_F` 1.05
  for a hot crowd (a weight, never a gate) · ☠ Reaper (`reap(flows=)` from the tape `_flow_now` already holds — no new fetch): `R4f sellers
  took over` banks an agent seat ≥ +4% (`FLOW_BANK_PCT`), `R4c buying climax` banks one ≥ +15% (`FLOW_CLIMAX_PCT`), sellers on a RED seat only
  tighten its stop to 70% (`FLOW_TIGHT`, never under `STOP_FLOOR`) — a fast green candle on a held seat is never an exit. It only ever makes
  the agents buy LESS or bank sooner. Page: `SeatFlow` on each cockpit seat (`flowBar`, `thd-flow`) + the 🌊 held-back list on the first open
  seat. Hand-set thresholds, NOT learned — R4f / R4c results land in the archive under their own rule; read them before trusting either.
- 💻 THE LOCAL MODEL IS OWNER-ONLY (owner, 2026-10-13: "bad lag in this tab, perma fix — has to be LM Studio"; `ai_router.local_ok`): measured
  that day — event loop blocked only 2.2%, but the 7B MLX model took ~13s an answer and ran ~half the time (`AI_DUTY`) on the SAME M3 GPU +
  unified memory (24 GB, 16.8 GB swap in use) Chrome draws the Agents tab with. Background jobs (READY coins, conflicts, contenders, Judge
  reviews) now NEVER run on the local model: they go to the cloud fallbacks, or are not asked (deterministic only) — `tried` reads
  ['local', 'OWNER ONLY']. The local model answers only role `owner` / urgency `force` (the ASK box). `LOCAL_LLM_BACKGROUND=true` puts it back.
  The Groq fallback had NEVER answered: its default model `llama-3.1-8b-instant` is gone (404 model_not_found, shown only as OFFLINE) →
  default `qwen/qwen3.8-27b` (the vitals schema in ~0.9s; gpt-oss-20b / 120b return malformed for it). A PROVIDER READS OFFLINE WITH A KEY SET ⇒
  curl its /models first. "LAG IN THE AGENTS TAB" ⇒ loop_lag.json, then `office.ai.metrics.provider` + avgMs: 'local' in the background = this.
- ☀ DAY LAG, part 2 (2026-10-13, tips.css): the day sweep `.terminal-main::before` was still a full-screen `mix-blend-mode: soft-light` layer over the page (anything moving under it re-blended the viewport every frame), the two day auroras (`day-aurora-a/b`, App.css) drifted full-screen under the translucent day panels and `body.theme-day::before` carried a filter. All three are off in day; the static wash stays. Never put a blend mode or filter on a full-screen layer.
- 🧹 AUTO CACHE CLEAN (`lib/cacheSweep.js` `sweepable(name, map, {ttl, max, at, keep})` + `sweepNow`, tested): 20 module-level frontend caches
  keyed by coin / wallet / URL never evicted (candle histories, live prices, coin edge, profiles, rep, rug shield, sharedJson answers …) —
  a tab open for days (the owner's: six) only grew. ONE sweep a minute + when the tab is hidden: entries past their age go, each cache is
  trimmed oldest-first, anything a mounted consumer still uses (`keep`) stays. A NEW module-level cache ⇒ `sweepable(...)`, never a bare
  `new Map()`. Agents hub paints ≤ once per `EMIT_MS` 400 ms (was 150).
- 💵 TOP-UP COUNTS RESERVE SOL PARKED AS RENT (`fuse_wallet.free_for_topup`, `TOPUP_LIQUID_MIN` 0.006; top-up route + HQ `topupSol`):
  2026-10-13 the owner sent 0.0156 SOL ($1.68) and could not top up $1 — 0.0135 of the 0.019 SOL reserve sat as refundable rent in 9 coin
  accounts, so the deposit read as "refilling the reserve" and only $0.87 was "free". Parked rent now counts toward the reserve (the
  `free_for_owed` rule); the wallet always keeps 0.006 SOL liquid outside the cards; the refusal names the numbers. "CAN'T TOP UP" ⇒
  compare `reconciliation.outsideCardSol` with `keeper.rent.parkedSol` first.
- 🩺 FX GOVERNOR = THE LAG CATCHER'S FIX (`lib/fxPause.js` `govern` / `setFxPressure` / `fxStats`, started with `startFxPause`; owner,
  2026-10-13: "lag catcher actually fixes instead of a lite mode"): every ~1.5s (+ scroll / resize / tab visibility) it reads EVERY endless
  animation on the page — no class list — and pauses those off-screen, with no box, or in a hidden tab, resuming them when they are back
  (it only resumes what it paused; one-shot animations are never touched). `perfWatch.flush`: two bad minutes (< 24 fps or > 1.5s blocked)
  → `setFxPressure(1)` = only layers ≥ `BIG_PX` 150,000 px² pause (sweeps, auroras, drifting backdrops); three healthy minutes → back.
  AUTO LITE IS GONE: `fx-lite` is only the user's own switch (or HQ forceLite). The perf report carries `fx` {running, paused, shed,
  pressure}. Measured on Fuse › Arena: 167 endless animations, 136 of them off-screen. A new animated surface needs nothing; the
  `FX_SURFACES` class list is the older, coarser net and stays.
- ⏳ EVERY HQ BUTTON REACTS (`lib/hqBusy.js` `hqWrite` / `useHqBusy`, wired once in HqDeck's `call`; `HqBusyBar`, `hq-busy` in hqNav.css):
  every HQ write marks the button just clicked `aria-busy` (dim, pulsing, unclickable) until the server answers, shares ONE request for
  an identical write already in flight (a double click never sends twice) and shows a bar on top of HQ that explains a wait past 4s
  ("the keeper finishes its pass"). Owner money routes wait on `_fw_tick_lock` by design — the button used to look dead meanwhile.
  A new HQ button needs nothing as long as it uses `call`. Fuse wallet ↩ (sell every coin) now asks first. 🩺 `data/perf_view.json`
  (every 30s, last 15 min): what browsers feel — routes by p95, pages by fps / blocked ms, the FX governor's counts — readable without
  an HQ sign-in. "A PAGE / BUTTON IS SLOW" ⇒ read perf_view.json (browser) and loop_lag.json (server) before touching code.
- 🔌 TWO BROKEN ENDPOINTS FOUND FROM THE LOGS (2026-10-13; `tests/test_routes_bound.py` guards both kinds): (1) `GET /intel/{chain}/{mint}`
  answered 422 on EVERY read since 2026-10-11 — a helper (`_early_buy`) was inserted between the route decorator and `token_intel`, so the
  route was bound to the helper (launch forensics, coin intel tags: 136 failures in one log). (2) the Agents cockpit's owner review
  (REVIEW · TRACK · ARM · IGNORE) answered 500 on every click — `_audit` called with the wrong arguments AFTER the list had been saved.
  "A BUTTON DOESN'T WORK" ⇒ count non-2xx by route in /tmp/feeless-*.log first:
  `grep -E '" (4|5)[0-9][0-9] ' /tmp/feeless-reputation.log | sed -E 's/.*"(GET|POST)/\1/' | sort | uniq -c | sort -rn | head`.
  NEVER put a new def between a decorator and its handler.
- 🧠 AGENTS LEARN FROM REAL WINS + LOSSES, LIVE (owner, 2026-10-13: "do #2, 3, 4 but seats still stay filled, 5"):
  · #2 `real_memory`: the table now carries a LINE = the median estimate of the card's own real trades; a coin's estimate = the MEAN of its
    learned buckets (`door:other` says nothing and is dropped). Under the line = the worse half → ranked down (`_judge_weights`: ×0.7 …
    ×1.3 against the line), never a blocked seat. Proof = ROLLING walk-forward (each trade from the 30th judged by a table built only from
    the trades before it; ≥ 10 taken, ≥ 5 skipped, ≥ 2 pts apart). Why: the old veto was "3 points under the card's typical trade" — with a
    typical trade of −23% nothing was ever skipped. 2026-10-13, 76 real exits: ranked first 35 at −7.8% avg vs ranked last 11 at −38.8%.
  · #3 `judge_review.LIVE_RULES` True + kernel ctx `pens` → `brain.think`: each repeat real-loss cause (≥ 3 in the last 20 reviews) that
    matches a coin ranks it ×(1 + points/100), all together ≥ `PEN_FLOOR` ×0.75. It had never been wired into the live ranking.
  · #4 `CONTROL_MOVES_HR` 6 → 3 (a held coin sold for another); empty-seat fills keep `FILL_MOVES_HR` 36 so seats stay filled.
  · #5 THE MODEL IS VETO-ONLY: `ai_learn.UP` 1.0 / `DOWN` 0.85, `open_score` clamps it to 0.85–1.0 — it can never rank a coin up (its
    ENTER calls fell a typical 39%); only a warning proven on its own judged record weighs. Trench-voice prompts (`ai_router.SYSTEM` /
    `ROLE_ASK`: the desk's rug-sniffer, "find what kills the play"). `AI_JOBS` 2 a round: owner review · a split desk · a READY coin ·
    an ambiguous setup — no call for a contender or a closed trade (the Judge's review is the engine's own). The local model stays owner-only.
  · 📄 PAPER = ONE ENTRY PER CONFIRMED REAL BUY (`_shadow_real_buys`): each FILLED, signed agent buy on the ledger → one paper row at its
    decision's market price (`midPx`) carrying the real fill (`real`) + that moment's control picks. The 5-minute round decisions are no
    longer paper rows. Paper and real now grade the same trades 1 : 1; no model, quote or fetch is spent on it.
  None of this is a promise: the edge audit that day read 0 of 755 rules positive on unseen coins.
- ⚡ HQ POP-OUT (`components/HqPop.jsx` + `styles/hqPop.css` `hqp-*`, mounted in `FeeCatWidget` above the cat; owner, 2026-10-13: "in my
  mini cat bottom right, a one click big HQ popout"): CREATOR WALLET ONLY — `GET /admin/whoami` now answers two bools `{isAdmin, isOwner}`
  and the button renders only on `isOwner` (nothing renders, and no HQ code loads, for anyone else). One click = the whole `HqDeck` in a
  full-window portal on any page (`startTab="agents"`), still behind the same signed HQ session. Header = spinning HQ mark + a mood read
  from REAL requests in flight (`hqMood(useHqBusy())`: 🟢 LOCKED IN · ⚡ SENDING IT · ⏳ STILL COOKING — never a canned ticker) + six
  shortcuts (`HQ_JUMPS` → window event `feeless:hq-go` {tab | view | panel}, which HqDeck listens for). Esc / ✕ closes; open state lives
  in sessionStorage. While open `body.hqp-open` hides `.terminal-main` (an opaque pop-out: the page under it paints nothing).
  New HQ shortcut ⇒ one `HQ_JUMPS` row.
- 👑 THE COACH + 🎬 REAL TRADE TAPE (`backend/coach.py` pure + tested `tests/test_coach.py`; `lib/coachTape.js`, `command/CoachTape.jsx`
  (`TradeTape`, `CoachBox`), `styles/coachTape.css` `ctp-*`, mounted in the cockpit as `ack-tapezone` between the main row and the matrix;
  owner, 2026-10-13: "I the creator can strengthen agents and advise to pull coins with a reason that is used and vital, not just a note …
  AI should be able to instruct / strengthen agents … real tape of entry, fills and agent / AI analysis"):
  · A DIRECTIVE = one cause from a FIXED vocabulary (`coach.CAUSES` = the features `opportunity.judge_hits` tests on a live coin) + points →
    kernel ctx `pens` (`_coach_pens`: merged with the Judge's, the stronger per cause) → `brain.think` ranks matching coins down, together
    ≥ `PEN_FLOOR`. Owner −8 (strengthened −12) for 24h · model −4 for 6h, never over an owner rule. Never an order, a size, a sell or a
    blocked seat. `POST /admin/agents {coach: {key, why, strong} | {strengthen: id} | {kill: id}}` (creator only, audited, wakes the desk).
  · ✋ PULL + TEACH (`{coach: {key, why, mint, sym}}` AFTER the page's own `manualSell` call — the sell is the card's existing ✂ path): the
    cause becomes an owner rule and the coin is off the agents' buy list 6h (`coach.blocked` → `_agent_blocked`).
  · 🧠 MODEL COACH (`_coach_ai`, role `coach`, ≤ every `COACH_AI_EVERY` 15 min, only with ≥ 2 real losses in 6h; cloud only —
    `local_ok` is false for it): it reads the last real trades as cause / result lines + the vocabulary and may answer `directives`;
    `coach.from_ai` keeps only vocabulary causes (≤ 2). They wait for the creator's ✅ Back it / ✕ on the page.
  · 🎬 `coach.trade_tape` (payload `tradeTape`, rebuilt ≤ every 20s): one story per confirmed agent buy — fill ($, fill vs the decision's
    market price, seconds to land, tx) → the agents' why (door, thesis, phase, sources, size) → the model's read nearest the buy → exit
    fills → real result → the Judge's ruling. An open trade claims no result. + `source_record` / `rule_record`: every source list and
    every exit rule (R4f / R4c included) graded on confirmed real exits only.
  · ALSO LIVE: memory half-seat (`brain.MEM_SIZE` 0.5: a coin in the worse half of our real trades takes half a seat, never none) ·
    source weight (`coach.source_factor`: every source of a coin a proven loser on real fills, n ≥ 8, typical ≤ −15% → ×0.9) · second look
    (a READY coin the rug-sniffer already flagged CAUTION goes behind the ones it did not, in the fill order — no call, never a block).
  New cause ⇒ add it to `opportunity.judge_hits` AND `coach.CAUSES` (a test checks the vocabulary is a subset).
- 🧾 ONE SALE = ONE REAL RESULT (2026-10-13, the "9 of 76 results don't match their path" trace): (1) a coin that left the card and came
  straight back left two or three waiting records and the ONE later sale closed them all — 12 of 77 archived "real results" were the same
  sale again (memory, the Judge, source / exit-rule records learned each twice). `office.confirm_exits(.., used=)`: the newest record of a
  coin takes the sale, older ones are filed `exit.state: 'duplicate'` with no result; `real_memory.trades` (used by coach records too)
  keeps one record per sale signature for the old archive. (2) the rest of the gap is REAL: the path is the last TRACKED move, the
  result is the fill — closed records now carry `gap` (real − last tracked). The ledger result was right every time; never "fix" it.
- ⏱ CALL → FILL IS THE LEAK, NOT THE EXIT LINE (same day, from the ledger + chain): decision → send median 89s (7 min on the newest 24),
  send → landed median 24s; 11 of 66 real trades were already past −15% at the FIRST look after the fill. `coach.line_replay` (payload
  `tradeTape.line`, 🧪 line under the tape) replays a tighter cut on every real path: −12% → avg −10.7% vs −11.8% real, 4 winners thrown
  away, median worse → NOT PROVEN, not shipped; it reads `pays` only from 40 trades, +3 pts on the average and no worse a median.
  Shipped instead: `_fw_catch_up` (a keeper pass asked for while one runs → ONE more pass the moment it ends, still one at a time) ·
  the tier tick hands the keeper its OWN clock · ⚡ urgent exits: `arena_prime.urgent_exit` stamps `agentOut[mint].urgent` on a
  protective agent exit, `fuse_wallet.mark_urgent` marks the keeper's sell (its `why` only ever read 'not on the card any more', so NO
  real exit was ever urgent), `priority_cap(.., urgent_usd)` lets its first try pay ≤ 1% of the sale, inside the same half-cent
  ceiling. Tape: `waitSec` per buy + ⏱ `speedMeters` (CALL → SENT · SENT → LANDED · FILL vs CALL PRICE). The remaining wait is
  Jupiter's free rate limit on the keeper's quotes (4 calls a buy, lanes resting on 429) — a paid Jupiter key is the fix, the owner's call.
- 📏 DIRECTIVES ARE GRADED (`coach.grade_note / grade_settle / grades / drop_wrong`, `_coach_grade` with the tape rebuild): every coin a
  live rule (owner · model · Judge) ranks down is noted once per 6h at the desk's price and judged 30 min later (no price for 2h =
  −100%); from 10 coins: `right` (they typically fell) · `wrong` (they rose 3%+). A MODEL rule proven wrong ends itself (logged); an
  owner's is only shown (`ctp-rgrade` chip). Stamp checks test the stamp exists first (`now - 0 < N` is true at now ≈ 0).
- 📈 NO STATIC LINES ON ANY CHART (`lib/chartLevels.js` pure + tested, `components/terminal/ChartLevels.jsx`, `styles/chartLevels.css`
  `clx-*`; drawn by `PriceChart`, so every chart has it): your fills + entry, a Fuse card's / the agents' entry · stop · lock · trail ·
  take · support · invalidation, Fee's read and the chart tools' levels are ONE list of live rows — a lit line with a runner, a tag
  with the price and the LIVE distance (▲ 3.2%), heat inside 2.5%, a one-shot flash when the price crosses, key levels off the scale
  pinned at the edge (under the vitals ring), overlapping tags pushed apart (`spreadTags`). ONE rAF loop ≤ 30fps writing transforms +
  text only when a value changed. Never call `createPriceLine` again: a new level ⇒ a row in `ownLevels` / `feeLevels` / `toolLevels`.
  The tools' soft bands are still `useToolDraw`. Cockpit seat board header: `OpenPnl` (`cockpit.openPnl`: every held seat's live P&L).
- 👁 THE COCKPIT CAN BE SEEN WITHOUT HQ: a scratch webpack bundle (node API, frontend node_modules, babel-preset-react-app, style-loader +
  css-loader `url: false`) rendering `<AgentDesk call={readOnly} />` on a COPY of `backend/data/agents_view.json`, served by a tiny
  GET-only static + proxy server on a FREE port (51399 was still held by an older session's server and served its 3-hour-old bundle —
  check `lsof -iTCP:<port>` first), screenshot with the cached Playwright headless shell. Scratch only, never shipped.
- 🤖 PAPER CARDS INHERIT THE AGENTS (owner, 2026-10-13: "have the engine build new strats from the agents' work — never waste the agents'
  time, just inherit"): pick style `agents` (`arena_prime.PICK_STYLES`, default for ⚡ Next Level — it was 👤 picks-like-you, −27% on
  $20). `_agent_inherit_rows` = the kernel's own READY then CONTENDING coins, best rank first (`_kernel_row` = the one candidate-row
  shape, shared with `_agents_go_rows`): what the ten agents already read, ranked and weighed this pass — no second scan, no model
  call, no fetch; the edge gate is skipped for it like the 👤 card; exits stay the tier's own. Paper only. A paper restart may deal
  it to any tier (`paper_reset.STYLE_PICK`). `PRIME_RESET` 'paper20c' = every paper tier card back on $20 once (runs archived to the
  record; the real card untouched). Its own record says whether the agents' list pays — never promote it without that.
  The model coach's case now carries what the desk MEASURED (`coach_case(.., grades_, exits, speed)`: each rule's own record, the exit
  rules' real results, call → fill timings; `ai_router.CASE_KEYS` + exits / speed).
- 📡 EVERY JUPITER KEY IS ITS OWN LANE (`JUP_KEY_ENVS`: `JUPITER_API_KEY`, `_2` … `_6` in backend/.env; `_jup_keys`, `_jup_lanes(list)`,
  `_jup_lid` = the lane's own pacing slot, base#N from the 2nd key): the keeper's quotes go to whichever lane is free, so N keys ≈ N
  requests a second. Before, only ONE key was ever read — a second key in .env did nothing. Distinct names (env_loader keeps the first
  value of a repeated name); restart the reputation service after adding one. Reads (`_jup_prices` / `_jup_tokens`) still use key 1 only.
- 🧬 THE MODEL SEES OUR OWN TWINS (`real_memory.twins`, case key `twins`, `_real_trades` 60s cache): each case it is asked about carries
  the real trades that looked most like this coin at entry (≥ 3 shared entry features) and how each REALLY ended. No extra call.
  THE AI'S REAL LIMITS (2026-10-13, say these before promising anything from it): asked ~0.1×/min · veto-only · its own ENTER calls
  fell a typical 39% · its rug read did not separate winners · it judges a snapshot and the fill lands 2 minutes later. Where a model can
  add: reading text (site / X / call thesis), and PROPOSING rules that the record then tests walk-forward — never picking coins itself.

- 🎛 THE OWNER'S BUY GATE + 🎯 ARMED SEATS (owner, 2026-10-13: "seat filling is the problem — fix controls and limits to really allow me to set
  stuff"; the paused session's WIP finished): realCfg `agentGapPct` 0/4/6/8 (buy ≤ X% over market; 0 = the agents' 2.5%) · `agentBackPct`
  0/5/7/10 (sells straight back ≤ X% lower; 0 = 3.5%) · `agentPoolMin` 0/3K/5K/12K/20K (smallest live pool; 0 = the keeper's $8K trench floor,
  never under $3K) — `fuse_wallet.set_agent_limits` (each tier tick) → `agent_limits(order)` inside `live_buy_market` + `buy_safety`: the seat
  pre-check and the keeper's final gate read the SAME limits. The no-route / honeypot / below-market checks never move. `agentCurve` on = an
  AGENT coin on a launch curve is judged on the curve's depth whatever the desk row said (READY curve coins were refused as "$2.4K pools").
  Entry `armed` (`office_edge.armed_fill`, `ARMED_SIZE` 0.5): a seat empty past the owner's target with fewer READY coins than empty seats
  takes the best CONTENDING coins Trigger ARMS (never WAIT / NO, never a 0-size hard veto, never a blocked coin) at HALF a seat, tag
  "🎯 ARMED (seat target)"; `_armed_fix_1013` switched the real card to armed + 15s target (old values data/realcfg_before_armed1013.json).
  HQ › Agents controls: 🛂 BUY GATE card with `GateLine` = the keeper's own refusals counted by the limit that refused them (`gateCounts`).
  The AgentDesk bottom bar = vital lenses first (Live · Review · Missed · Board) then 🎛 Limits ("N held back" badge).
- 🧪 THE RULE LAB (`backend/rule_lab.py` pure + tested; `_lab_tick` in the AI round, `data/rule_lab.json`, payload `lab` → `RuleLab` in the
  🧠 AI tab; owner: "the model proposes rules, the record tests them … let it name new causes … all agents need lessons"): tokens = the entry
  features our REAL trades are filed by (`real_memory.pos_feats`) + the buy / sell vital at the entry (`flow:`) + how far under its high
  (`high:top|near|off`; the entry thesis now keeps `flow` + `distHigh`). Once an hour ONE cloud call (role `lab`, never the local model)
  reads `vocabTable` and may propose ≤ 3 rules in those exact words; every rule is re-judged every 10 min with NO model call. LIVE = passes
  walk-forward on real fills (oldest 60% and newest 40% both ≥ 3 pts the rule's way, ≥ 6 / 5 matched) or — avoid only — fits ≥ 3 of the
  last 20 real losses without the replay contradicting it (a NEW CAUSE under the model's name). A live rule is its desk's lesson: rank
  ×0.88 (avoid) / ×1.06 (favor) through `_judge_weights`, and a live avoid rule on the entry MOMENT arms Trigger instead of entering
  (`brain.trigger(.., lab)`). Contradicted or 24h unproven = failed. Never an order, a size or a sell.
- 🔎 TEXT SCOUT + 📍 ASK AT THE FILL: every answer may carry `scout` {original, thesis real|swarm|none, site match|mismatch|none, tech 0–100}
  (`ai_router.parse_advice`, strict), judged like every read (`ai_learn` buckets SCOUT:COPY · SCOUT:SWARM · SCOUT:TECH · SCOUT:MEME) and shown as
  chips (`scoutChips`). A coin that just took a real seat is read once more on its live tape (`_ai['fillQ']` → `_ai_jobs` role devil,
  `atFill`), RECORD ONLY — its own bucket AT:FILL says whether a read at the fill is worth anything; it never undoes a buy.
- 🧪 The lab never waits on the model (`rule_lab.auto_propose`, every judge pass): any token on ≥ 10 real trades whose typical result sits ≥ 5 pts
  from the whole record's is proposed (≤ 2 a pass); the walk-forward still decides. Age at entry is a word (`fresh:<15m|15-60m|1-3h|3h+`, a
  timing word → Trigger's lesson). First run on the real archive (81 trades): favor `phase:PRE-FOMO` went live (+16.7% vs −12.2% unseen, n 6);
  avoid `struct:EARLY` FAILED (bad in the older 60%, better than the rest in the newest 40%). Reaper's exits learn on their own already
  (`office.judge_candidates`: real trades moved protectAt 6 → 4 and giveBackPct 50 → 35).
- 🧹 CHART TAGS NEVER STACK (`lib/chartLevels.spreadAround`, `LIVE_ROOM` 16): level tags are spread apart AND kept off the live price row (the
  P&L tag riding the candle + the axis's own price label); a tag moved off its own line is dashed (`.clx-tag.is-moved`). The owner's
  screenshot had seat P&L, entry and take tags on top of each other near the price.
- 😴 THE REGRET LEDGER (`backend/regret.py` pure + tested; `_regret_tick` once a minute in the agents' pass, `data/regret.json`, payload +
  stream `regret` → `RegretLine` in the 🛂 BUY GATE card; owner, 2026-10-13: "learn like you do from missed opportunities and tweaks … last
  forever untouched"): the missed-winner autopsy files only coins that RAN, so it can never say a block was wrong. Here EVERY coin a check
  blocked (pre-check refusals by `why_class`: gap · back · pool · route; the tape waits flow:PEAK / flow:SELLERS) is noted at its price
  beside every coin the desk TOOK (`taken`), and all are graded 30 min later (end %, peak, dumped; no price for 2h = −100%). TWEAKS, only
  where the owner left AGENTS: a buy-gate limit steps ONE notch looser (gap 2.5 → 4 → 6 → 8 · back 3.5 → 5 → 7 → 10 · pool $8K → 5K → 3K)
  when ≥ 12 blocked and ≥ 12 taken coins show the blocked ones ≥ 5 pts better AND dumping no more (+5); a tape wait switches OFF the same
  way and back ON when its blocked coins turn ≥ 5 pts worse; one notch per 6h; a tweak whose taken coins since did ≥ 5 pts worse is rolled
  back and rests 12h. `_regret_limits(cfg)` = owner value › tuned value › default, read by `set_agent_limits` and the kernel ctx `waits`
  (`brain.trigger(.., waits)`). The no-route / honeypot / below-market checks and every exit never move. Stamp checks guard a missing stamp.
- 🔑 Jupiter keys: each in its OWN name (`JUPITER_API_KEY`, `_2` … `_6`). 2026-10-13 the owner pasted two keys on one line as a second
  `JUPITER_API_KEY=` (the loader keeps the first value of a repeated name → both ignored); split into `_2` / `_3`, both answered 200 while
  key 1 was 429. Probe a key with one quote + one price call and print the status only.
- 📡 LAUNCH BOARD = PER-COIN FRESHNESS (`launchpad_board.due_mints / fresh_from`, `HOT_N` 180 · `HOT_SEC` 45 · `TAIL_SEC` 240; market.py board
  build + `jup_mem`): the board sorted ~660 mints ALPHABETICALLY into 30-mint batches whose cache key is the exact list — one new coin shifted
  every batch after it, so nearly all 22 batches missed on every 20s rebuild (1,493 DexScreener batch calls in 45 min, HALF refused 429; 755
  Jupiter searches the same way) and every list the agents read went stale. Now only DUE coins are fetched (hot every 45s, tail every 4 min;
  a coin Jupiter had nothing for is remembered as None); quiet-chain search top-ups cache 3–5 min. "LISTS STALE / 429" ⇒ count the market
  service's outbound calls by endpoint in /tmp/feeless-api.log first. Measured after that fix: still 144 batches / 150s, half refused — a
  refused batch left its coins due, so they were re-asked every 20s and the retries WERE the next refusals: now a refused coin rests
  `RETRY_SEC` 90 (`launchpad_board.resting`, `ds_try` / `jup_try`) and a build asks ≤ `DS_BATCHES` 4 DexScreener batches + ≤ `JUP_CALLS` 2
  Jupiter searches, hottest first. Restart ONE service by PID (`kill <pid>`; keep-alive restarts it): `pkill -f "uvicorn server:app"` inside a
  shell command also matches that shell's own command line.
- ⚡ CANDLE FX (`components/terminal/CandleFx.jsx`, `styles/candleFx.css` `cfk-*`, in every PriceChart except `plain` / fx-lite / reduced
  motion): the forming candle's aura rides its drawn close, every REAL tick (the bar's own close, never the eased value) throws a ring, a ≥ 1%
  tick bursts 6 sparks, a new candle flashes its column; the chart area gets `cfk-up` / `cfk-dn`. ONE rAF ≤ 30fps, transform / opacity only.
  Theme ⚡ Neon trench (`neon`): a neon grid floor rolling toward you + horizon + beams, the grid turns pink on a red candle (cfk-dn).
- 🛰 INTAKE BAND (`command/IntakeBand.jsx`, `lib/intakeBand.js`, `styles/intakeBand.css` `ib-*`; cockpit, under the chart, over the decision
  tape): every coin the kernel reads as a dot — across = live MC (log $1K–$1M, the owner's band shaded), up = IN → CONTENDING → READY → PICKED
  (dots glide up on transform; new coins pop; READY breathes; PICKED rings) + a lane funnel + intake /min. Tap → splash: MC · age · 5m ·
  buyers · pool · 5m vol (bad ones flagged), Devil's first objection, the model's read + scout chips, and ⚡ ARM · 📌 TRACK · 🔎 REVIEW ·
  ✕ IGNORE (the owner-review route) · 📈 CHART. Drawn from the kernel's own state; it decides nothing.
- 🎓 TEACH THE DESK (`backend/teach.py` pure + tested, `data/agent_teach.json`, POST /admin/agents `{teach: {kind, text, mint?, sym?, img?} | {remove}}`
  (creator only), payload `teach` → `command/TeachBox.jsx` + `styles/teachBox.css` `tch-*` stacked under the coach box): the owner's 💬 notes,
  📖 narratives (key words → coins whose ticker / name carry them) and 📈 chart lessons (caption + an image from OUR upload store only) go
  into every fitting model case (`_ai_case` → `lessons`, the lab's case too); every read on a coin the owner taught is graded in its own
  ai_learn bucket TAUGHT, so the record says whether the teaching helps. The text model reads captions, not pictures (a vision provider would
  be needed for the image itself). Never an order, a size or a sell.
- 🎯 CHART SAYS GO (2026-10-13, real card 107 agent trades / 24h: chart call ENTER NOW n10 +14% typical, 70% won, +$0.48; WAIT FOR PULLBACK
  n26 −13% · WAIT FOR DATA n6 −29% · SKIP n9 −10% (bought anyway in open trenching) · stops + gaps were the whole −$2.57): `brain.trigger`
  turns ENTER / ARM into WAIT when the coin's chart call is not ENTER NOW (`CHART_GO`, so armed fills can't take it either); no chart read =
  half a seat (`NO_CHART_SIZE`, Warden). Owner switch realCfg `chartWait` (🛂 BUY GATE card, "🎯 Chart says go"); the regret ledger grades
  every chart-held coin (`chart:WAIT`) beside the taken ones and may switch it off (WAITS) — then back on when it is right again.
- 🩹 A RATE LIMIT IS NOT A RUG (2026-10-13): Jupiter's public price lane answered 429 nearly every time from this machine, and `_jup_prices`
  dropped every batch after a failed one → 62–71% of watched coins and ~58 of every 60 settled list / call / read records were "−100%"
  (busted reads → Devil hard vetoes, paused lists, fake rug signs, agents scrapped on losses that never happened). Now: one refused batch
  never drops the others; result graders read with `judge=True` (`_judge_fill`: the candles service's live price → the launch board's last
  build → a ≤ 5-min Jupiter reading); vanished = no price from ANY source for 15 min (`trench_brain.GONE_SEC`, `paper_desk.GONE_SEC`, else the
  last move). Old records were NOT rewritten — they roll over within hours. "EVERYTHING READS −100%" ⇒ curl the price sources for those mints first.
- 🔑 THE READ KEY (`backend/jup_keys.py`): with ≥ 3 Jupiter keys the LAST (or `JUPITER_READ_KEY`) is for price / token READS; the keeper's lanes
  (`_jup_keys`) are the others. The candles service read every chart price with key 1 (the keeper's), ONE coin per call — now every read waiting
  in the same 0.5s goes out as ONE batched call (`_px_batcher`, ≤ 50 coins) on the read key → public → DexScreener. Seat P&L, the fast stop guard
  and exits all read that price: a refused price = a stale seat. New Jupiter read ⇒ `jup_keys.read_key`, never `JUPITER_API_KEY`.
- 🩹 THE GRADERS' PRICE READ TIMED OUT (2026-10-13, the reason "a rate limit is not a rug" did not hold): `/api/candles/prices` fed the
  batcher 8 coins a window (a leftover 8-at-a-time limit), so a 60-coin read cost 8 upstream calls and 5–7s, while `_live_px` gave up at 3s
  and returned NOTHING — every grader (trench brain, list / call / entry / edge / flow proofs, paper desk, shadow book) then filed live coins
  as vanished (16 of 16 "gone" coins checked had a price). Now: every coin joins ONE batch (60 = 2 calls), a queue over 50 goes back to back,
  `LIVE_PX_BULK_SEC` 8 for reads > 12 coins, a refused Jupiter lane rests (`_px_rest`, its Retry-After or 6s) instead of being asked every
  half second. `trench.meta_track`: a coin with no price when due waits `PROOF_GONE_SEC` 15 min before it is −100% (it was instant).
  `_proof_clean_1013` (once, flag data/proof_clean.json, old rows data/proof_before_clean1013.json): every 1-hour paper record's SETTLED rows
  restart (45–80% were fake −100%); the trench brain learns and the edge audit / proof gate judge only coins settled since its `cleanFrom`
  (`edge_audit.audit(since=)`, `_brain_clean`; left out WHOLE — never just the bad rows). Under 500 clean coins the gate reads "wait".
  "A RECORD READS −100% TYPICAL" ⇒ time one 60-mint call to :5099/api/candles/prices and compare with the caller's timeout first.
- 🧊 A CANDIDATE OFF THE DESK STEPS DOWN (`trench_kernel.kernel.STALE_SEC` 90, `Kernel.stale`, decision flag `stale`): a mint the desk has not
  re-read for 90s is TRACKING ("off the desk for Ns"), is no case file and no page row, and is judged again the pass the desk reads it; a live
  price event alone never makes it a candidate. Found in the card's own events: Lynk was "2 min old, +3% on 12× volume" at 15:36, 15:46 and
  16:01 (it had died to its $3K floor at 15:52) — 15 of the top 24 candidates had readings 15–66 min old and armed / READY fills came from them.
  🎯 The seat pre-check also judges the owner's band on the LIVE cap ("live cap $2,993 is outside your $12K–$500K band").
  💧 `fuse_wallet.buy_floor(order, cfg)` = THE pool floor for the pre-check, the live gate AND `check`: the missed-opportunity ledger had tuned
  the agents' floor to $5K, `check` still read $8K → a coin passed, took a seat, was refused seconds later, on a loop (6 of 11 refusals / hour).
  "SAME COIN SEATED AGAIN AND AGAIN" ⇒ read the card's agent-fill events: an identical rank / "N min old" twice = a frozen reading.
- 🧨 DEGEN IDEAS = PAPER-FIRST STRATEGIES (`paper_desk.STRATS`, drivers `strat:<k>`, no starting belief — only their own judged record weighs;
  shown with the other drivers): `base_crowd` (launch phase PRE-FOMO, flat 5 min, buyers ≥ 58%, holders growing) · `pro_first_call` (a PROVEN
  Pump caller on it, ≤ 2 callers so far; row `pros` from the call board) · `wave_original` / `wave_copycat` (row `waveRole` from
  `meme_terms.wave_roles`: the biggest-then-oldest coin of a ticker wave leads, the rest copy). First dip after bonding, real callers stacking
  and the clean dip catch were already there (2026-10-13 5-min records: +1.1% n13 · −10.6% n51 · −4.8% n15; volume burst −34.7% n115).
  House money at 2× is an EXIT that already exists (`houseAt` / moon ladder), not a selection rule. None of them touches real money by itself.
- 💰 CAPITAL DESK (`backend/capital.py` pure + tested `tests/test_capital.py`; owner, 2026-10-13: "agents must be taught capital management and
  how to grow faster"; realCfg `agentCapital`, on by default; `_capital_view` → payload `capital`, Warden ctx `capital`, the model coach's case
  `capital` line): size follows the agents' own last 30 CONFIRMED real exits — win rate, avg win, avg loss, payoff, expectancy, Kelly.
  🧪 PROVING (< 12 exits, or winning with < 20) = seats as before · 🛡 PROTECT (Kelly ≤ 0: the average bet loses) = Warden rule `W23 capital`
  ×0.25 and uncertain coins may shrink to ×0.25 · ⚖ STEADY (winning by a hair: half-Kelly of the card < ¾ seat) = ×0.5 · 🚀 GROW (20+ exits,
  half-Kelly ≥ ¾ seat) = ×0.75 / ×1 and an uncertain coin may take ×0.75 instead of ×0.5 (`trench_crew.warden_rules(rules, floor)`).
  Never more than the card's own seat (allowed ≤ requested stands); execution rules W1 / W3 / W17 / W11 / W22 untouched; a seat is a share of
  the card NOW, so winnings compound by themselves. `leaks` = which exit rules lost the window's money (the lesson). Page: `CapitalMeter` +
  the `agentCapital` switch in 🪑 SEATS & ENTRY (`capitalRead` in lib/cockpitControls.js). FIRST READING (114 real agent exits): all-time
  40% won, +20.9 / −26.8, Kelly −0.36 → no size was right; last 30: 57% won, +15.8 / −19.1, payoff 0.83, +0.7% a bet, Kelly 0.04 → STEADY;
  the 20 exits after the chart gate: 65% won, +15.3 / −11.2, payoff 1.36 (thin). 112 of 114 seats had been ×0.5 whatever the record said.
  THE PAYOFF IS THE PROBLEM, NOT THE SIZE: stops (R5 / R5x / R1) lost $3.68 of a net −$0.85 — losses fill ~−27% against −12…−25% lines.
  Growing faster = a smaller average loss or a bigger average win; pressing size on a 20-trade record is how the card went $28 → $0.47.
- 🕯 THE FORMING CANDLE IS NEVER EASED (owner, 2026-10-13: "current candle morphing before it becomes its true shape — can't have that"; this
  REPLACES "PriceChart eases the forming candle's body to each real tick at 30fps"): `PriceChart` redraws the live candle ONLY when a real
  price tick lands (the stream re-reads the price right after each on-chain swap) and at exactly that price — no in-between frames, no rAF
  loop in the chart. `tweenClose` stays for number tickers (`lib/easedNumber`) only; a test fails if the chart imports it again.
  NOT built: candles assembled from the swaps themselves (every fill's own price) — that needs each pool's swaps read from RPC, the daily budget.
- 👁 REAPER'S REPLAY WAS BLIND PAST ITS OWN SALE (2026-10-13; `backend/after_path.py` pure + tested, `data/after_paths.json` MemStore): the
  self-tuning (`office.judge_candidates`) replayed each real position's path — which ENDS at the exit — so a tighter trail could only look
  as good or better and a wider one could never show what it would have kept. That is how protectAt walked 6 → 4 and giveBackPct 50 → 35
  while winners banked +2% (YUNG peaked +15.4%, banked +1.7%). Now every confirmed agent exit is watched 30 more min (`watch` / `step`, one
  reading / 30s from the live chart price, no price for 5 min = −100% from there); `judge_candidates(.., after=)` proposes AND shadow-tests
  on path + after only (a position counts once its after-path is filed, keyed per position); `after_path.grid` = every arm × give-back pair
  on the whole moves → payload `trail` → 👁 TRAIL LAB in 💰 EXITS (`trailRead`). Under 30 whole moves it says nothing. Nothing ships
  without the existing propose → 20-exit shadow → promote path. ANY "replay on our own paths" must ask: does the path end where WE left?
- 🧠 THE MODEL TUNES REAPER — INTO SHADOW ONLY (`ai_router.TUNE_KEYS`, advice `tune` {key giveBackPct | protectAt | stopPct, dir up | down, why};
  `office.model_candidate`: ONE grid notch, refused when a candidate is in shadow / < 10 whole moves / judged in 24h / no notch left;
  queued as `_coach['tuneAsk']`, applied in `_office_pass`, tape line AI TUNE). The coach's case now carries `capital` (record · by door ·
  brake · leaks), `trail` (live vs the top 3 pairs) and `tunes` (Reaper's live settings), and it runs when the MONEY asks (capital PROTECT,
  the brake on, or the trail grid leaving ≥ 1 pt a trade) — not only after two real losses. The model still never sizes, orders or sells;
  a shadow test on trades it never saw decides. `real_memory.door` knows `armed` / `ready` (every seat since 2026-10-12 read 'other', so
  the memory, twins and the rule lab had no door word).
- 💰 CAPITAL v2 (`capital.py`): SIZE BY DOOR (`doors`, `for_door`: 🎯 armed / ⚡ ready each on its own last 30 real exits once it has 12;
  the Warden's W23 reads the fill's own door) · an ARMED fill = ×0.5 of the Warden's size, ×1 once the armed door's own record is GROW, ×0.25
  while it is PROTECT (`armed_size`; replaces the flat `office_edge.ARMED_SIZE` at the fill) · 🧯 DRAWDOWN BRAKE (`brake`, `BRAKE_PCT` 15: card
  ≥ 15% under its 24h high (office `peaks`) → every fill ×0.25 until it climbs back or the high rolls off; on a ~$4 card that is below what
  W22 "size too small for costs" lets through, so the brake mostly means NO new buys — intended: stop digging). A withdrawal lowers the
  card's value and can trip it for ≤ 24h; the `agentCapital` switch turns all of capital off.
- ⚡ AGENT SEATS ARE GUARDED ON THE LIVE PRICE, EVERY 3s (`AGENT_GUARD_SEC`, `_real_guard_loop`): `fast_reap` judged the agents' coins on
  `_jup_prices`' shared 20s cache (a 6s loop on a ≤ 26s-old price) — real stops set at −12…−25% were FIRST SEEN at −21…−84%. The guard now
  merges `_live_px` (the chart's own price, ≤ 5s old, 1s after a swap) over it and loops every 3s while an agent seat is held.
- 📡 `backend/jup_rest.py` (market service only, `install()` after ds_pace): a Jupiter READ lane (host + key + `/tokens/` | `/price/`) that
  answers 429 rests its Retry-After (else 8s); a call to a resting lane answers 429 at once with no network request. Quote / swap paths are
  never touched. 2026-10-13: 536 token lookups in 21 min, every one refused, half a second apart.
- ☠ CAPITAL v3 = SIZED FOR THE RUG (2026-10-13, the same evening capital v1 shipped: a 30-exit streak with no rug in it read GROW, seats went
  ×0.5 → ×0.75 ($0.53 → $0.85), and $X — 2 min old — went −85% in 47 seconds: −$0.72 = 17% of the card; $PEVEIL −77% in 41s; 15 other trades
  made +$1.19 that window). 134 real agent exits: 18 rugs (13.4%, avg −74%), spread over EVERY age / class / phase bucket; no selection rule
  held walk-forward (LATE FOMO lost in the older 60% and won in the newest 40%). So: (1) the LONG record (`LONG` 150 exits, rugs included, from
  `LONG_MIN` 50) is the CEILING — the 30-exit window may lower the stance, never lift it past the long one (`capital.view`); (2) a door may
  size DOWN from the desk's stance, never up; armed fills earn ×1 only when desk AND door are GROW, and are not halved again once the seat is
  already the smallest; (3) ☠ RUG BUDGET (`rugs`, `RUG_BUDGET_PCT` 8, Warden rule `W24 rug budget`): one rug may cost ≤ 8% of the CARD →
  a seat ≤ 8 ÷ avg rug loss (≈ 10.8% of the card today), whatever the stance. THE WHOLE SEAT IS THE RISK ON A LAUNCH COIN — never size from a
  stop line or a short window again. Today this reads PROTECT (long record −5.1% a bet): quarter seats until the long record turns.
- 🧠 THE MODEL WAS BARELY ANSWERING (same day): Groq's free plan = 8K tokens a MINUTE; two ~3K-token cases a round fired together, the second
  was refused, the provider "cooled", and 5 of 6 asks came back NONE (0.1 calls / min, the coach had said nothing). `ai_router`: the provider's
  own `x-ratelimit-remaining-tokens` / `reset-tokens` are remembered (`_budget_note`), a call that would not fit WAITS for the reset
  (`budget_wait`, ≤ `BUDGET_WAIT_MAX` 20s) instead of firing into a 429, a short Retry-After is waited out once, Groq runs one call at a time.
  "THE AI ISN'T HELPING" ⇒ read `office.ai.totals` (asked vs answered vs none) and the provider state before anything about its judgement.
- 🛂 THE MODEL READS BEFORE THE SEAT (`_ai_gate`, `ai_router.gate_verdict / cloud_ready`, realCfg `agentAiGate` on by default; switch in
  🧠 MODEL): 2026-10-13 the trade tape showed the model had read NONE of the last 24 real buys before the buy — its reads came a round
  later, for display. Now the coins about to take a real seat get their read first: a fresh one (≤ 5 min) is used, a missing one is asked
  NOW (cloud only, in parallel, ≤ `AI_GATE_SEC` 7s; a late answer is kept for the next tick). A STRONG, SPECIFIC CAUTION
  (confidence_delta ≤ −0.12 with a named risk) holds that coin back this tick; silence, a slow answer, no cloud provider = the coin goes.
  Graded by the regret ledger as `ai:CAUTION` (`aiWait`): it switches the wait OFF when the coins held back keep beating the ones taken.
  It can only make the agents buy LESS. `AI_JOBS` 3.
- 🧠 PROVIDERS, MEASURED (same day): Groq's free plan has a 200K tokens-a-DAY cap — it was spent, so every ask came back NONE whatever the
  per-minute pacing did (read the 429 BODY: "tokens per day"). OpenRouter (the owner's key, `OPENROUTER_MODEL`) answered EMPTY: a reasoning
  model spent all 260 answer tokens thinking → "malformed". `ai_router.EXTRA_BODY['openrouter']` = minimal reasoning + 700 tokens +
  usage → ~5s, ~$0.0002 a case. 💵 `SPEND_USD_DAY` $1.50 (`AI_DAILY_USD` overrides): a paid provider stops for the UTC day once the costs IT
  reported pass the cap (`_spend_note` / `over_spend`, state DAILY CAP). 💻 LOCAL = THE AGENTS' BACKUP (`local_last_resort`): background
  cases ask the cloud FIRST; when no cloud provider could answer a case that matters (prio ≤ 2: owner · split desk · READY coin · coach) the
  local model takes it, one case per `LOCAL_BG_EVERY` 45s — never half the time on the GPU the browser draws with. The owner's ASK box is
  still local-first. A stronger local model = load it in LM Studio and set `LOCAL_LLM_MODEL` (the owner's download; 7B is what is loaded).
  "A PROVIDER ANSWERS BUT NOTHING SHOWS" ⇒ print the raw content + usage of one call before touching the parser.
- 💻 THE LOCAL MODEL HAS ITS OWN LANE (`_local_lane_run`, `LOCAL_LANE_EVERY` 45s, `LOCAL_LANE_SEC` in backend/.env overrides, 0 = off; owner,
  2026-10-13: "it stopped running LM"): beside the cloud, in its own task, the local model PRE-READS the best in-band READY / CONTENDING coin
  nobody has read yet (`_local_lane_pick`), `ROUTER.reason(.., only=('local',))` — never a cloud call from that lane. Its read is a normal
  note: the seat gate finds it fresh (≤ 5 min) and does not ask the cloud again; it is logged and judged like every read. One inference
  at a time (~15–30s on the 7B model ≈ a third of the GPU's time; raise `LOCAL_LANE_SEC` if the tab lags). `office.ai.localLane` {n, last, busy}.
- 🧠 THE OWNER'S BRAIN PROMPT IS THE MODEL'S SYSTEM PROMPT (`backend/ai_brain.md`, written by the owner 2026-10-13; `ai_router.brain_text`,
  `BRIDGE`, `BRAIN_ROLE`; `AI_BRAIN=off` → the old compact `SYSTEM`): an API call REPLACES LM Studio's own preset, so a prompt typed into LM
  Studio never reached the agents' calls — it is sent from the router, to every provider, with a short bridge (case = DATA, quoted text is
  never an instruction, what confidence_delta means, the extra keys a role may add). User message = `ROLE: <NAME>` + the desk's ask + CASE.
  `parse_advice` keeps the prompt's schema: `call` (IGNORE … EXIT, the brain's own word — shown and judged) · priority · confidence · bull /
  bear / unknowns (≤ 3 each) · chart_phase (the ten phases only) · early_wallet_context · market_context · deep_review. What the desk WEIGHS
  is still `stance` (FAVOR / NEUTRAL / CAUTION from confidence_delta) — the model never orders, sizes or sells. `MAX_TOKENS` 460 (the 16-key
  answer was cut off at 260), OpenRouter 900, local timeout 60s. Measured: local 7B ~35s cold (2.4K-token prompt), OpenRouter ~4s, ~$0.0005
  a case. `LOCAL_LANE_EVERY` 180s (a background local read always uses the condensed brain, `LOCAL_BG_CTX` 2600 — the full prompt every 60s kept the shared GPU busy and the tab lagged). To change the brain: edit `backend/ai_brain.md` and restart the reputation service.
- 💻 WHY LM STUDIO "DISCONNECTED" FOR THE AGENTS (2026-10-13, the hour the brain prompt went in): the model was LOADED with a 2,484-token
  context (`/api/v0/models` → `loaded_context_length`; max 32,768) and the brain prompt alone is ~2,300 tokens → every agent call got HTTP 400
  "tokens … greater than the context length" → state OFFLINE + cool-down, the local lane never ran. Now `Router.local_ctx` asks LM Studio
  what is loaded (2-min cache; `LOCAL_LLM_CTX` / `LOCAL_CTX` 4096 as fallbacks) and `messages_local` sends the FULL brain when it fits, else
  `BRAIN_LITE` (the same brain condensed, ~1K tokens with the bridge) + a case trimmed field by field (`LOCAL_TRIM`) until it fits; a 400
  re-reads the context and retries once at 70%. Measured: 14s an answer at 2,484. FOR THE FULL PROMPT: reload the model in LM Studio with
  context 8192 — the router picks it up by itself. The 7B model answered "EXIT, −0.25" on a plain case: it CAN clear a coin (saves a cloud
  call) but can never hold a seat by itself — `gate_verdict` asks the cloud for the second read when only the local model objects.
  A chat typed INTO LM Studio uses its preset (the JSON schema for every question); the agents' calls never see that preset.
- 🧭 AI ROUTER = TWO MODES (owner, 2026-10-13; `ai_router.MODES`, `mode_of`, `is_case_packet`, `Router.ask`, `messages_general`, `GENERAL_SYSTEM`,
  `clean_answer`): CASE = a real coin / position / desk packet (a mint · a symbol with trading fields · the coach / lab packets) → the brain
  prompt + `parse_advice` (validated JSON); every trading call in the service passes `mode='case'` EXPLICITLY (a test reads the source).
  GENERAL = everything else — the provider health check (`Router.test`: "reply with the single word ONLINE", any non-empty text = ONLINE),
  a model / owner question, agents coordinating — a plain-language system prompt, the answer returned as `text` (never parsed, cached or
  noted on a coin). `reason()` with no mode = GENERAL unless the packet is unmistakably a case. `POST /admin/ai/ask`: a CA / link → CASE as
  before; anything else → GENERAL with a few desk facts as context (`_ai_general_context`: card, capital line, trail, Reaper's settings,
  providers) → `{mode: 'general', answer: {text}}`; the ASK box shows it as prose (`cai-general`). New model call ⇒ say its mode.
- 💬 AI / LM CHAT + OWNER-APPROVED AGENT UPDATES (owner's spec, 2026-10-13; `backend/ai_chat.py` pure + tested `tests/test_ai_chat.py`;
  `command/AiChat.jsx` on top of the 🧠 AI tab, `cch-*` in cockpitAi.css; owner routes `GET|POST /admin/ai/chat`, `POST /admin/ai/chat/clear`,
  `POST /admin/ai/proposals/decide`). Three modes: 💬 CHAT (router GENERAL mode: normal language + the short conversation) · 🔎 CASE REVIEW
  (router CASE mode on the coin on the chart) · 🛠 AGENT IMPROVEMENT (GENERAL + `IMPROVE_ASK` → `parse_improve` → PENDING proposals).
  The model sees `ai_chat.context` only: the ten agents (gen · status · record), newest decisions, seats, the selected coin (missing
  vitals = the WORD UNKNOWN / PENDING), execution health, recent real results, capital + trail — ~2K chars, cached 20s. History = the last
  8 exchanges, in memory, gone on Clear / restart. A PROPOSAL changes nothing: {agent, kind, key, old, new, reason, effect, rollback} waits
  for ✅ / ✕. `_ai_proposal_apply` is the ONLY apply step and only for `ai_chat.KINDS`: `cfg` (`SAFE_CFG`: agentAiGate · agentAiLearn ·
  chartWait · agentCapital · agentDial) · `lesson` (teach.py) · `weight` (a coach rule on a vocabulary cause) · `tune` (one Reaper notch →
  SHADOW only) · `idea` (filed, applies nothing). Any key matching `ai_chat.PROTECTED` (slippage · gap · sell-back · pool · wallet · limits ·
  sizes · seats · stops · orders · keys …) is refused at parse AND at approval; decided once; `data/ai_proposals.json` keeps ≤ 60 compact
  records (never a raw prompt / response). One chat answer at a time (`_chat['busy']` → 429). The panel keeps its own state: a reply never
  touches the agent hub (test). New proposable thing ⇒ a kind / a `SAFE_CFG` key + its branch in `_ai_proposal_apply` + a test — never a
  generic "set any config" path.
- 🛂 The seat gate ignores the "organic / bots" flag when it is the model's ONLY named risk (`ai_router.GATE_SOFT`): Jupiter reads nearly
  every Pump coin 0–3% organic, so the model flagged it on everything and READY coins stopped being seated; with nothing taken the regret
  ledger had no baseline to switch the wait off. A specific risk (dev holds 79% · top-10 93% · site mismatch …) still holds the coin.
- 🧠 THE BRAIN = the chat, rebuilt (owner, 2026-10-13: "not that little section — meta and degen, something that learns and can fix agents on my
  call, in the mini cat for the creator"; `command/AiChat.jsx`, `styles/brainChat.css` `cch-*`, `components/MiniBrain.jsx`, `lib/hqCall.js`).
  ONE component, three places: 🧠 AI tab in HQ › Agents (`variant="full"`) · the mini cat's 🧠 Brain tab (`FeeCatWidget`, CREATOR ONLY via
  `useIsCreator`; `variant="mini"`, panel `is-brain` 440px, fixes folded under one bar) · ⤢ a full-window pop-out (portal `cch-shade`, chat |
  fixes side by side, Esc closes). Header = spinning orb + a mood read from real state (`brainMood`: 🟢 LOCKED IN provider · model · latency ·
  ⚡ COOKING · 💤 NO MODEL) + 🎓 LEARNED (lessons on file) + 🛠 YOUR CALL (pending fixes). One-tap prompts per mode (`QUICK`). LEARNS on the
  owner's tap: 🧠 Remember on any model line → `POST /admin/ai/chat/remember` → a teach `note` every fitting model read sees (the owner's own
  tap is the approval; never a setting). ✕ on a message → `chat/clear {index}`; 🗑 clears all. FIXES agents only through the proposal cards
  (✅ / ✕). Outside HQ the calls use the HQ session the creator already signed (`hqCallFor` reads `feeless:cc-session`; no session = "open HQ
  once", it never asks a wallet to sign). transform / opacity only (0 other animations, measured), fx-lite / reduced motion / day / 640px.
- 🧠 The Brain's place in HQ › Agents = the cockpit's tape zone, under the 🎬 trade tape (`ack-tapecol`, `variant="full"`) — NOT inside the
  small 🧠 AI panel tab (owner, 2026-10-13: "AI / LM chat in the Agents tab here"). The AI tab keeps the decision log, the ASK box and the
  rule lab. The Brain reads its own chat state once (`GET /admin/ai/chat`) — the desk itself is still fed by ONE request.
- 🗂 COCKPIT DECK + 🧱 BUILD MODE + 💓 LOCAL HEARTBEAT + ⚙ HOME ENGINE (owner, 2026-10-13: "alive layout, less scroll, less reading unless it's decisions and AI"):
  · HQ › Agents tape zone = `Deck` (AgentCockpit.jsx, `ack-deck*` in coachTape.css): 🎬 Trades · 👑 Coach · 🎓 Teach share ONE tab row (counts from the
    payload, pick remembered `feeless.agentDeck`, every pane stays mounted + hidden) with the Brain always beside it. A new secondary box ⇒ a deck tab,
    never another stacked block.
  · Brain = FOUR modes (`ai_chat.MODES` + `build`; each wears its own colour, `cch-scan` runs only while the model answers). `ai_chat.CHAT_ASK` = the chat
    voice (verdict first, every claim a number / agent / coin from CONTEXT, ≤ 5 lines, no consultant lists — the 7B model had answered "improve decision
    accuracy · monitor and adjust"); `route_mode`: a chat message that asks for a change ("can you fix?") runs as 🛠 Fix agents → proposals. 🧱 BUILD
    (`BUILD_ASK`, `parse_improve(only=('idea',))`): the models propose what to build (a vital, a meter, a check, a test) — filed as ideas, nothing applied.
  · 💓 `ai_router.Router.heartbeat` (called from `_local_lane_run` every AI round): while LM Studio is not ONLINE, ONE cheap model-list GET per 45s (no
    inference) → ONLINE again, cool-down cleared. One slow answer used to leave it OFFLINE until the owner pressed Test.
  · ⚛ THE FUSE REACTOR = `components/HomeEngine.jsx` + `styles/homeEngine.css` `hen-*` (Home, under the $FEE hero; the first belt version read like
    another product's — owner asked for a unique FEELESS idea): REAL coins from `/fuses/trench/open` ORBIT a core — outer ring ⚠ failed the scan, middle
    ❔ not read, inner ✅ safe (`reactorRings`); the core holds the runners live and beats faster the greener the board (`beatSec`); gate bars 🛰 → 🔬 →
    ✅ → 🏃 + meters from `/fuses/forecast` + `/runners`. Each pod = an orbit rotation + an equal counter-rotation; the counter element needs a REAL box
    (2px) — the FX governor pauses animations on boxless elements and the pods tilted out of sync.
  · SEATS EMPTY that evening = the owner's own 🎯 Chart says go switch: all 5 contenders were ARMED then held by the chart call (seat reason "timing (5)").
    It was NOT loosened: since that gate the armed door reads 60% won / +7.9% a bet. Read `office.seat.blockers` before touching a fill rule.
- 🧭 AGENTS TAB DOCK (`command/LensDock.jsx` + `styles/lensDock.css` `lnd-*`; owner: "tabs at the bottom more usable, every Agents tab needs live
  visuals, no crazy reading"): the lens tabs moved from a sticky BOTTOM bar to a sticky TOP dock (icon + word + live badge, ← / → walk them), and every
  lens opens on `LensVitals` = four live tubes from the payload (`lensVitals(lens, d, cnt)`, pure + tested; "—" + empty tube when a number is missing).
  New lens ⇒ a `lensVitals` case. Brain chat clean-up: one-tap prompts fold once you are talking (⚡ in the form brings them back), the mini shows mode
  icons only. 💓 LM Studio: heartbeat every 20s while not ONLINE + one forced re-check before every chat answer.
- 📋 BUILD QUEUE — READ `backend/data/build_queue.json` AT THE START OF A SESSION (owner, 2026-10-13: "do me approving actually build?"): an approved 🧱
  build idea (`_ai_proposal_apply` kind idea) or any model line the owner taps 🧱 Build this on (`POST /admin/ai/build`) is QUEUED there with its text;
  the owner's tap is the permission to build it. The model never writes code in the app. "build the queue" = build every queued item now. When you ship one, set it `shipped` (`ai_chat.build_set`, or
  edit the file while the service is stopped) and say so; `dropped` = the owner's ✕. 🧵 The Brain keeps ONE THREAD PER MODE (`_chat['th']`,
  `ai_chat.push_thread`, ≤ 6 exchanges each): chat · case · fix · build never mix. Decided fixes fold under "N decided". `CHAT_ASK` rule 5 = money
  first (capital / record lines outrank one coin; outcomes are CLOSED trades) — the live Qwen test answered from the capital line after it.
- 🧠 BRAIN v3 (owner, 2026-10-13: "pop-out must work over everything, real edit, new chat, add image, switch models, readable"): the pop-out shade is
  z-index 6000 (above the HQ pop-out's 4000 — it opened BEHIND it), 96vw × 92vh, chat | side (build queue + fixes) columns. Header: 🤖 model switch
  (`cch-model`, remembered `feeless.brainProv`; the chat POST sends `provider` → `ROUTER.ask(only=(key,))`) + ＋ New chat (clears this mode's thread).
  ✏ Edit on your own message = `chat/clear {mode, from: i}` (rewinds the thread) + the words back in the box. 📎 picture: our own upload store only
  (`_chat_image`: `/api/reputation/uploads/<hex>.<ext>`, ≤ 4 MB) → sent as a data URL to a CLOUD model that can see images
  (`ai_router.with_images`; the local text model is skipped; `est_tokens` counts a picture as ~1K tokens). Image GENERATION is NOT built (no image
  model / key wired). Ideas show only BUILD (no "now: nothing" row); why · effect · rollback sit in a fold; the normal-size side is capped at 210px so the
  chat keeps its room.
- 🧠 BRAIN v4 (owner, 2026-10-13): 👑 Coach + 🎓 Teach live INSIDE the Brain (`AiChat extras` → `cch-panes` 💬 Talk · 👑 Coach · 🎓 Teach; the cockpit
  deck beside it is trades + loss map only). Threads, saved conversations and settings persist in `data/ai_chat_state.json` (`_brain_load` — NOT `_chat_load`, that name is the social chat loader; reusing it broke the rooms /
  `_chat_persist`): ＋ New files the current thread (`ai_chat.save_convo`, ≤ 20), 🗂 reopens one (`POST /admin/ai/chat/open`). ⚙ settings
  (`POST /admin/ai/chat/settings`, `ai_chat.clean_settings`): 🌡 temperature 0.1 / 0.3 / 0.6 / 0.9 + 📏 answer 250 / 600 / 1200 tokens → the OWNER's chat
  calls only (`ai_router.TUNE` contextvar; background agent reads keep 0.1) · 🤝 SMALL THINGS (off by default): the model's `lesson` + `idea` proposals
  apply at once, marked "🤝 auto"; switches, rank weights and exit notches still wait for ✅. No sideways scroll: every `.cch` child may shrink.
- 🎨 THE BRAIN DRAWS (`ai_router.Router.gen_image`, `IMAGE_MODEL` google/gemini-3.1-flash-image, `OPENROUTER_IMAGE_MODEL` overrides; owner
  `POST /admin/ai/image {prompt, mode}`; 🎨 button beside 📎): OpenRouter chat completions with `modalities: ['image', 'text']` → the data URL is saved
  in our upload store and lands in the thread (meta.img), counted in OpenRouter's daily spend cap, audited. 2026-10-13 the owner's OpenRouter account
  answered 402 "requires at least $1.00 in balance for image or video output" — the provider's own reason is shown as is. GIFs: no image model
  outputs animation; NOT built.
- 🧵 BRAIN WITHOUT GLITCHES (2026-10-13; owner: "chat tabs not glitchy, no lag"): `AiChat` is `memo` and its log is its own memoized
  `ChatLog`; the cockpit hands it `brainExtras` from a `useMemo` keyed on coach / teach / ai / the HELD coins (a new extras array every
  hub paint re-rendered the whole log ~2.5×/s). Talk stays MOUNTED behind 👑 Coach / 🎓 Teach (`.cch-talkpane[hidden]`: switching panes
  used to remount + re-scroll + replay every message). Only what you just sent + its answer animate (`.cch-msg.is-fresh`, `markFresh`);
  a mode switch replays nothing. Fixes fold outside 🛠 / 🧱 (`sideOpen`) — and `.cch-props ul[hidden]` is needed: `display: grid` beat the
  hidden attribute, so the "folded" list never folded and squeezed the log to ~100px (now ~260px). Any `hidden` on an element whose
  class sets `display` needs its own `[hidden] { display: none }`.
- 📡 Empty seats = `HuntLine` (radar sweep, rotate only; headline = the blocker before ":", numbers under it; seats 2–4 with the same
  blocker say "same blocker as seat 1"). The seat's old `.ack-open` paragraph collided with OpenPnl's `.ack-open` pill (cockpitAi.css).
- 🧹 Dead code 2026-10-13: TradeTabs, TrenchHero, WatchlistPage, hasSocials, edgeOf, announcedWallets, searchTokenByAddress,
  lib/liveCandles.js (retired 3D room), FusePage's unused `fx` state (set on every pair move, never read), their CSS (brace-aware prune);
  terminal.css budget 540.7 → 537.
- 🗳 EACH DESK ON ITS OWN VOTE (build queue b5 + b10, 2026-10-13): `desk_stats` credited all six entry desks with the SAME team record
  ("80 real decisions, 62% right" seven times). Now `_office_warden` stamps `thesis.votes` = `judge_review.votes_of(kernel opinions)`
  (GO / DOUBT per desk: Tally 5m up · Sherlock factor ≥ 1 + holders known · Weather factor ≥ 1 · Trigger ENTER · Devil no strong warning ·
  Warden size ≥ ×0.75) and `desk_votes(real trades)` scores each desk on its own vote (right %, GO vs DOUBT typical, lone dissents);
  older trades read what the archive kept (`votes_from_pos`: wx, warden size, door tag). `_desk_stats_view` → payload `deskStats[d].own` +
  Courier (sends landed, last hour) + Archivist (records filed, chain intact) → matrix `recWord` / `VoteBar`, Brain context `_rec`.
  First read: Trigger's own GO trades −0.9% typical vs its doubted (armed) ones +4.3%.
- 🎚 DIAL LAB (b7 + b9, `paper_desk.dial_replay`, payload `dialLab`, the dial's tip): leans spread ±100, the dial moves the bar ±0.5 — of 884
  judged calls only 1 sat that close; the dial moves the PAPER desk only (the live kernel has none). Never "tune the dial" for real money.
- 🟢 b8 `after_path.by_rule` → trail payload `byRule` / `ruleWords`: green exits by the rule that sold them vs the live trail replayed on the
  same whole move. 2026-10-13: R7 +7.6% real → +10% replay — the gap is call → fill delay, not the rule.
- 🔥 VOLUME LIMITS (owner: "fix limits so I can tune for more volume and wider tunes to get Pump trending in there"): realCfg
  `agentMaxAgeH` (1h–30d, default 6h) · `agentMinVol1h` ($1K–$250K) · `agentPumpTrend` off | first (Pump-trending coins skip the age line,
  count fresh, rank ×1.15) | only · MC top now up to $10M. ONE source `universe.clean_limits / limits / on_trend / max_age / min_vol`
  (`set_trending` from the ptrend list each agents pass) read by `in_lane`, `opportunity.hard_fail / open_ok / open_score` and the intake's
  `stale_old`. HQ › Agents › controls card 🔥 VOLUME. Every safety gate and keeper check is unchanged.
- 📈 THE MODEL LEARNS CHART READING (owner: "learn snapshot chart reading, local mainly … all teachings wired live"): `ai_learn.note`
  keeps the model's `chart_phase` + the engine's phase + local / cloud; buckets PHASE:EARLY/LATE · SPLIT:MODEL-LATE/EARLY (who was right when
  they disagreed) · SRC:LOCAL/CLOUD. Every case carries `chartRec` (its own chart record) + `learned` (live lab rules, Judge / coach
  causes, each desk's vote edge) — kept in local trims; the brain bridge + BRAIN_LITE tell the model to use them.
- 💻 LOCAL BOOST 24h (Brain ⚙, `ai_chat.lane_every / watch_note / watch_view`, settings `localBoostUntil` set by the server only): the local
  lane reads every 45s instead of 180s for 24h, falls back by itself while any browser reports lag (fps < 30 or > 400 ms blocked in 2 min),
  never more than half the time. Hourly watch `data/local_watch.json` → Brain ⚙ bars + header chip.
- ⌨ Brain send without stutter: `Composer` owns the text (a keystroke re-renders only the form); while the model answers `holdFx(true)`
  (lib/fxPause, counted, separate from the lag catcher's pressure) rests the page's big endless layers — the local model shares the GPU.
- `ai_chat.salvage`: a model answer cut off mid-JSON shows its reply text, never raw `{"reply": …` (it had been queued to build raw).
- 🎨 The cockpit chart shows the owner's chart theme (no more `plain`; `ThemePick` in its header writes the ONE site choice) and every scene
  has a LIVE TIDE (`.cbg-tide`, green swell from below / red from above, switched by CandleFx's cfk-up / cfk-dn on each real tick).
  Decision panel = clamp(380px, 29vw, 460px). Agents-tab + Brain text boxes are compact (30px, mono, gradient edge on focus).
- 🎓 YOUR LESSONS ARE RULES NOW (owner, 2026-10-13: "teaching AI and agents about fake candles / narratives — not wired so it can be used or tweaked";
  `backend/taught_rules.py` pure + tested `tests/test_taught_rules.py`): a teaching only ever reached the MODEL's prompt — "stop buying fake candles" was even
  split into ticker words (fake, stop, buying) and matched nothing. Three rules the agents run on every coin, stored as `agent_teach.json.rules`
  (teach.add / remove keep them): 🕯 FAKE CANDLES (N green candles in a row, no red, on REAL candles from the shared chart snapshot `_office['charts']` —
  a tape is never judged; knob 5–15, default 8) · 🔁 SAME NARRATIVE (theme / name word / ticker stem shared with a coin on the card or traded in the
  last N h, from archive positions) · 🪞 COPYCAT (`waveRole == 'copy'`). Each: off · 👀 flag (graded only) · ⬇ rank (Soft −6 / Normal −12 / Hard −20
  through `_coach_pens` → `opportunity.judge_hits` "lesson: …") · ✋ skip (`_agent_blocked`). `_taught_stamp` (start of `_kernel_pass`) puts
  `row['taught']` = {rule: reason}; the model's case gets "your rule X HITS this coin"; graded 30 min later like every directive (`coach.CAUSES`
  has the three). A taught note naming a rule (`taught_rules.from_text`) switches it to rank. POST /admin/agents `{taughtRule: {key, mode?, strength?,
  run? | hours?}}` (creator). UI: `RuleCard` (VitalBoard.jsx) in 🎓 Teach (🧷 RULES THE AGENTS RUN above ✍ NOTES FOR THE AI) and in the vital board.
  Narrative NOTES now ignore instruction words (teach.STOP) and match whole words.
- 🫀 DECISION PANEL VITAL BOARD (`lib/vitalBoard.js` pure + `components/command/VitalBoard.jsx`, `styles/vitalBoard.css` `vbd-*` / `trl-*`): every kernel
  candidate carries `vit` (`trench_kernel.kernel.vit`, the top `VIT_TOP` 12 non-TRACKING rows: holders · flow · launch · chart · story · your rule hits ·
  socials report) → tiles grouped 🧩 🌊 🚀 📈 📖 🎓 📣, toned good / watch / bad / unread; tap = the line it is judged on, WHO reads it, WHAT it does
  (+ the rule card to tune it, the socials channels with links, open coin / copy CA). Panel labels in plain words (SCORE vs THE BUY LINE, DEVIL SAYS,
  NEXT CHECK …). Kernel view no longer sends relative `ages` / `decidedAgo` (the page computes from `times` / `decidedAt`; the office payload was at its 100 KB cap).
- 📣 SOCIALS REPORT (`social_research.report(packet)`): per channel (🌐 site · 𝕏 · 💬 TG) a state (MATCH · FOUND · HIDDEN login wall · DOWN · MISMATCH ·
  NONE) + proof (url, followers, last post, CA mentioned) and one grade CONFLICT · STRONG · OK · THIN · NONE · UNREAD. BUG FIXED: the research worker read
  only the desk row's links, so coins WITH a Pump-set X / site / Telegram were filed "no socials" (2 of 4 checked) — `_research_tick` now warms
  Pump's coin record first (`_pump_links_warm`) and fills site / x / tg from it.
- 🫀 Home reactor LIVE SCAN (`HomeEngine` `ScanPulse` / `scanBeats` / `beatPath`, `hen-ekg*` in homeEngine.css): one heartbeat per real launch coin the
  scan judged (up = passed, down = caught, blip = not read), scrolling (transform only, pauses on hover), + "🛡 caught $X · failed “<gate>”".
- 🌙 THE AGENTS SURVIVE THE NIGHT (owner, 2026-10-14: "every time I go to sleep and wake up they get lazy … survive on their own"). Night of
  10-13 → 10-14 (from the ledger + archive): ~200 swaps, 145 exits in 16h, 69% won, median +4.5% — and the average −0.1%: 9 rugs (R5x, −72%
  avg, coins 2–3 min old) ate every gain. Rugs hit ~7% of EVERY kind of entry (age, door, class, brand name — no selection rule separates
  them); no trail setting helps (143-exit trail lab). By morning the card sat in cash: brake on (×0.25, 24h high incl. top-ups) + every READY
  coin held by "chart says go" + 1 READY on cooldown. Fixed:
  · 🧯 brake (`capital.brake`): `BRAKE_HOURS` 6h high (was 24h), `BRAKE_MULT` ×0.5 (was 0.25 — a quarter seat sat under the cost floor, so
    braked = no trading = never climbs back), RELEASES itself after `BRAKE_RELEASE` 3 straight winning real exits.
  · 🪫 PATIENCE VALVE (`office_edge.valve_fill/valve_record`, realCfg `agentValve` on, 🪑 SEATS card): a seat empty ≥ 10 min with nothing
    READY or armed takes ONE coin the chart only held at WAIT FOR CONFIRMATION / BREAKOUT (never SKIP / PULLBACK / DATA / a hard veto) at a
    quarter seat, ≤ 1 per 15 min, tag "🪫 VALVE (empty seat)"; it closes itself when its own ≥ 12 real exits have a losing median.
  · 🏄 RIDE THE VOLUME (`office.reap` `ride_` / `RIDE_GIVE` 50 / `RIDE_HOLD_SEC` 90, rule `R10r`; owner: "they don't know how to hold on real
    volume"): a green seat whose last 90s are a real crowd buying (flow vital BUYERS + hot) is not banked by the take line, the normal trail,
    R7s or a time window; it rides on a 50% give-back trail (also in the 3s live guard). Stops, rug / drain / dump and R4f still act.
  · 🧬 CLONE TICKER rule (taught_rules `clone`, default ✋ skip, 24h): the same ticker as a coin the card traded (5 different $MrBeast in a
    day, FOMO ×9) or a copy of a bigger coin with that ticker on the board; near tickers count ("SpaceX AI" ↔ "SPACEX", "Chat GPT" ↔ "ChatGPT",
    ≥ 4 letters). Owner words naming it ("8th time", "clone", "same coin") switch it on.
  · 😴 regret ledger flip-flop: `regret.note` rebuilt the book without `hold`, so a rolled-back tweak came back 74s later (aiWait / pool floor
    flipped all night). It keeps every key now. 📋 build queue: `_build_state` reads the FILE every time (the service's memory copy had saved
    b7–b10 back to 'queued'); all 14 items closed with notes.
  · 📐 chart scale keeps your entry + stop on screen (`lib/chartLevels.scaleKeep`, PriceChart `autoscaleInfoProvider`) — the BUY sat above the
    scale and its chip floated over the vitals badge. 🫀 vital board never blank: `mergedVit` fills from the candidate's own numbers + the
    held position when the server's `vit` is missing; 📣 socials strip on top (the coin's own links → `SocialIcons`, Pump links ride on every
    desk row via `_taught_stamp`), report adds 🌐 domain age (public RDAP, `social_research.domain_age`, a day cached, free hosts named),
    𝕏 account age (Joined month) + latest post, ⚖️ registry / legal level. 🕯 one bad print never draws a candle (`lib/tickGuard`) and never
    stops a seat (`office.spike_held`, the fast guard's previous read). Chart scenes all redone in the neon-trench language (`CHART_BGS`).
  RESTART THE BACKEND after a backend push, or none of it runs: on 10-14 the 22:31 copy was still serving at 11:17.
- 🧾 THE CHAT SEES REAL FEELESS DATA (owner, 2026-10-14: "no provider answer, local lm should be always running" + the evidence spec; `backend/chat_evidence.py`
  pure + tested): a 💬 chat question about what HAPPENED (why we failed last night, which trades hurt, who was wrong, what Reaper missed, why a coin was
  bought / sold) resolves its window (`window`: last N h · last night 20:00 → 09:00 · yesterday · today · default 12h) and builds ONE compact packet
  in a worker thread (`_chat_evidence`, 60s cache): confirmed real exits (archive) + summary by exit rule / door · the ledger (buys, sells, refusals,
  land time, write-offs, halts) · Judge loss causes + blamed desk · card events + the kernel tape (in memory: since the last restart only) →
  `known_gaps` names every source that has nothing. The model gets it as an EVIDENCE PACKET with `RULES` ("answer only from it, never invent");
  NO HISTORY + no answer = "Insufficient evidence". The reply carries `data` → `DataChip` "DATA: LIVE FEELESS / PARTIAL / NO HISTORY" (missing
  sources in the tip). Read only — changes still go through proposals. The local model: per-request timeout (the shared 20s httpx client cut it
  off → "no provider answered · 20.0s"), the owner's chat waits up to `OWNER_LOCAL_SEC` 120s, the background local lane pauses while the chat answers.
- 🧬 "SAME COIN AGAIN" WAS NEVER RPC (2026-10-14, the owner: "keep buying gta 6, fomo, coca cola, pedo — what's wrong with RPC?"): the ledger had
  22 FOMO buys on 18 DIFFERENT mints, 8 CocaCola on 7, 5 GTA6 — every one a new launch wearing a trending ticker. The 🧬 clone rule (✋ skip, 24h of
  the card's own filled buys, prefix ≥ 4 letters) went live at the 11:32 restart that day; the test pins the exact tickers. "SAME COINS" ⇒ count
  mints per ticker in the ledger before blaming the feed.
- 🐣 THE YOUNGEST-COIN CONTROL IS ENFORCED AGAIN (`universe.min_age/too_young`, carried by `clean_limits` → `set_band`; read by `in_lane`,
  `opportunity.hard_fail`, `opportunity.open_ok` and the seat pre-check on the LIVE pool's birth; options `AGENT_MIN_AGES` 0 · 3m · 15m · 30m ·
  1h · 2h · 3h; Pump trending does not waive it): the 2026-10-12 refactor dropped the check, so `agentMinAgeH` only showed on screen (the card
  read 30 min while it bought 2-minute coins). `_minage_fix_1014` set the real card to ANY AGE = what it really ran on, because its own record
  says young coins are the best scalp bucket: 273 real exits — 0–5 min old 72% won / median +5% · 5–15 min 47% · 1–6h 32% won / −5.4% avg ·
  rugs 8–11% in EVERY bucket. THE EDGE AUDIT'S "<15 min −68%" IS A 1-HOUR HOLD, NOT A MINUTES SCALP — never quote it as a reason to stop
  scalping young coins. Without the 26 rugs (≤ −45%) the real trades average +5.3%; with them −2.6%: the rug rate × ~−72% is the whole loss.
  Rugs by door: ⚡ ready 20 of 156 (13%, −4.6% avg) · 🎯 armed 6 of 113 (5%, +0.5% avg).
- 💻 LM STUDIO WATCHDOG (`scripts/keep-alive.sh` `lm_watch`, about once a minute): server down → `lms server start`; the agents' model
  (`LOCAL_LLM_MODEL`) not loaded or loaded under `LM_CTX` 8192 → `lms unload` + `lms load … --context-length 8192 --gpu max -y`, at most once per
  30 min. `LOCAL_LLM_ENABLED=false` switches it off. After editing keep-alive.sh: `bash scripts/background.sh start` (the running loop keeps
  the old copy). Tested live: 5470 → 8192.
- 🧠☠ THE MODEL'S EXIT READ (owner, 2026-10-14: "agents only take ~+8% — AI should help Trigger and Reaper make smarter, cleaner exits";
  `backend/exit_read.py` pure + tested `tests/test_exit_read.py`, `data/ai_exit_proof.json`, realCfg `agentAiExit` on — 🧠 MODEL card "☠ Exit read
  for Reaper" + `ExitLine`): role `exit` (advisory; Reaper stays in `FORBIDDEN_ROLES`) reads up to 2 HELD agent seats a round (fresh ≤ 60s skipped;
  case = pct · peak · heldMin · structure · phase · Reaper's own state) → one word RIDE (HOLD, no named risk) · TIGHTEN (PROTECT / EXIT or delta ≤
  −0.12) → `_ai['exit']`, noted at the price and graded 15 min later (`_ai_exit_settle` with the learn settle; RIDE right = rose, TIGHTEN right =
  fell). A word reaches `office.reap(ai_exit=)` ONLY when proven (≥ 20 graded, typical move ≥ 2% the right way) and ≤ 3 min fresh: proven RIDE on
  a green seat not seller-led = the ride trail (`rideAt` → also the 3s live guard); proven TIGHTEN on a green seat = the trail ×0.6. Never a stop,
  the catastrophic line, an order or a size. The real record it answers (143 exits since the 3s guard): 69% won, average win +8.3%, 34 of 109
  losers had been up ≥ +5% (median peak +14%).
- 🏃 PROFIT-PROTECTING EXITS ARE URGENT (`arena_prime.URGENT_EXIT_WORDS` + trail · protection · climax · reversing · structure turned): 11 R7 trail
  exits decided at +4…+16% filled at −5…−89% (ZOOAGENCY +16.5 → −12, Engineers +4.3 → −89) — the sale used to wait like a time exit. The
  median R7 fill is fine (+2.7 pts over the last tracked price); this is for the tail.
- 🩸 DRAIN VITALS (`backend/drain.py` pure + tested; owner, 2026-10-14: "buy/sell bar should be a vital to getting out if holders are gone or
  big holders are about to drain the chart"): `read` = 🐋 exit liquidity (top-10 $ bag ÷ pool) · 👥 holders leaving · 💧 pool draining · 🌊 the
  90s tape · 🤖 same-size bots · a big wallet dumping → score + CLEAR / WATCH / DRAIN. Reaper `R4d drain` sells an agent seat on DRAIN only
  with a MOVING part (a heavy bag alone never sells). 🔮 `odds_table` / `odds`: the share of the trench brain's judged coins with this coin's
  strongest feature that fell 50%+ within the hour, with its n (`_drn.set_table` wherever the brain table is rebuilt) — a record, not the
  "80% prediction" the owner asked for: the best buckets read 73–79%, which is a measured rate on past coins, never a promise. Brain
  features `xl:` / `hd:`. Kernel `vit` carries them COMPACT (`drain` {s, st, xl, hd, lq, w} · `tape` [state, $buy, $sell] · `odds` [rug %,
  n, base %, feature]) — the office payload is capped at 100 KB. Vital board: 🩸 EXIT RISK group first with meters (DRAIN · EXIT LIQ ·
  HOLDERS Δ · POOL Δ · TAPE 90s split bar · RUG ODDS); tiles removed: organic, holder count, DATA, socials grade (the socials strip's grade
  button `vital-soc` opens the report).
- 🖧 AI PROVIDER URLS (`ai_keys.base_check` = THE rule for local + custom): `http://` ONLY for localhost / 127.0.0.1 / [::1] / private LAN
  IPv4 (10/8 · 172.16/12 · 192.168/16); every public host `https://` with a real name; never 169.254 / 0.0.0.0 / a query / user@. LM Studio on
  the LAN box: `LOCAL_LLM_BASE_URL=http://10.0.0.249:1236/v1` + `LOCAL_LLM_API_KEY` (its "require API token", sent as Bearer, never shown) +
  `LOCAL_LLM_MODEL=google/gemma-4-e4b` + `LOCAL_LLM_FALLBACK_MODEL` (tried once when the primary is refused / unloaded / unreachable — never
  on a timeout). A NON-loopback local base (`ai_router.local_remote`) = no shared GPU: the agents may use it in the background and the local
  lane reads 3× as often; keep-alive's `lm_watch` leaves a remote base alone. Setup + the chat system prompt: `docs/LM_STUDIO_MCP.md`.
- ⚡ FEELESS MCP (`backend/feeless_mcp.py`, `scripts/feeless-mcp.sh start|stop|status|url|token`, test `tests/test_feeless_mcp.py`): a
  READ-ONLY MCP server for the owner's LM Studio chat, no SDK (JSON-RPC 2.0 over stdio, or Streamable HTTP POST /mcp on :8765 with a Bearer
  token — `FEELESS_MCP_TOKEN` or `data/mcp_token` 0600 — LAN / loopback clients only). Tools: feeless_card · feeless_agents · feeless_trades
  (chat_evidence over archive + full ledger + Judge reviews + card events) · feeless_coin · token_search · trench_now · web_search
  (DuckDuckGo HTML, Brave if `BRAVE_API_KEY`) · web_fetch (public hosts only — DNS checked on every redirect hop) · x_search. It reads the
  services' PUBLIC endpoints + the data files (+ `feeless_diagnose` = LEVERS: facts → the real control with its direction and options, so a 7B model picks from a list instead of inventing one; `feeless_site` = any site section); never /admin, never a POST except DuckDuckGo's search form (test). `FEELESS_MCP_AUTOSTART=true`
  → keep-alive keeps it up. A new tool must READ — never sign, trade, top up or change a setting.
- ⚡ CHART OVERLAYS = ONE EVENT-DRIVEN FRAME (`lib/chartFrame.js` `addChartJob` / `bumpChart`; owner, 2026-10-14: "site / agents tab lags
  horribly"): ChartLive, ChartLevels and CandleFx each ran their own 30fps rAF on every chart (layout + scale reads 90×/s while nothing
  moved). PriceChart now BUMPS its container on a real tick, new data, a scroll / zoom (onRange) and a resize (ResizeObserver); one shared
  rAF runs an overlay only for a chart that changed, plus a 1s safety refresh, nothing in a hidden tab. A new chart overlay ⇒ `addChartJob`,
  never its own rAF loop. The live P&L tag sits `GAP` 28px off the forming candle with a dotted leader (`clv2-lead`).
- 🧾 Fuse wallet KV doc keeps only RECENT ledger rows (`fuse_wallet.recent_rows`: last 26h, 300–2000 rows) — 1.2 MB of a 1.4 MB doc was
  parsed every keeper pass and rewritten every save. Every row stays in the SQLite ledger (`_fw_full_ledger`). `ARENA_KEEP` 300 paper runs in
  fuse_hq.json (was 600 = 370 KB rewritten every card tick). THE MAC: 16.6 of 17.4 GB swap used with a 7B model + Chrome + 4 services —
  a full swap is lag everywhere no code can fix; the real fix is the model on the LAN box (or a smaller one).
- 💻 LOCAL MODEL ON THIS MAC PAUSES ITS BACKGROUND READS WHILE A BROWSER LAGS (`ai_chat.lane_every(.., shared_gpu=)`, `SHARED_LAG_EVERY` 900s;
  `shared_gpu` = not `ai_router.local_remote`): the owner's own chat is never paused. LM Studio on another machine is never paused for this Mac.
- 🏄 Reaper trail reset by the owner (`office.owner_tune`, `_trail_fix_1014`, lineage `owner: True`): protectAt 10 / giveBackPct 30 (was 4 / 35,
  promoted by the old replay that ended where the agents sold — it could only favour a tighter trail). Full-move trail lab: typical +7.7% vs +4.4%.
  The shadow → promote loop may move it again on new evidence. Stops / hard exits untouched.
- ✋ YOUR LINES ON AGENT SEATS (`set_leg(.., now)` stamps `ownerLvAt`; `office.reap`: an agent coin with `ownerLvAt` uses its own `sl` (wider
  or tighter, never past the −45% catastrophic line) and `tp`; the position carries `owner` → archive → `office.owner_hand` = "did your hand
  help?" (yours vs agents: n, typical, average) in the payload (`ownerHand`) + the MCP diagnose). Cockpit chart: the seat's stop + take are
  ChartGrab handles (`fuse.src: 'cockpit'`, the cockpit confirms + posts `{leg}`; HqRealCards ignores cockpit drags).
- 🎨 Chart scenes = Default · ⚡ Neon trench · 🟩 Code rain (bull words ↔ bear words on the tick) · 🌧 Gutter (rainy street, flickering TRENCH 24/7
  sign + puddle reflection, ripples) · 🐋 Whale sonar (radar arm, pings, a whale, bubbles) · 🫧 Lava lamp · 📼 Trench TV (VHS scanlines, REC, a
  tracking tear on a red tick). Retired: reactor · helix · city · warp · tunnel · storm (stored ids fall back to Default).
- 🧪 THE TRENCH SIEVE replaced the Home reactor (`HomeEngine`: `sieveDrops`, `gateOf`, `SIEVE_GATES` scan · holders · bundles · dev): real
  launch coins fall through four laser gates — caught ones stop at the gate their own fail reason names, get zapped into the ☠ pit; safe ones
  fall into the 🏦 vault (runners live); unread ones hover at the scanner. `fateOf`: "not scanned yet" is WAIT, never a fail.
- 🔏 `FeeStamp` (Home heading): notary seal, serrated edge, turning word ring, $FEE live 24h on the arc, one ink-thump on arrival.
- Brain chat bubbles hug the text (`.cch-msg` width fit-content, ≤ 78%, 10.5px).
- 🤝 THE DUET (`backend/ai_duet.py` pure + tested; owner, 2026-10-14: "gemma primary, qwen secondary, learn / grow together"): 🖥 Gemma on the
  desktop Mac = provider `lan` (`LAN_LLM_BASE_URL/MODEL/API_KEY`, first in `AI_PROVIDER_ORDER`, `reasoning_effort: none` or it answers empty) leads
  the background lane; when it makes a real call (CAUTION / FAVOR) 💻 Qwen (`local`) re-reads the same case (≤ 1 / 150s, never while a browser
  lags) → note slot `sherlock2` + a merged `duet` note. `ai_learn.note` dedups PER PROVIDER (two models, two calls). `record` = pairs within
  10 min: agree %, both-CAUTION / both-FAVOR results, who was right on splits; a split is NEUTRAL until one model wins ≥ 10 called splits at
  ≥ 60% (`trusted`). `gate_verdict`: an AGREED (or trusted) duet CAUTION may hold a coin back; a lone small model still never can. Chat: Brain
  model switch `🤝 Duet` → Gemma answers, Qwen reads that answer and agrees / pushes back, both shown. UI: 🧠 AI tab `ModelReport` + `DuetLine`.
  The 401 in HQ's provider list = the running service had an older LM Studio token: restart after any `.env` key change.
- 🕸 MCP `deep_research` (several searches incl. scam / team / news angles, best pages READ in parallel, each with its URL) + `investigate`
  (one coin: FEELESS read + its own site — does it name the mint? — its X link + web results for the CA). Public hosts only, every hop checked.
  FEE prompt (`docs/lm_fee_prompt.txt`, pushed into the LM Studio preset) = the owner's FEE voice + FACT / INFERENCE / UNKNOWN + the levers rule.
  Portable pack for a bigger model: `docs/FEE_BRAIN.md`. Handoff map: `docs/HANDOFF.md`.
- 🔬 HOME = WATCH FEELESS WORK (`HomeEngine.jsx`, `homeEngine.css` `wfw-*`; replaced the HUD / Stack / Sieve and the deleted `FeeStamp`): ONE real
  launch coin at a time (caught · cleared · runner woven, 6s each, hover holds) runs the real checks as bars that fill to its own number
  (top-10 · dev · bundles + snipers · pool · buyers, ✓ / ✗ against the line, unread = "—"), then the verdict STAMPS in; beside it the real cards'
  confirmed swaps. Entrance keyframes are transform-only.
- 🪪 MODEL NAMES: in the owner's chat each LM Studio model speaks as itself (`ai_router.IDENTITY` set by `Router.ask(role='owner')`, `identity_line`):
  Gemma = **Vega** (lead), Qwen = **Kai** (second); `LAN_LLM_NAME` / `LOCAL_LLM_NAME` override. `GENERAL_SYSTEM` answers the LATEST message only
  and greets back on slang ("yurrr") instead of resuming the old topic.
- 🧪 BRAIN › PLAYGROUND (`backend/ai_play.py`, owner `GET|POST /admin/ai/playground`, `AiPlayground.jsx`, `aiPlay.css` `apg-*`): a model writes ONE
  self-contained HTML document (`ai_router.RAW` returns the whole text); shown in `<iframe sandbox="allow-scripts">` (no same-origin) with a CSP that
  blocks ALL network injected server-side (`lock`); ✏ Change it iterates; ≤ 30 kept. AI code edits are NOT a feature: ideas → 🧱 build queue → Claude.
- 🕸 MCP adds `pump_trending` (Pump's own trending tab or another pick list, every FEELESS vital per coin) + `feeless_notes` (teachings, rules, build
  queue). `scripts/lan-bundle.sh` → `lan_bundle/` (git-ignored, holds the MCP token): preset + mcp.json pointing the DESKTOP Mac's LM Studio at this
  Mac's MCP over the LAN + README.
- 🧹 CHART TAGS DECLUTTER (`lib/chartLevels.declutter`, `MERGE_PCT` 0.4, `MAX_TAGS` 5): levels at the same price = one tag, money levels first
  (entry · stop · take · trail / lock · invalid / support · tools), the rest `quiet` faint lines with no tag; prices only on key tags.
- 🎨 CHART SCENES = Default · ⚡ Neon trench v2 (striped synth sun, ridge, stars, speed streaks on a green tick) · 🟩 Code rain v2 (3 depths, hot heads,
  sweep) · 🚀 Hyperspace (stars stream out; reverse + pink on a red tick) · 🎰 Degen casino (THE HOUSE ALWAYS RUGS, slot reels lock on a red tick,
  chips). Gutter / sonar / lava / Trench TV retired (fall back to Default).

- ⚡ AGENTS TAB LAG = ONE GIANT LAYER (2026-10-14, measured in the scratch harness with CDP LayerTree + tracing): React was cheap (commits ~1 ms,
  < 1% main thread while streaming) — the cost was COMPOSITING. `.agd` (the whole 4,200px tab) carried `m-live`, whose `inset: -35%` aurora
  became a 2392×7160 rotating layer and forced the content above it onto its own 1384×4192 layer: 39.6 Mpx of layers, every frame. Now
  `m-live::before` is capped (`top: max(-35%, -260px)`, `height: min(170%, 1200px)`) and `.agd.m-live::before` is still (2D transform, no
  will-change; the ribbon's m-live still drifts): 16.7 Mpx, per-frame compositing ≈ halved. Test `styles/liveLayers.test.js`. "A TAB LAGS" ⇒
  count layer Mpx (CDP `LayerTree.layerTreeDidChange`, drawsContent) before touching React. Never put an animated m-live on a page-tall element.
- 🗂 AGENTS COCKPIT = ONE SCREEN (2026-10-14, owner: "less scroll, fewer stacked boxes"): under ribbon · pulse · seats · chart | decision panel sits
  ONE `Deck` (testid `ack-tapezone`, `feeless.agentDeck`): ⚡ Live (intake band + live decisions, default) · 🎬 Trades · 🧠 Brain · 🧩 Agents
  (matrix) · 📋 Review · 🎛 Controls — every pane mounted, only the picked one shown. Page 4,214 → 1,601px. P&L strip over the chart = one line
  (entry → now + Reaper's rule in tips); chart header = MC · 5m vol · liq (price + supply in the MC tip); decision chips = 6 newest, one row.
  🧠 AI pane: the newest `LOG_SHORT` 6 decisions first (rows clamp to 2 lines, intel on the newest only), ask box, then `details.cai-record`
  (agree bar, metrics, rule lab, report, duet, learning). Layout CSS = `styles/cockpitDeck.css` (imported last). New cockpit block ⇒ a deck pane.
- 🖥 DESKTOP MAC ONE-PASTE: `bash scripts/lan-bundle.sh` (this Mac) prints `curl -fsS -H "Authorization: Bearer …" http://<ip>:8765/lan-install | bash`;
  the MCP serves `install_script` (FEE preset → ~/.lmstudio/config-presets, a `feeless` entry merged into ~/.lmstudio/mcp.json, other servers kept,
  `$HOME` respected). Also writes `lan_bundle/install.sh` (AirDrop + `bash install.sh`, or `bash scripts/lan-bundle.sh install`). This Mac's own
  LM Studio uses the stdio entry (no token, no port).
- 🧠 BRAIN SHELL + 📜 ACTIVITY: full Brain / pop-out = a left section rail (Talk · Coach · Teach · Playground · Activity) + the open section;
  `GET /admin/ai/activity` (`ai_chat.activity`) = one timeline of model reads, proposals + your decisions, playground creations, the background
  lane → `AiActivity.jsx` (`aiActivity.css` `cac-*`: last-hour pulse bars, kind filters), polled every 10s while open.
- 📸 SNAPSHOT EXITS (owner, 2026-10-14: "we're exiting too fast — listen to the AIs, 2–3 snapshot decisions on TP / SL"; `office.soft_confirm/soft_exit`,
  `SOFT_EXITS` R6 · R7 · R7s · R7b · R7v · R8 · R9 · R9e · R4f · R4c): a profit-side / soft exit sells only after `SNAP_N` 2 reads ≥ `SNAP_GAP` 8s
  apart (an older one is forgotten after 90s); the model's FRESH exit read (`exit_read.fresh_words`, proven or not) sets 3 (RIDE) or 1
  (TIGHTEN). Reaper's tick AND the 3s fast guard's R7 both use it. Stops, −45%, rug / drain / dump, scan fails, R5t stay INSTANT.
  Older Reaper tests pin `SNAP_N` 1 (monkeypatch). Judge the change on real exits: R7 / R6 results before vs after.
- 🧩 CODE LAB (replaced the HTML playground; `ai_play.py`, `AiPlayground.jsx`, owner `GET|POST /admin/ai/playground` + `/playground/decide`): pick a
  target (`ai_play.TARGETS`: Reaper · agents · kernel · ranking · capital · AI router · MCP · cockpit · Home), the model gets that file's real
  OUTLINE and proposes ONE change {title, file, kind, why, risk, code}; ✅ files it to the build queue ("code lab cN … code in
  data/ai_playground.json") — BUILDING ONE = read its code there, apply it yourself with tests. No model writes a repo file.
- Home spotlight adds a score ring (checks passed / read), a scan beam, UP NEXT chips and a this-visit tally.
- 📡 HOME = RUG RADAR (HomeEngine.jsx `radarBlips`, `rr-*` in homeEngine.css): every live launch coin is a blip (angle from its mint, radius from
  launch age: newer = centre), pinging as the sweep passes (each blip's delay = its angle; green passed · red ✕ caught · grey unread; the
  centre = caught count); beside it the selected coin's checks (ring, bars, verdict stamp, up next) and the real trades. Tap a blip = select.
- 🌙 NIGHT GUARD (`night_guard.py`, realCfg `nightGuard` on, `_night_check` in the tier tick before the agents' fills, `data/night_guard.json`,
  payload `nightGuard`): card 12% under its 6h high → 2h pause on NEW real buys; 4 losing real exits in a row → 45 min; 2 exits ≤ −45% in an hour
  → 90 min. A pause = `agentPaper` for that tick (switch-ins too); exits keep running. Owner inbox on each trip + ☀ an overnight report each
  morning (8–12 local, `night_guard.morning`).
- 🧬 COPYCATS BLOCKED PERIOD: `taught_rules.LOCKED` keeps clone + copycat at ✋ skip (not switchable lower); clone memory 30 days (knob 168 /
  336 / 720 h); `family` matches sequels (GTA 6 ↔ GT IV ↔ GTA5) + 4-letter prefixes; 8,000 ledger rows read.
- Owner's ideas 1–3: 🏔 the seat gate holds a coin the model reads at the TOP (chart_phase LATE FOMO / DISTRIBUTION / COLLAPSE / REVERSAL or
  timing LATE / CHASE; cloud or an agreed duet only); ☀ morning report; `opportunity.links_conflict` = its own site / X point at another coin
  → hard no. 🔪 `opportunity.knife` (build queue b15–b20): 30%+ under its chart high → no buy until a higher low (`chart_intel.compact` now
  carries hl / ll / distHigh).
- FEE prompt v3 (`docs/lm_fee_prompt.txt`): no code sandbox (call tools, never fake code), A/B/C routing, research first, `now` MCP tool for the
  date. In-app Brain: same no-sandbox line + `today` in its context.
- 🤖 HOME = AGENT RELAY (HomeEngine.jsx `relayOf/relays/board/DESKS`, `arl-*`; replaced the rug radar — owner: "no radar or scans"): the ten desks
  as one lit chain; each REAL decision from the public `/fuses/proof` feed replays every 5s — the coin rides the wire to the desk that decided
  (Courier = buy, Reaper = sale, with Reaper's own rule), it flares, the stamp + reason + tx land; score = decisions · exits won · card value.
- 🧬 The clone rule reads the WHOLE ledger by time (a 1,500-row slice covered ~2h on a busy card: a 2nd $FOMO got through at 02:08).
- FEE prompt: "YOUR MEMORY IS OLD — THE TOOLS ARE RIGHT" (Qwen found Trump, then 'corrected' it with 2023 memory).
- ⚛ HOME = FUSE FORGE (HomeEngine.jsx `forgeCards/pctWord`, `frg-*`; replaced the relay — owner: "show a crazy cool FEELESS feature"): the live
  coins of a real tier card (`/fuses/prime` legs, placeholders skipped, real card first) orbit the forge, spiral into the core, flash + shards,
  and the holographic Fuse card is forged (rotateY in, then an endless tilt + sheen), every coin with its own live %. One 8s cycle per card,
  tier chips pick one, hover holds. Keys are `${mint}-${index}` (a card can hold two legs of one coin). The forged card stays dark in day.
- 🧩 CODE LAB fixes: it sends ONLY its own prompt (`Router.ask(only_system=True)`, no persona line) — under the chat prompt ("no JSON", "greet
  back") Gemma answered "Yo, I'm Vega" and the lab errored; auto / duet tries the other model when one returns no code (the error names each
  answer). 🔍 PREVIEW BEFORE ANY CHANGE (`ai_play.preview_diff/current_of`): each function the proposal writes vs its current version in the
  real file (unified diff, NEW for names the file lacks) + for UI targets a `preview` mock-up (sandboxed, CSP-locked) → tabs 🔍 Before → after ·
  🖼 How it looks · 📄 Full code. ✅ Approve still only queues it; Claude applies it with tests.
- 🌙 NIGHT SHIFT 00:00–09:00 local (`night_guard.night_cfg/is_night`, realCfg `nightShift` on; merged in `_prime_real_cfg` + the agents' `set_band`):
  seats ≤ 15% of the card (a smaller owner ceiling stays), no coin under 30 min, chart must say ENTER NOW, no valve fills; the night guard trips at
  8% drawdown · 3 losses in a row · ONE rug-level exit. 09:00 = the owner's own settings again. Only ever tightens.
- ▶ CODE LAB TEST RUN (`ai_play.safe_code/safe_call/test_run`): a Python proposal's `examples` are RUN — only after an AST check (no imports outside
  SAFE_MODULES, no open/exec/eval/getattr/dunder, examples = its own function with literal args) in `python -I`, env {}, temp cwd, CPU 2s / no
  file writes / 16 fds, 4s timeout, macOS `sandbox-exec` deny network + file-write. Tab ▶ Test run (call → got, ✓ / ✗). UI proposals: 🖼 See it working.
- 💻 THIS MAC'S LOCAL MODEL = `qwen/qwen3-4b-2507` (MLX, `LOCAL_LLM_MODEL`; 7B Qwen 2.5 is `LOCAL_LLM_FALLBACK_MODEL`) — lighter on the M3 Air and better at
  tool calls (chat ~6s, a coin case ~37s). FEE prompt: "NUMBERS: COPY, NEVER COMPOSE" — it once quoted "$20K lost on PUMP-7" on a $2 card.

