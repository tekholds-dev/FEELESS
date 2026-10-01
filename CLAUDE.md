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
- Lag catcher (Cmd Ctr › Lag catcher) is the source of truth: fix its list before adding features. Full list: `docs/REQUIREMENTS.md`.

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
- Tests NEVER touch real data: `tests/conftest.py` sandboxes every backend `Path` under `backend/data` per test. (A test
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
- Fuse Lab (`FuseLab.jsx`) starts in Cmd Ctr › Fuse (`<FuseLab call>`: 6 pools, auto|manual weights, publish as a Fuse) and
  reaches traders as Trade › ⚛️ Fuse Lab tab (`TradeTabs`, `?tab=fuse`; 3 pools). Caps are HARDCODED server-side
  (`fuse.USER_MAX_LEGS`=3 / `MAX_LEGS`=6). Pools: `/fuses/discover` (popular/yield/deep/new); preview: `POST /fuses/preview`
  (`fuse.preview`: split, $/day, blended APR, grade, 24h backtest, size guard >1% of pool liquidity).
- 🧬 Fuse Evolution (Cmd Ctr, `FuseEvolve` → `POST /admin/fuses/evolve` → `fuse.evolve`): genetic search over baskets of
  the chain's best ~40 live pools. Genes = strategy (`fuse.STYLES` yield/momentum/steady/degen), pools 2–6, generations,
  budget ($5/$20/$100). Fitness = grade + APR + momentum + calm − size-impact − duplicate coin − fee drag (network fees on
  tiny buys). Elitism (best never drops), seeded, tested vs brute force. Champion → "Load into Lab" → one-click Fuse in.
  Ranking only: never claims profit, never trades by itself.
- Fuse HQ (`backend/fuse_hq.py`, pure + tested; `FuseHQ.jsx` in Cmd Ctr, `FusePnl` on Trade › Fuse Lab):
  real Fuse P&L (`POST /fuses/position` counts a leg only if its sig is YOUR confirmed FEELESS buy; cost/tokens from that
  record), paper Arena (champion → $5 for 24h, settles once; style is *proven* after 3 settled runs with avg > 0),
  Bloodline (saved champions seed gen 0), Health (published Fuse vs fresh champion → BEATEN ≥10%).
  Traders get ONE button: `POST /fuses/best3` ($5/$20/$100) breeds with the arena's proven style (else yield), cached 2 min.
- Chat: `/fuse [name]` posts `⚛️ fuse:<id>`; `FuseChatCard` (≤340px, shared `lib/fuseFeed.js` poll) → amount → FuseGo.
- Cmd Ctr › Fuse = `FuseDeck`: KPI ribbon (real P&L, 24h outlook from the ARENA only — `fuse_hq.outlook`, never a
  promised return), left rail (Breed & fuse | HQ · P&L | Published | Vault, each with a one-line explainer), one panel at a
  time). Admin fuses up to 10 pools (`fuse.MAX_LEGS`; `fuse.min_share` keeps big-fuse weights distinct). Champions render
  as `FuseCard` (MetaCard: drag tilt + ⟲ flip, back = why it won) with the admin `FuseExplainer` pipeline; traders get the plain-words `FuseExplainer` (APR est. = LP fee rate, not
  paid to holders; fee drag on tiny buys). Explain every money mechanic on the surface that uses it.
- Prebuilt rail (`FuseRail`, `GET /fuses/prebuilt`): best basket per strategy bred from `_fuse_candidates()` (5 min cache),
  flip cards + arena record + "Use this"; traders 3 pools, Cmd Ctr 3/5/8/10. Shown in BOTH the trader Lab and Cmd Ctr Lab.
- Fuse chat: ONE room `fuse-lab` (`FuseSide`, beside the Lab; stacks under 980px via container query) ⇄ Holders board
  (`GET /fuses/holders`, verified positions, P&L %), transform slide between panes.
- Receipt: `FuseGo` shows BEFORE (per leg pay/get/FEELESS fee/network/impact, total cost %) and AFTER (`POST /fuses/receipt`
  = `fuse_hq.receipt`: quoted vs exact fills, slippage). Never scrollIntoView inside clipped cards (scrolls the card).
- Hourly loop `_fuse_autopilot_tick`: settles 24h arena runs, enters each strategy's champion once/hour (`auto: True`),
  then `_shield_alerts` → admin inbox once per newly flagged bot. Published Fuses rank by `fuse_hq.trust_rank`.
- Hover explainers: `[data-tip]` inside `.fe` / `.frail` (CSS tooltip, focus too). Explain every gene/control there.
- FeeCat Fuse: NOT built on purpose — only after a strategy beats holding SOL in the arena over weeks.
- One-click Fuse in (`FuseGo` + `lib/fuseGo.js`): quote+simulate every leg in parallel (refresh 10s), review must match
  (`orderMatches`), ONE `signAllTransactions`, then `/execute` each leg. Same trading path as Quick trade — no new money path.
- Built and paid out in Cmd Ctr › ⚛️ Fuse. System map: `docs/ARCHITECTURE.md`.
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
- Earned quest badges join `wallet_badges` (chat chips + profiles) with their art. Cmd Ctr › Badges › Quest engine edits all.
- Tool quests: case files opened + war room trades via `POST /quests/event` (war room trade must be one of your verified
  FEELESS trades; case files once per wallet per day, ≤30/day); alerts counted from your push watchlist.
- Perks (`quests.PERKS`, editable per badge in Cmd Ctr): fee discount (best of tier/promo/badge, read from cache so quotes
  never wait, noted on the quote) and chat backgrounds. Only add perk kinds that something actually honours.
- Season: `QUESTS_PATH.season`, PAUSED until launch (no leaderboard, no trophies). Unpause in Cmd Ctr › Badges on launch
  day; "Award week's top 3" writes `kind: 'quest'` trophies once per week.
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
- Engine: Jupiter Swap API primary (FEELESS fee into our SOL/USDC token accounts, capped priority,
  our broadcast). Ultra only as engine or opt-in fallback. Fallback off + Swap API down ⇒ trading pauses.
- Nothing trades fee-free except **buying** $FEE / FEECAT / rFEE. Coin→coin with no SOL/USDC side is refused.
- The wallet signs everything; the server verifies the signed message equals the quoted one; no resubmits.
- Only show or sign an order that matches the coins, side and amount on screen.

## Coin verification + coin badges
- `backend/verify.py`: coins EARN and LOSE the check and coin badges (`COIN_BADGES`) the same way — recomputed each run
  (6h TTL); `transitions()` logs earned/lost with the reason into verify.json `history` (shown in `VerifyReport`).
  A granted gold check is suspended while a `CRITICAL` gate fails (mint/freeze/creator/liquidity); official coins keep gold.

## Bot shield (our defender) — ties into rep, rewards, Fuse
- `backend/bot_shield.py` (pure, tested): 8 engines — reward_farmer, clockwork, batch_cluster, wash_trader, dust_farmer,
  chat_spam, referral_farm, fuse_self_deal — each with cited evidence. verdict bot ≥75 / watch ≥45. `_shield_of(addr)` (5 min
  cache). Ties: trust score (bot −40, watch −15), wallet case evidence, check-in rewards refused for bots, Fuse creator cut
  = 0 for self-buys and bots, Fuse creators gain rep per outside buyer (`_fuse_rep`). Check-ins store `checkinAt` timestamps.
- Cmd Ctr › Safety › 🛡 Bot shield (`BotShield.jsx`): scan all, per-engine counts, evidence, Clear / Confirm / Back to auto
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
- Command Center settings that matter at scale (keys, engine, fees) must be visible in its **Core** group.
