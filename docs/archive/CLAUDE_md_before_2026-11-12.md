# FEELESS — working rules (lean).

> 👑 **The owner's newest chat message overrides anything in this file, HANDOFF or memory.** When he sets or changes a rule, update every .md that says otherwise in the same turn. Don't stop to ask before tasks: work through all he asked, in order.
> ✨ **FIRST TRY = FINISHED (owner 2026-11-12):** he should never have to curse to get good work. Styled, real data, tested, seen in the browser, pushed, HANDOFF ticked — or it isn't done.
> 🧰 **STASH ORDER (owner 2026-11-12, every Claude):** every safe, clean, harmless piece of data or build you make or find goes into the stash AND Fee's stash/Git folder. That folder is an elite dashboard of proof stats (every proof type), easy to maintain. Think above and beyond; never lazy.

The full feature log lives in `docs/FEELESS_HISTORY.md` — GREP IT, never load it whole.

> 🧭 New session? Read `docs/HANDOFF.md`: section 0 (owner blockers), then the block your task is in (1 AGENTS · 2 COLLECTIVE · 3 SITE, the only task list) → only the history lines your task touches.
> 🧨 Fuse / the real card? Read `docs/specs/money.md` first.

Degen trading terminal (Solana-first). Every feature ships **one and done**: styled, animated, fast, tested, pushed.

## 🎨 MANDATORY STYLING + ANIMATION — NO BS (owner, 2026-10-21; this outranks speed of delivery)
The owner rejected work that shipped as "dull", "non degen", "emojis sliding around a block". A surface is NOT done until it meets ALL of:
1. **Scratch-built visuals, not emoji props.** Emojis are labels only — never the art. A city has drawn buildings (CSS 3D boxes / SVG /
   canvas / three.js) with lit windows, roofs, streets, MOVING CARS with headlights, people, signs; a card has a drawn face; a chart scene
   has drawn geometry. If the reference is a game (Godfather PSP, Jailblock, Sims, Pump.fun), match its LOOK, not a grid of icons.
2. **Every surface is ALIVE**: at least one ambient layer (light sweep, drifting glow, particles, traffic, weather), real-number
   animation (values tick / flash / count up on change, bars fill), and an entrance (stagger via `--i`). transform/opacity only;
   pause off-screen (`lib/fxPause.js`), still under `body.fx-lite` + `prefers-reduced-motion`.
3. **Degen meta, unique per page**: its own palette + backdrop + type (Obsidian green is home / trade; Familia = noir gold + city night;
   FeeCat = violet night; Launch = the official logo green on near-black — owner 2026-10-22, amber dusk read as mud). Glass panels with an inner highlight, neon edges, glow on the hot number, segmented
   controls, no flat boxes-in-boxes, no bare paragraph walls — meters, rings, bars and charts instead of text.
4. **A twist, never a copy**: when the owner names a reference ("dev/null", "Pump", "X"), take the IDEA and make a FEELESS version
   (our data, our language: germ floor, gun line, rep, rug, MP) — never a clone of the reference's UI.
5. **Every interactive element**: hover + active + focus-visible, a `data-tip` explaining it, ≥ 32px hit area, never covered by a layer.
6. **Prove it**: open it in the Browser pane, screenshot it, and look at it as the owner would before saying done. If it looks like a
   prototype, it is not done.
7. Day theme, 360 px phone, fx-lite, reduced motion — every new surface.

## How to work (save usage)
- 🧩 New component UI: look at HeroUI first (owner 2026-11-05, heroui.com/llms.txt), then the existing m-* presets. Every coding agent gets it the same way through the kit library.
- 🧠 **THINK PAST THE ASK (owner 2026-11-12, every Claude):** "he couldn't even fathom this — humans never think of this and that's why they fail."
  For every request, also build the elite piece the owner didn't name: the next step a user will want, the failure a human would miss, the
  data that makes it honest, the one-tap path from it to the next proof. Every proof/folder chat ends by offering what to do next (options +
  a free-text "something else"), the way Claude asks. Real data and the money rules still win: never fake a feature to look elite.
