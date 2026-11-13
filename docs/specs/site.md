# SITE — architecture, always-on, speed requirements, mobile layout, Telegram, LM Studio (merged 2026-11-12, word for word)

Sections: [ARCHITECTURE](#architecture) · [ALWAYS_ON](#always_on) · [REQUIREMENTS](#requirements) · [MOBILE_LAYOUT](#mobile_layout) · [TELEGRAM](#telegram) · [LM_STUDIO_MCP](#lm_studio_mcp) · [market-graduation-source](#market-graduation-source)


---
<a id="architecture"></a>
## ⟪ARCHITECTURE⟫ (was docs/ARCHITECTURE.md)

# FEELESS — system map

One page: which engine owns what, where its data lives, and which shared hook/poller the UI reads it through.
If you add a feature, plug it into the row that already owns that data — never add a second source.

## Services (restart all after backend changes: `bash scripts/start-backend.sh`)

| Service | Port | Owns |
|---|---|---|
| `server.py` + `market.py` + `trading.py` | 5001 | market feeds (DexScreener + own indexes, **no GeckoTerminal**), quotes/swaps (Jupiter), chat (Mongo) |
| `reputation_service.py` | 5077 | reputation/case files, fees + fee ledger, quests/badges, Fuse, seasons, profiles, notifications, admin |
| `feecat_service.py` + `feecat_brain.py` | 5088 | FeeCat paper-trading agent (discipline: 9 lives, tilt/cold pauses, probation sizing) |
| `candles_service.py` | 5099 | candles (sanitize → gap-fill → continuous), trade tape (Helius → Solana RPC fallback), live price stream |

## Engines (pure, tested modules)

| Module | Decides | Read by |
|---|---|---|
| `investigate.py` | reputation score, every point cited | case files, rug shield, radar, alerts |
| `quests.py` | 40 badges, tasks, daily/weekly quests, XP/levels, perks, season score | `/quests/*`, `wallet_badges`, fee perk on quotes |
| `fuse.py` | Fuse legs, index, A–F score, split, creator cut, real-pool filter | `/fuses*`, HQ Fuse builder |
| `fuse_vault.py` ⇄ `contracts/fuse_vault` | vault shares at NAV, auto-weights, caps, rebalance, mgmt/perf fees | `/vaults*`, HQ vault designer, on-chain program (localnet v0.1, NAV = SOL held; adapters deferred) |
| `fee_report.py` | per-wallet fees / FeeBack; totals rebuilt from the ledger (`_fee_totals_heal`) | fee report, HQ fee book |
| `feecat_brain.py` | setup memory, edge, discipline | FeeCat loop + HQ strip |
| `candles_service._sanitize/_fill_gaps` | valid, gap-free, continuous candles | every chart |

## Shared client data (one request per key, never one per card)

| Data | Hook / store |
|---|---|
| market feeds, pairs | `useMarket` (SWR — same URL = one shared request) |
| your holdings | `lib/myHoldings.js` (`useHeld`, `useHeldList`, `HeldChip`) |
| quests, badges, perks, season | `useQuests` (QuestBoard, QuestNudge, ReserveProgress, Season, MintedTimeline) |
| launch forensics | `lib/coinIntel.js` (tape tags) |
| coin mood (chat bg) | `lib/coinMood.js` |
| snipers-out | `lib/snipersOut.js` |
| pump pulse | `lib/pumpPulse.js` |

## Money paths (see docs/FEELESS_HISTORY.md › Money rules)

Quote → simulate → wallet signs → server verifies the signed message equals the quote → broadcast → confirm sweep →
fee ledger (`fee_ledger.json`, the source of truth) → fee totals / FeeBack / Fuse creator cuts / quest metrics.
Anything that "counts" a trade (quests, Fuse buys, war-room trades) must find the signature in the wallet's
confirmed FEELESS trades — nothing is self-reported.

## Safety nets

- `tests/conftest.py` sandboxes every backend data path per test (tests can never write real data).
- `test_no_undefined_names.py` (pyflakes), `test_no_geckoterminal.py`, `styles/cssHygiene.test.js` (dead CSS + budgets).
- Lag catcher: auto fx-lite is temporary (6h, recovers after 3 smooth minutes).


---
<a id="always_on"></a>
## ⟪ALWAYS_ON⟫ (was docs/ALWAYS_ON.md)

# Always-on host (so real cards are managed while your Mac sleeps)

Everything that trades or watches runs inside the backend as loops — the runner engine, Arena battles, the tier cards + Fuse-wallet
keeper, FeeCat, candles. Today they only run while your Mac is awake. One container runs them all, 24/7:

| # | Step | Where |
|---|------|-------|
| 1 | Create a project on **Railway** (https://railway.app) → *Deploy from GitHub repo* → pick this repo. | Railway |
| 2 | Settings → Build → **Dockerfile path** `deploy/Dockerfile`. | Railway |
| 3 | Add a **Volume** mounted at `/app/backend/data` (your cards, books, ledger, profiles live there — copy your current `backend/data` up once). | Railway › Volumes |
| 4 | Variables: paste everything from `backend/.env` (RPC / Helius, Alchemy, Jupiter, Circle `CIRCLE_API_KEY` + `ENTITY_SECRET`, admin wallets, `ALLOWED_ORIGINS` = your site, `FEELESS_TRUST_PROXY=1`). Never commit `.env`. | Railway › Variables |
| 5 | Networking: expose **5001** (trading API) and **5077** (reputation / Fuse / HQ API) as public domains; point the frontend `REACT_APP_*` API URLs at them. 5088 / 5099 stay internal. | Railway › Networking |
| 6 | Turn the Mac's backend OFF once the host is live (two keepers on one Fuse wallet would race). Keep the frontend wherever you host it. | you |
| 7 | Check: HQ › Lag catcher green, HQ › Fuse › 👛 shows the wallet, a tier card's next-round clock ticks. | HQ |

`deploy/run-all.sh` restarts any service that crashes. Logs: Railway › Deployments › Logs.
⚠ Only ONE place may run the backend against the Fuse wallet at a time.


---
<a id="requirements"></a>
## ⟪REQUIREMENTS⟫ (was docs/REQUIREMENTS.md)

# FEELESS: what it needs and how we keep it clean

> Planning status and remaining requests: [HANDOFF.md](HANDOFF.md) `## TASKS`. This file retains the technical specification/history; do not maintain a second active backlog here.

## Priority #1: low usage, clean build, no lag, no bugs
Every change has to meet all of these before it ships:

1. **Gates must pass before a push.** Run these in order:
   - Frontend tests: `cd frontend && CI=true yarn test --watchAll=false`
   - Build: `CI=false npx craco build`
   - Backend tests: `PYTHONPATH=backend:. python -m pytest backend/tests -q`
   - Page scan: every page renders, with no panel or page crashes.
2. **Speed budget.** A page should stay at 55fps or better on a mid laptop, and no API route should have a p95 above 1.2s. **HQ › Lag catcher** reports both from real browsers. Anything on its fix list gets fixed before new features.
3. **Animation rules.**
   - Animate only `transform` and `opacity`.
   - Never animate a CSS custom property such as `--ang`, because it repaints every frame.
   - Never use `backdrop-filter` over an animated background.
   - Don't put `filter: blur()` on moving layers.
   - Respect `prefers-reduced-motion`.
   - Heavy effects switch off under `body.fx-lite`.
4. **Network rules.**
   - No request waterfalls: use `asyncio.gather` or parallel fetches.
   - Use one shared poller per data type (`pumpPulse`, `snipersOut`, `RepMark` batch).
   - Load hot JSON through `_cached_json` / `_json_load`.
   - Debounce typing to 300ms or less.
5. **Crash-proofing.**
   - Every page and panel sits inside a `PanelBoundary`, so one bad API shape costs one card, not the page.
   - Crashes auto-report to Bugs.
   - `test_routes_unique.py` blocks duplicate API paths.
6. **Usage (saving credits).** Grep before reading, read only what's needed, batch commands, and keep reports short. Add new mechanics to pure, tested modules such as `investigate.py`, `reserve_pool.py` and `perf.py`, so fixes are small.

## To go live: what the owner must do
| Step | Where | Status check |
|---|---|---|
| Helius RPC key → `SOLANA_RPC_URL` | `backend/.env` | HQ › Launch & setup › Hook-up steps |
| `JUPITER_API_KEY` | `backend/.env` | same |
| `PUBLIC_SITE_URL` (coin metadata host) | `backend/.env` | same |
| `FEELESS_ADMIN_WALLETS` (hardware or multisig) | `backend/.env` | same |
| Fee accounts (SOL + USDC) for the trade fee | HQ › Trading & fees | Self-test goes green |
| Treasury route / fee claimer (Squads multisig) | HQ › Treasury | Hook-up steps |
| **Launch config**: pick a preset, check the readiness box, sign once (about 0.01 SOL) | HQ › Launch & setup | Box reads "✓ Valid on Meteora" with no ⚠ warnings |
| `ALLOWED_ORIGINS=https://your-domain` | `backend/.env` | Hook-up steps |
| Restart the backend after `.env` edits | `bash scripts/start-backend.sh` | |

### Launch presets (Meteora DBC)
All presets use:
- a 99% launch fee that decays exponentially (block-0 snipers lose money);
- dynamic (volatility) fees;
- a fixed supply, with mint and freeze authority revoked;
- 100% of graduated LP locked forever.

| Preset | Open → graduate | Snipe tax | Normal fee | Use for |
|---|---|---|---|---|
| 🛡 Anti-snipe max | 30 → 500 SOL | 99% → 1% over 3 min | 1% | Default |
| 🚀 Pump classic | 28 → 420 SOL | 90% over 1 min | 1% | Fast pump.fun-style runs |
| 🏦 Deep reserve | 100 → 1500 SOL | 99% over 5 min | 0.5% | Slower candles, deep pool |
| 💵 Stable (USDC) | $5K → $69K | 99% over 3 min | 1% | No SOL price swings |
| 🔥 Buy & burn | 30 → 500 SOL | 99% over 3 min | 1.5% | FEELESS share goes to a buy-back wallet |

Meteora's own validator checks the curve before you can sign. The warnings flag weak anti-snipe settings, a normal fee above 2%, and any withdrawable LP.

## Engines and how they link
- **Trading.** The Jupiter Swap API is primary; the FEELESS fee is its own transfer in the transaction. Ultra is only used when opted in. The wallet signs, the server verifies the signed message and broadcasts. A confirmed trade then earns **season points**: fees paid weigh most, capped at 50 per trade, counted once per signature.
- **Reputation.**
  - `investigate.py` produces cited evidence and a verdict.
  - The **same verdict** appears on case files, profile rails, chat rep marks (a red ⚠ when suspect or high, opening the case file on click), and in the rug shield / trade tickets ("Creator case file: …").
  - FEELESS wallets are never suspects.
- **Wallet watch.** One tap from any case file or profile. Alerts arrive on the wallet's next buys and sells, and dumps by suspect wallets are called out. The limit is 25 per user.
- **After the sell.** Your recent sells compared with the price now ("sold a runner" / "good exit"). This is FeeCat's learning loop applied to you.
- **Badges → money.**
  - Season tiers earn a share of the season **reserve wallet**.
  - **Badge pools**: a pool is any wallet you choose plus the % of it that forms the pot. In the badge × pool matrix, each badge gets its own **% of each pool's pot**, split equally between that badge's holders. A pool's shares can't pass 100%, and unassigned % stays in the wallet.
  - The pool wallet always signs its own payout. The server records only SOL transfers verified on-chain, and never the same transaction twice.
- **Networks.**
  - DexScreener boosts are the first source.
  - Small chains (Cronos, zkSync, Zora…) are topped up by `chain_feed` from their own DEXes and hub-token pools (DexScreener), so no network loads empty. No GeckoTerminal, sitewide.
  - Chain logos come from DexScreener, which carries the current CRO mark.
- **Treasury.** HQ › Treasury shows every wallet holding FEELESS money: the fee accounts (wSOL / USDC), the admin wallet, season reserves and badge pools.
  - **Split now** sends fees to the split-plan destinations. You sign from the wallet that owns the fee account.
  - The server re-reads each transaction on-chain and records only what actually moved.
  - Nothing splits automatically, because that would need a server-held key.
- **What's launchable** (HQ › Launch & setup):
  - **Launch config:** a one-time on-chain template.
  - **FEELESS coins:** launched on the Launch page. The config's terms apply and the page's planning fields lock.
  - **Pump.fun coins:** launched from the same page.
  - **Pools for existing tokens:** created in the Pools tab.
  - Airdrops and badge payouts.
- **Coin verification.** A coin earns a green ✓ on its logo, site-wide, by passing all 5 safety gates and scoring 75+ out of 100 on 10 cited checks:
  - **Gates:** mint and freeze authority revoked, creator not flagged, 24h+ of trading, $25K+ liquidity.
  - **Checks:** locked LP, holder spread, insider share, dev bag, socials, real volume, two-sided flow, 72h+ age.
  - Official or reviewed coins get a gold ✦ granted in HQ › Verify coins. A revoke always wins.
  - Checks re-run every 6h. Case files and the coin passport show the same report.
- **Fee's setup memory.** Fee files every closed trade under its setup buckets (1h move, flow, depth, age, 5m heat, market-cap band, lane, fair value gap).
  - Setups with a proven edge size her up, to at most 1.5×. Setups that keep losing size her down, or veto the entry outright after 6+ trades at ≤20% wins and −8% or worse on average.
  - HQ › Fee 🐱 shows her playbook, her vetoes and her exit tuning.
- **Lag catcher.** Browsers report API latency, long tasks and FPS once a minute. A device that lags switches itself to lite effects. The owner can force lite effects site-wide.

## Open items (not built yet)
- Circle house-wallet trading: needs the owner's per-trade and daily caps.
- Buy & burn executor: claimed fees are currently bought and burned by hand from Treasury.
- Moving to a database plus multiple workers, for scale beyond one box.


---
<a id="mobile_layout"></a>
## ⟪MOBILE_LAYOUT⟫ (was docs/MOBILE_LAYOUT.md)

# Mobile and Duo layout contract

Owner requirement, 2026-10-28: every page must fit the usable browser screen on mobile and Duo, across orientation and browser chrome changes. All controls must remain available. The matrix is a test requirement, not a device-name allowlist.

## Exact owner-supplied Duo reference

**Confirmed against Apple's spec page (apple.com/iphone-duo/specs, 2026-11-12):** outer 5.4" 1398 × 2034 px at 460 ppi, inner 7.6" 1878 × 2670 px at 430 ppi (announced 2026-09-09). At DPR 3 that is exactly 466 × 678 folded and 626 × 890 / 890 × 626 open — the owner's numbers. Apple publishes no browser viewport: Safari's toolbars take ~90–120 px of height (folded upright ≈ 466 × 560, open wide ≈ 890 × 540), so test those too. Safari in this environment reports no viewport segments; never require that API to enable the layout.

| State | Width × height, CSS px | Expected behavior |
|---|---|---|
| Folded upright | 466 × 678 | Single-column phone flow |
| Folded sideways (rotated reference) | 678 × 466 | Compact landscape split where usable |
| Unfolded wide | 890 × 626 | Chart left, desk right; split near center |
| Unfolded upright | 626 × 890 | Chart above independently scrollable desk |

Browser chrome, keyboard, display scaling and split windows can produce other usable sizes. Do not hard-code these numbers as layout heights. Do not multiply them by DPR for CSS geometry.

## Rules for every mobile feature

1. Fit available space using flex/grid with min-width/min-height:0. Use dvh with fallback and safe-area env insets; for Safari shell fitting, observe visualViewport resize/scroll plus window resize/orientationchange, coalesced with requestAnimationFrame. Clean up on unmount. Preserve native pinch zoom.
2. Orientation comes from the usable layout dimensions, not the device name. Preserve selected coin, interval, dock tab and swap state across rotation. Existing useDuoFloor detects coarse-pointer wide devices/sideways phones; keep ordinary desktop behavior intact.
3. Scroll the content panes, not the entire fixed cockpit. Avoid a fixed minimum height larger than the viewport. Avoid overflow:hidden ancestors that can be programmatically scrolled by focus; use overflow:clip where no scrolling is intended.
4. Safe areas, browser bars, keyboard and standalone/home-screen mode must never cover close/navigation/trading controls. iPhone browser fullscreen behavior is platform-controlled; CSS fitting must work without requestFullscreen.
5. **Tab rows never scroll sideways (owner 2026-11-12: "no scroll tabs" on the Duo, folds and phones): they wrap and share the row** — one rule in `terminal.css` ("Tab rows never scroll"); add a new tab row's class there. Readable labels and usable touch targets (32px minimum; prefer 40–44px; `touch.css` grows small ones on touch screens). No missing controls: collapse secondary navigation behind a clearly labeled toggle, preserve keyboard/focus access and allow scrolling.
6. Canvas charts resize from their allocated container. Do not subtract guessed toolbar heights or let a descendant overwrite the intended chart size token. Keep live state intact on viewport changes.
7. Run the device matrix below (`site-audit` style, touch emulation). Verify ordinary 360/390px phones; folded 466×678 and 678×466; open 890×626 and 626×890; intermediate widths; shortened Safari viewport; keyboard; day/night; reduced motion/lite; desktop regression. Capture evidence and label emulation versus physical-device testing.

## Duo floors — the OFFICIAL Duo / fold / phone view (owner 2026-10-29: "the official Duo view should be in MD's so no f-ups, bugs, bad containments")

Every app that runs full-screen on a Duo, fold, tablet or phone uses ONE shell: `styles/duoFloor.css` (`dfl-*`). Today: the Trenches floor
(`components/terminal/DuoFloor.jsx`, modes trench · pump) and HQ › Agents (`AgentCockpit` duo branch, `.dfl.dfl-agents`). A new floor copies this, never invents a layout.

| When (`lib/duo.js`) | Layout (`.dfl` class) | Grid |
|---|---|---|
| Duo unfolded wide 890×626 · tablet wide · phone sideways (`useDuoFloor().wide`) | `is-wide` | `rail 56px · chart = 50% − rail · side = 50%` → the split sits EXACTLY on the crease (445 px) |
| Duo unfolded upright 626×890 · tablet upright (`useDuoFloor().on && !wide`) | `is-up` | `chart 58fr · side 42fr · act auto` |
| Phone upright < 600 px wide, incl. Duo folded 466×678 (`usePhoneUp()`, Agents) | `is-up` | same as above — one screen, chart first, never a multi-screen scroll |
| `is-swap` (⇄ / ⇅, saved per device) | either | the two halves trade places |

Rules (each one is a bug we already had):
1. **Portal to `<body>`**, `position: fixed`, own z-layer (Trenches 45 under dialogs · Agents 4500 above the HQ pop-out 4000, under the Brain drawer 5200 / AI panel 9000).
   NEVER fit a floor by retouching a host (`.hqp` classes, `cc-shell` overflow) — that was the Agents "bad containment" (2026-10-28 build).
2. **Height = the visible viewport**: `100dvh`; floors inside Safari chrome follow `visualViewport` (resize + scroll; skip while pinch-zoomed) via `--adf-vh` / `--adf-top`.
   Safe areas = `env(safe-area-inset-*)` padding on `.dfl`. `body.duo-floor-on` hides the site chrome (FeeCat widget, Duo bar, mobile tab bar) while a floor is open.
3. **The chart height is MEASURED, never guessed**: a ResizeObserver on `.dfl-plot` sets `--dfl-h` = its height − the measured heads/toolbars; `.chart-area` + `.candle-canvas`
   read `--dfl-h`. No descendant may set its own chart height. Short landscape (≤ 520 px tall) drops secondary blocks above the candles (Agents: the P&L block — the ride bar keeps it).
4. **Only the panes scroll** (`.dfl-pane`, `overscroll-behavior: contain`); the shell, rail, bar and tabs never move. Use `overflow: clip`, not `hidden`, on anything focus could scroll.
5. **Every control stays**: secondary nav lives in the side half (Agents: money strip + nav lead it; the nav's pick opens in the DESK tab). An exit (`←` / `☰ HQ`) is always on screen; ☰ HQ steps the floor aside and ⤢ brings it back.
6. **State survives a turn / fold**: the open tab, the coin, the interval and swap are remembered (`feeless.duo*`, `feeless.ack.*`), so a rotation re-renders the same screen.
7. **Tabs** = a locked `.dfl-tabs` row (≥ 38 px tall); every button ≥ 32 px (rail 40 px), `data-tip`, hover / active / focus-visible.
8. **Proof before done**: screenshot 890×626, 626×890, 678×466, 466×678 and 390×844 in the Browser pane (`/dev/hq?touch` for Agents) and check: crease at 50 %, no page
   side-scroll, the chart filling its half, the pane scrolling alone, no control clipped. Physical Safari (toolbars, keyboard, home-screen) stays OWNER verification.

### Pages checked against the contract (browser pane, emulated sizes — not physical Safari)

| Page / surface | 360 | 390×844 | 466×678 | 626×890 | 678×466 | 890×626 | Notes |
|---|---|---|---|---|---|---|---|
| HQ › Agents (floor) | — | ✓ one screen | ✓ (phone floor) | ✓ | ✓ chart 248 px | ✓ crease 56·389·445 | 2026-10-29 |
| Trenches floor (DuoFloor) | ✓ no side-scroll | — | ✓ | — | — | ✓ | shell owner since 2026-10-27 |
| Home · Trenches · FEEd · Pump radar · Radar | ✓ | — | ✓ | — | — | ✓ | real-page sweep 2026-10-29: no side-scroll; Pump toolbar fixed |
| Fuse · Launch · FeeCat · Launch a cat · Familia · Perps | ✓ | — | ✓ | — | — | ✓ | no side-scroll; Fuse tab + Familia directory rail fixed; Launch / FeeCat flags were probe artifacts (verified) |

## This delivery

Agents only: fitted HQ shell, safe-area padding, visualViewport listeners with cleanup, chart-height allocation, rotation, scroll containment and HQ-controls toggle. Landscape chart gets the entire left half; the money/navigation strip lives above the right desk. Portrait prioritizes the chart above the dock. Other tabs must adopt/verify this contract in M01; they were not all modified here. Physical Safari fullscreen/keyboard verification is still OWNER work.

## Device matrix (2026-11-12, emulated in headless Chromium with touch; physical devices stay OWNER verification)

| Device | CSS px | Source |
|---|---|---|
| iPhone Duo folded / sideways / with Safari bars | 466×678 · 678×466 · 466×560 | Apple spec px ÷ 3 |
| iPhone Duo open upright / wide / with Safari bars | 626×890 · 890×626 · 890×540 | Apple spec px ÷ 3 |
| Galaxy Z Fold 7 cover / open / open sideways | 412×915 · 984×1092 · 1092×984 | open from yesviz (DPR 2); cover = usual 412 Android width (estimate) |
| Galaxy Z Fold 5/6 cover / open | 344×882 · 882×1104 | Chrome DevTools preset |
| Pixel 10 Pro Fold open | 865×897 | 2076×2152 px at ≈2.4 (estimate) |
| Phones | 360×780 · 375×667 · 390×844 · 440×956 | common widths |
| iPad · desktop | 820×1180 · 1280×800 | regression |

Checks per page: no page side-scroll, no tab row that overflows (it must wrap), no control off-screen outside a scroll pane, no console error or crash.
Android fold widths move with the phone's display-size setting, so treat them as ranges, not exact numbers.


---
<a id="telegram"></a>
## ⟪TELEGRAM⟫ (was docs/TELEGRAM.md)

# 📲 FEELESS × Telegram — Strike Zone (the Familia shooter) + an automated group

Owner 2026-10-27: "family be a telegram game" → then "a cool third-person shooter instead of the raceway". What is built:

| Piece | Where |
| --- | --- |
| 🎯 STRIKE ZONE — a full-screen third-person shooter on three.js's own open-source FPS physics (Octree + Capsule) and its rigged Soldier model: a container yard with warehouses + ramps, bots (easy / normal / hard) or ONLINE rooms, over-the-shoulder aim, ADS, recoil, headshots | `components/StrikeGame.jsx`, `StrikeZone.jsx`, `lib/strikeGame.js` |
| Levelling + the GUNSMITH — 4 guns × barrel · optic · magazine · stock · skin, each part unlocking at a level; XP for kills, headshots, wins (server-checked on its own clock) | `backend/arena.py`, `/api/reputation/arena*` |
| Telegram Mini App — opens full screen inside Telegram, plays under the player's Telegram name (no wallet needed); a wallet in a family also feeds the family bank (+5 MP a kill, 150 a day) | `lib/telegram.js`, `backend/tg_auth.py` |
| Online rooms — a WebSocket per room (≤ 8 players), positions + shots relayed | `/api/reputation/arena/ws` |
| Automated group posts — every level-up (with what it unlocked) and a 🎯 PLAY button | `_tg_group`, `arena.level_post` |

## A. Set it up (≈10 minutes, only you can do this)
1. **Make the bot.** In Telegram open **@BotFather** → `/newbot` → name `FEELESS Familia` → username e.g. `FeelessFamiliaBot`. Copy the token.
2. **Put the token in** `backend/.env`: `TELEGRAM_BOT_TOKEN=<the token>` (never paste it anywhere else).
3. **A public https address.** Telegram only opens https pages. Production: your `PUBLIC_SITE_URL`. To test from this Mac today:
   `cloudflared tunnel --config /dev/null --url http://127.0.0.1:51367 --http-host-header localhost:51367` → it prints `https://<random>.trycloudflare.com` (keep that terminal open).
4. **Make the Mini App.** @BotFather → `/newapp` → pick your bot → title `Fee City Race` → description → a 640×360 picture (a screenshot of the
   Raceway works) → skip the GIF → **Web App URL** `https://<your https address>/familia?tg=1&place=strike` → short name `strike`.
   BotFather answers with the app link `https://t.me/FeelessFamiliaBot/strike` → put it in `backend/.env` as `TELEGRAM_APP_URL=`.
5. **The menu button** (so the bot's chat opens the game in one tap): @BotFather → `/setmenubutton` → your bot → the same Web App URL → label `🎯 Play`.
6. **The group.** Create a group `FEELESS Familia` (or use yours) → add your bot → make it **admin** (Post messages · Pin messages).
   Get the group's id: post any message in the group, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser and copy
   `"chat":{"id":-100…}` → `backend/.env`: `TELEGRAM_GROUP_ID=-100…`.
7. **Restart the backend** (push to `main` restarts it through auto-pull, or the watcher — see `docs/HANDOFF.md`). HQ › Launch › Ready board
   and HQ › Setup show the three Telegram keys as set (never their values).
8. **Pin the game in the group:** post `https://t.me/FeelessFamiliaBot/strike` in the group and pin it. Done — the group now gets `🎯 STRIKE ZONE · <name> hit LEVEL n — unlocked …` on every level-up, with a 🎯 PLAY button.

## B. Test the shooter (no setup needed)
1. Open **`http://localhost:51367/familia?place=strike`** (or Familia → the city → Directory → 🌹 THE FAMILY → **STRIKE ZONE**, also a room of Family HQ).
2. The lobby: your level + XP, the GUNSMITH (pick a gun, then barrel · optic · magazine · stock · skin — locked parts say the level they open at),
   VS BOTS (easy / normal / hard) or ONLINE (type a room name, share it with your family).
3. **🎯 PLAY** opens full screen. Desktop: click to capture the mouse → **WASD** move · **Shift** sprint · **Space** jump · **left-click** fire ·
   **right-click** aim down sights · **R** reload · **Esc** frees the mouse. Phone: left stick moves, drag the right side to look, **FIRE · AIM · JUMP · R**.
4. First to 25 kills (bots) / 30 (online) or the clock ends the match → the result card: kills, deaths, headshots, accuracy, the XP saved (a guest
   sees it but keeps nothing — sign in with a wallet or open it from Telegram).
5. The server refuses results that beat its own clock (`backend/tests/test_arena*.py`). Dev preview without the lobby: `/dev/towers?strike=hard`.
6. Online: open the same room on two devices — you see each other's soldiers (blue), shots and kills. (A dev server restart is needed once so the
   WebSocket proxy in `setupProxy.js` is live.)


---
<a id="lm_studio_mcp"></a>
## ⟪LM_STUDIO_MCP⟫ (was docs/LM_STUDIO_MCP.md)

# ⚡ FEELESS × LM Studio — MCP + model setup

Two separate wires:

| Wire | Direction | What it does |
|---|---|---|
| **AI router** | FEELESS → LM Studio | The agents + the Brain chat ask your model (gemma first, qwen as fallback). |
| **FEELESS MCP** | LM Studio → FEELESS | Your model, chatting in LM Studio, reads the live card, the agents, the trades, any coin, and the web. **Read-only.** |

---

## 1 · FEELESS → your LM Studio box (10.0.0.249)

In LM Studio on the box: **Developer → Server settings**
- Serve on local network: **on**, port **1236**
- Require API token: on is fine. Copy the token.
- Load `google/gemma-4-e4b` (context **8192** or more), and qwen as backup.

In `backend/.env` on this Mac, uncomment the block at the bottom (keep only ONE active `LOCAL_LLM_BASE_URL` — the first one wins):

```
LOCAL_LLM_BASE_URL=http://10.0.0.249:1236/v1
LOCAL_LLM_MODEL=google/gemma-4-e4b
LOCAL_LLM_FALLBACK_MODEL=qwen2.5-7b-instruct-mlx
LOCAL_LLM_API_KEY=<the LM Studio token>
```

Then restart the backend (`bash scripts/start-backend.sh`) and press **Test** on the LM Studio row in HQ › Agents › 🧠.

What changes when the model lives on the LAN box:
- this Mac's GPU stays free for Chrome → **no more Agents-tab stutter while it answers**;
- the agents may use it in the background too (it was owner-only because it shared this Mac's GPU), and it pre-reads coins 3× as often;
- the keep-alive watchdog stops loading models on this Mac (the box runs its own).

URL rule: `http://` is allowed **only** for localhost, 127.0.0.1 and private LAN IPv4 (10.x, 172.16–31.x, 192.168.x). Every public host must be `https://`.

---

## 2 · LM Studio → FEELESS (the MCP server)

On this Mac:

```bash
bash scripts/feeless-mcp.sh start
```

```bash
bash scripts/feeless-mcp.sh token
```

```bash
bash scripts/feeless-mcp.sh url
```

To keep it running with the other services, add `FEELESS_MCP_AUTOSTART=true` to `backend/.env`.

In LM Studio (on the box): **Program → Install → Edit mcp.json**, paste:

```json
{
  "mcpServers": {
    "feeless": {
      "url": "http://10.0.0.104:8765/mcp",
      "headers": { "Authorization": "Bearer PASTE_THE_TOKEN" }
    }
  }
}
```

(Use the address from `feeless-mcp.sh url` if this Mac's IP changes. macOS may ask once to allow incoming connections for Python — allow it.)

LM Studio running on **this** Mac instead? Use stdio — no token or port:

```json
{
  "mcpServers": {
    "feeless": {
      "command": "/Users/christopherclark/Desktop/feeless v.o7/backend/.venv/bin/python",
      "args": ["/Users/christopherclark/Desktop/feeless v.o7/backend/feeless_mcp.py"]
    }
  }
}
```

### Tools (all read-only)

| Tool | Gives the model |
|---|---|
| `feeless_card` | the real card: put in → now, all-time P&L, who controls it, every coin's % and $ |
| `feeless_diagnose` | the money picture + the levers: expectancy, biggest leak, rugs, doors, trail lab, blocked-vs-taken, controls with options |
| `feeless_site` | any section: runners · arena · gauntlet · callouts · edge · lists · calls · strategies · brain · learn · forecast · proof · slang · season |
| `feeless_agents` | mission, capital stance + leaks, the 4 seats with Reaper's ruling, top candidates, the Judge |
| `feeless_trades` | what REALLY happened in a window ("last night", "last 3 hours"): closed trades, ledger, Judge reviews |
| `feeless_coin` | FEELESS's full read of one mint (vital, holders, dev, tape, trench read, callers, socials) |
| `token_search` | ticker / name / CA → mint, cap, pool, 1h move |
| `trench_now` | weather + the live launch list with safety marks |
| `web_search` | DuckDuckGo (no key), cached 5 min; Brave if `BRAVE_API_KEY` is set |
| `web_fetch` | any public page / JSON API as text (private network refused) |
| `x_search` | recent X posts about a coin (via search) |
| `deep_research` | several searches (query + scam / team / news angles) and the best pages READ in parallel, each with its URL |
| `investigate` | one coin: FEELESS read + its own website (does it name the mint?) + its X link + web results for the CA |

There are no tools that sign, trade, move money or change a setting.

### Model settings in LM Studio
- Context **8192+** (16K if the box can hold it — tool answers are up to ~6K chars).
- Temperature 0.6 for chat.
- gemma-4 / qwen2.5 both do tool calls; leave "tool use" on.

---

## 3 · The system prompt + preset

The master prompt lives in `docs/lm_fee_prompt.txt` and is already installed as the LM Studio preset **FEELESS FEE Master**
(`~/.lmstudio/config-presets/FEELESS FEE Master.preset.json`): temperature 0.55, no response cap, context 16K on load, top-p 0.9,
min-p 0.05, repeat penalty 1.08. Pick it in the right panel › Preset. It makes the model:
- call `feeless_diagnose` before any advice (real expectancy, the biggest leak, rugs, doors, the trail lab, what the checks blocked);
- answer verdict → 2–4 real numbers → ONE move picked from the real LEVERS / CONTROLS (exact name, current value → a listed option);
- never give textbook filler ("diversify", "risk management is key").

The agents send their own brain prompt (`backend/ai_brain.md`) — editing the chat prompt never changes how they trade.

## 4 · Getting the most out of a small local model
- **One job per chat.** Start a new chat per coin / question — small models drift in long threads.
- **Make it call tools.** "check the card then tell me…" works better than an open question.
- **gemma-4-e4b** is quick and good at tool calls; **qwen2.5-7b** writes better analysis. A 14B+ model (qwen2.5-14b / gemma-3-12b) on the box is the next real upgrade.
- Keep KV cache / Flash Attention on in LM Studio for speed at 8K+.


---
<a id="market-graduation-source"></a>
## ⟪market-graduation-source⟫ (was docs/market-graduation-source.md)

# Pump radar graduation source

The Pump radar uses Pump.fun's public coin status endpoint
(`https://frontend-api-v3.pump.fun/coins/{mint}`) for graduation status.
The endpoint's `complete: true` flag is the source-of-truth signal that a
Pump.fun coin completed its bonding curve; the response may also include the
Raydium migration pool.

DexScreener and GeckoTerminal remain discovery sources only. A pool is shown
in the Graduated stage only when:

1. its exact base-token mint appears in the current DexScreener or GeckoTerminal
   Pump radar feed; and
2. Pump.fun reports `complete: true` for that same mint.

The API returns the Pump.fun source URL, source label, fetch time, and an
unavailable/error state. A provider-indexed pool, trending result, or new pool
is never marked graduated based on age, venue, liquidity, or ranking.

Graduated radar cards display `pool_address` only when Pump.fun reports a
Raydium migration pool. The destination is labeled as provider-reported and
links directly to the reported Solscan account. If Pump.fun omits the address,
the card shows that the migration pool is unavailable; the UI never substitutes
the discovered market pair address.

---
## ⟪STAFF + SAFETY NETS⟫ (moved from CLAUDE.md 2026-11-12, word for word)

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