- 🏆 The owner's asks are BASIC on purpose (owner 2026-10-30): build the corporate-level version. Before any UI, look at how the best real products do it
  (chat boxes, settings popovers, drawers, dashboards) and match that pattern with our existing m-* presets and sheets — never invent from no reference.
  Think one step ahead (e.g. settings go behind a ⚙ popover in the chat bar, not a loose panel).
- Be brief with the owner. Report what changed, what was tested, what wasn't. No essays.
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
- Palette = **FEELESS GREEN on OBSIDIAN** (owner 2026-11-12 pick from look lab v2: Obsidian default, Desk and Pit layouts, all `#19e68c`, day `#08995a`; green ban LIFTED — only the old `#15d16a`/`#45e486` stay retired). Looks live in `lib/looks.js` + `backend/looks.py` and remap the PLASMA hexes the sheets still write, so new CSS keeps using the meta.css tokens (never a hand-written hex); Plasma and every older look sit in one Classic row of the LookPicker. Each proof type keeps its own light. Colours come from the meta.css tokens, never a new hand-written hex.
  Labels/numbers in `JetBrains Mono`, uppercase micro-labels with letter-spacing.
- Fonts = the 6 tokens in `index.css` (owner 2026-10-27, all loaded in `public/index.html`): `--f-display` Unbounded (heroes) · `--f-ui` Sora (body) ·
  `--f-mono` JetBrains Mono (numbers, micro-labels) · `--f-tech` Chakra Petch (tickers, venue names, seg buttons) · `--f-noir` Cinzel · `--f-noir-it` Playfair. Never add a family.
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
- Lag catcher (HQ › Lag catcher) is the source of truth: fix its list before adding features. Full list: `docs/specs/site.md`.

## Data sources
- **NO GeckoTerminal, sitewide, ever** (backend or frontend). `backend/tests/test_no_geckoterminal.py` enforces it.
  Market data = DexScreener + our own indexes (Pump.fun, LetsBONK, LaunchLab, Helius, Alchemy, Jupiter).
- No dead war rooms: `chain_feed` tops up any chain under `THIN_FEED` pools from its own DEXes (`CHAIN_QUOTES` search)
  and its hub token's pools (`NATIVE_POOLS`, DexScreener /token-pairs). Quiet "new" lists add the youngest active pools
  tagged `discovery: 'rising'`; coins hosted on another chain are tagged `via` (Zora → Base). Never pad with unrelated coins.
- Search ranks most trusted first (`rankSearch`/`trustScore` in SearchBox): FEELESS assets, pasted CA, exact $SYMBOL,
  then liquidity/mcap/age/profile; one row per token = its deepest pool.
- Candles (owner 2026-11-04, CH01; replaces the old "every bucket exists, opens at the previous close" rule): a chart draws the source's own candles, unedited (`?view=true`, `_true_view`, client `trueCandles`).
  No filled minutes, forced opens, clipped wicks or sampled ticks over a provider's bars; a minute with no trades has no candle. No history = sampled prices, labelled as not trades.
  History = first provider with ≥120 bars, else the longest that agrees with the live price. The agents' inputs (no `view`, `/api/candles/live`) still use filled bars until the owner moves them. Change only with a test.

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


## Current work — single source of truth

Read [docs/HANDOFF.md](docs/HANDOFF.md) `## TASKS`: every open request in three blocks (AGENTS · COLLECTIVE · SITE), owner blockers, conflicts. The exact old wording is archived in `docs/FEELESS_HISTORY.md` ("ARCHIVED HANDOFF 2026-11-09"). Do not recreate a competing task list here or in any new file.

Read [docs/specs/site.md](docs/specs/site.md) before any phone/Duo change. Owner reference: folded 466×678, rotated 678×466, unfolded 890×626 / 626×890 CSS px, DPR 3; these are supplied viewport references, not universal hardware specs. Every mobile browser must fit its actual usable viewport, preserve controls and rotation state, and account for Safari chrome/safe areas/keyboard.

Read HANDOFF › REMAINING (the only to-do list), work it top down: build, verify, push, tick the row, keep going. Existing unrelated edits must not be committed with your change.
