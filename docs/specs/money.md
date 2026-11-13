# MONEY — Fuse playbook, perps, brokers, go-live, counsel (merged 2026-11-12, word for word). Money rules: CLAUDE.md + RULINGS.md win.

Sections: [DEGEN_PLAYBOOK](#degen_playbook) · [PERPS](#perps) · [BROKERS](#brokers) · [GO_LIVE](#go_live) · [COUNSEL_BRIEF](#counsel_brief)


---
<a id="degen_playbook"></a>
## ⟪DEGEN_PLAYBOOK⟫ (was docs/DEGEN_PLAYBOOK.md)

# FEELESS degen playbook — the model and mindset

> Planning status and remaining requests: [HANDOFF.md](HANDOFF.md) `## TASKS`. This file retains the technical specification/history; do not maintain a second active backlog here.

For the next Claude working on Fuse. Read this before you touch the engine, the real card or any list.
CLAUDE.md has the rules. This file covers how to think about them.

## The owner, in one paragraph
The owner runs a real-money Fuse card (Prime Blaze, tpl `degen`) on 5-minute rounds and trenches by hand. They talk in
degen shorthand ("send it", "trench cat", "seats not filling", "do all") and want things shipped, not debated. They love
visual meters, one-tap actions, live numbers and the evidence behind a call. They hate dead UI, extra clicks, emoji
stand-ins where a real icon belongs, and lectures. They make the trading decisions. Your job is to make the tools honest,
fast and readable, and to say plainly what the records show.

## Where the money is (2026-10-08, re-check before you quote it)
- Put in: **$22.50**. Card: **~$2.25**. Owner's next milestone: **$2.40**. They'll add $2.50 if the card gets there. The 🎯 goal
  bar on the real card tracks it.
- 24h you vs engine (`realBook.versus`): **hand picks −8.4% on $85 (35% won), engine −0.5% on $33**. Realized all-time
  −$12.38 (276 wins / 377 losses).
- Owner-move record (`humanStyle.moves`, judged 30 min later): picks 200 · 39 good / 88 bad · −6.7% typical. Profit takes
  46 · 20 good / 10 bad. 🏠 initial-out 2 · +182% typical (tiny sample, and the best thing on the board).
- Ledger autopsy (943 pieces, memory `real-card-what-pays`): **held 30+ min wins, exits inside 15 min lose, trims of
  winners make the money.** The leak is turnover × entry cost, not fees.

## What the records say works and what doesn't (1-hour medians, `/fuses/list-proof` + `/fuses/call-proof`)
| Least bad | Losing hard (scrapped from engine buys, shown ☠ BUSTED) |
|---|---|
| 🧲 Fed runners −0.2% | 🆕 New launches −81% |
| 🔥 Pump trending −2.4% | 🗑 Trench list −79% (small ticket only, never paused) |
| 🟢 Dips & bottoms −4.7% | 🔥🔥 Double signal −83% |
| calls WATCH +0.9%, WASH +0.5%, COOLING +0.2% | 🚀 Movers −65% · 📣 Pump callouts −54% |
| combo "in 2 lists, flat pace" +5.0% (n 9) | calls BOND RUN −83% · EARLY RUSH −64% · DUMPING −55% · BREAKOUT −25% |

No list or call is positive "95–100% of the time". Nothing on this site is. **The honest edge is not losing**: be in
fewer coins for longer, take profit from winners, and keep the seat count small while the card is small. A record
that reads −80% is mostly coins that vanished (no price = −100%). That is the point: those coins rug.

## The mindset
1. **Evidence first, every time.** Every list, call, exit and wallet signal keeps its OWN settled record (noted once,
   judged 1h later, no price = −100%). A new signal ships as a READ, and it moves money only once its own record is
   positive (`PROVE_FIRST`, `CALL_AUTO_MIN`, `smart` key ≥ 5). A busted record turns a feature into a warning
   (`busted()` in CoinVital: ≥ 30 settled, median ≤ −20%).
2. **Warn, never block the owner.** Their picks go through the 409 → "I understand — pick it anyway" path. Engine
   rules limit the ENGINE. Sizing (tickets) is fine, refusals are not.
3. **Never promise.** No "100%", no "guaranteed", no profit forecasts. Say the median and the sample size.
4. **Read the money before the code.** Start every task with a cash check (`realBook.reconciliation`, `versus`,
   `realized`). When the owner says "why did it buy X", read the card event before the buy and the leg's `bought` tag.
   When they say "button doesn't work", compare stored `realCfg` with `cfgEff` (ladder / real_guard / seat fit sit on top).
5. **Small card = few seats, small tickets, long holds.** 5-min rounds are the owner's choice. Don't lobby for a slower
   clock. Lobby for min hold, locks and trims.
6. **Degen UI = 5-second read.** Verdict word + meter + ≤ 3 facts + one tap. Buys/sells bar on every coin. Real icons
   (SVG globe / X / Telegram), socials first, record badge on every call (`+0.9%/1h`).
7. **Ship one and done.** Test (fake network), gate (`bash scripts/gate.sh`), fetch + rebase, push to main, restart the
   backend only when no order is pending, check one keeper (`pgrep -f "uvicorn reputation_service" | wc -l` = 1).

## The engine's shape (where to plug things in)
- Per-coin data → the coin-edge record (`/api/reputation/edge`, `lib/coinEdge.js`). Never a new poller.
- Ranking → `confluence.edge` (lists × call × learned combo × your real trades × capped hand tilts).
- Learning → `real_learn` (every coin leaving the real card is a lesson), `degen` (smart wallets, bursts, callout spikes),
  `flow` (90s tape: flow exit, rug radar, flow entry), `owner_moves` (owner actions judged 30 min later).
- Records → `trench.meta_track` / `meta_proof` keyed files in `backend/data/*_proof.json`.
- Real-card actions → `POST /admin/arena/prime {leg | skim | manualSell | pickSwap | fillSeat | realCfg …}`; the keeper
  (`_fw_tick`) does the chain work. Never sign or move Fuse-wallet money yourself. Never press money buttons in a browser.

## Next degen moves worth building (owner hasn't approved yet; offer them, don't assume)
- **🎟 Picks ride as tickets while your record is red.** A hand pick goes in at a ticket size (e.g. 25% of a seat)
  while `versus.you` is negative over 24h, and gets a full seat once it turns green. Sizing only, never a refusal.
- **🏠 Auto initial-out on every winner.** The only owner move with a positive record. Turn `trenchHouseAt` into a
  card-wide "pull the stake at +X%" for every coin, so winners ride on house money.
- **⏳ 30-minute pick lock.** The ledger says exits inside 15 min lose. A hand pick can't be hand-swapped for 30 min
  (warn + acknowledge, like picks).
- **🧲 Fed + 🔥 trending overlap lane.** The two least-bad lists. Coins in both get their own record, and the engine
  takes them once that record is ≥ 0.
- **🐳 Smart-wallet auto-follow.** Smart wallets started settling 2026-10-08. Once the `smart` key is proven (≥ 5
  settled, median > 0), a smart buy may jump a coin to the front of Coming up.
- **Scrap candidates:** the 📣 Pump signals tab (calls −54%, double −83%; fed is the only part worth keeping) and the
  🆕 New launches tab (−81%). Ask before removing tabs the owner uses daily.


---
<a id="perps"></a>
## ⟪PERPS⟫ (was docs/PERPS.md)

# 📉 FEELESS PERPS — everything about the perps / options desk (one page)

> Planning status and remaining requests: [HANDOFF.md](HANDOFF.md) `## TASKS`. This file retains the technical specification/history; do not maintain a second active backlog here.

Owner, 2026-10-23: *"perps / options TRADING DASH, quick trades, as low as $1 … all mechanics a real perps desk has … only realtime vitals …
true chart data ALWAYS … live TP / SL before the trade on the chart … look better than other perps dashes."* Read this before touching
anything perps. Money rules (CLAUDE.md › Money rules) and `docs/RULINGS.md` #1 / #8 still apply.

## 1 · Venues — the truth (researched 2026-10-23, re-checked at the owner's ask "any chain, Base, BNB… US based, 500× with $1")
| Venue | Chains | Leverage / min | US users | In FEELESS |
| --- | --- | --- | --- | --- |
| **Jupiter Perps** | Solana | 1.1–100× here (API 250×) · **$10** | owner lifted the 🇺🇸 rule for Jupiter only (DECISIONS #8) | ✅ LIVE — wallet signs, TP / SL, partial close |
| **Kalshi via DFlow** (event contracts as Solana tokens) | Solana | binary up / down · **$1** ($0.01–$1 a contract) — BTC · ETH · SOL · DOGE · XRP (15-min) + S&P 500 · Nasdaq-100 (hourly at-the-money) | ✅ CFTC-regulated | ⏳ built — on with `DFLOW_API_KEY` |
| **gTrade** (Gains Network) | Solana · Arbitrum · Base · Polygon · MegaETH | up to 500× (degen pairs) · tiny mins | ❌ terms (gains.trade/terms-of-service): use from the US is "STRICTLY PROHIBITED, REGARDLESS OF THE USER'S IP ADDRESS", VPNs too; users warrant they are not US persons | ❌ not wired — owner decision pending (non-US-only attestation gate is the default proposal) |
| **Aster** | BNB · Arbitrum | up to 1001× BTC | ❌ terms list the US as prohibited | ❌ |
| **Hyperliquid** | its L1 | 40–50× · $10 notional | ❌ front end restricts US | ❌ — Payward (Kraken) + Bitnomial announced a US-regulated HIP-3 market (2026-09-16, allowlisted, NOT live) → add it the day it launches |
| **Avantis** | Base | up to 500× | unverified (terms moved) | ❌ |
| **Kalshi BTCPERP** | Kalshi account (not tokenized) | perp · CFTC | ✅ live since 2026-06-03 (Webull resells from Nov 2026) | ❌ account venue — no wallet path |
| **Kraken US perps (Bitnomial)** · **Coinbase US futures (CFM nano)** | broker accounts | ~10× · contract mins | ✅ regulated | ❌ owner dropped broker-API orders ("too many steps") |
A site loading from the US is not permission: the venue's own terms decide. Standing rule 1 + DECISIONS #8 stand until the owner records otherwise.

## 2 · What the desk is (frontend)
`components/PerpsDash.jsx` (the Avenue's 📉 Perps room via `CityAvenue.PerpsDesk`; preview `/dev/perps`) + `components/perps/*` +
`styles/perpsDash.css` (pink meta, `pd-` frame · `pc-` chart · `pt-` ticket · `pp-` positions · `kd-` Kalshi).
- **Top** — brand · SOL / ETH / BTC tabs (true price ticking on every trade, 24 h %, prints/min bar) · OPEN P&L (all positions, marked live).
- **Live strip** — MARK (last Coinbase print, prints/min, seconds since the print) · JUP ORACLE + basis (true vs oracle) · 24 h % + volume ·
  24 h RANGE (marker) · SPREAD (bp, bid / ask) · BORROW / HR long vs short (Jupiter pool) · WHO'S CROWDED (Jupiter long vs short utilisation) ·
  OI + FUNDING (global board).
- **Chart** (`perps/PerpsChart.jsx`) — TRUE candles: Coinbase Exchange REST (1m / 5m / 15m / 1h, 300 bars) + the live candle folded from every
  trade on the shared websocket (`lib/cbFeed.js`: `fetchBars`, `foldTrade` — a new bucket opens at the previous close). Levels drawn as price
  lines: the ticket's ☠ LIQ, **TP + SL (drag them — grab within 8 px)**, each position's entry / ☠ / TP / SL. The scale always holds your levels
  (☠ only within 4 %).
- **Ticket** (`perps/PerpTicket.jsx`) — LONG / SHORT · collateral ($ input + $10 / 25 / 50 / 100 / 250) · leverage slider 1.1–100 + chips ·
  vitals SIZE / ENTRY / ☠ LIQ (+% away) / FEE + borrow / h · **TP / SL before the trade** (price, % chips, or chart drag; side-checked live;
  $ P&L + ROE at each; R : R) → REVIEW (Jupiter's quote: entry, ☠, fee, Jupiter's own P&L at each trigger) → SIGN + OPEN.
- **Positions** (`perps/PerpPositions.jsx`) — live P&L / ROE on the true price, ☠ distance meter, TP / SL chips (move · cancel · + add), close
  25 / 50 / 75 / 100 %.
- **⏱ Kalshi UP / DOWN** (`perps/KalshiDesk.jsx`) — a market picker (BTC · ETH · SOL · DOGE · XRP · S&P 500 · NASDAQ, each with its live UP %)
  and the picked window's odds (target vs true price, countdown, $1 pays UP / DOWN, the nearest ladder strike; indexes = the soonest hourly
  window's at-the-money strike, `kalshi_odds.atm`);
  with the key: 🪪 Proof → UP / DOWN from $1 → fill status → your contracts → REDEEM winners.
- **🧪 Practice** — `PaperPerps` (paper book at the real mark).
- **🌊 LIVE FLOW** (`perps/LiveFlow.jsx`, always beside the positions) — TAKER PRESSURE (market buys vs sells $ over 60 s + 5 min from every
  Coinbase print; Coinbase's `side` is the maker's, so a filled resting sell = a taker BUY) · MOMENTUM 1 m / 5 m / 15 m / 1 h (1-second samples) ·
  RVOL (last hour, annualized) · 🐋 WHALE PRINTS (BTC $50K+ · ETH $25K+ · SOL $10K+) · 🏆 Jupiter's top traders THIS week on the market (tap →
  case file). Pure helpers in `lib/cbFeed.js`: `flowOf`, `whales`, `moveOf`, `rvol`.
- Pure math + signing: `lib/perps.js` (`perpPlan`, `quoteMatches`, `atPrice`, `tpOk`, `slOk`, `levelAt`, `rr`, `liveRow`, `signTx`, `signRun`).

## 3 · Backend
| Endpoint | What |
| --- | --- |
| `GET /api/reputation/familia/perps` | the global board (mark, 24 h, funding APR, OI, max lev) — `perps_desk.py`, 1 read / min |
| `GET /api/reputation/familia/perps-real?address=` | Jupiter pools (fee, borrow / h, utilisation, room) 60 s · **market-stats** (Jupiter mark, 24 h hi / lo / vol) 10 s · the wallet's positions (+ TP / SL requests, fees, borrow) |
| `POST /api/reputation/familia/perps-real` | `act`: open (default; `tp` / `sl` + `mark` ride the open) · `close` (`pct` 25 / 50 / 75 / 100 + `size`) · `tpsl-add` · `tpsl-edit` · `tpsl-cancel` → Jupiter builds, `jup_perps.verify` checks, returns `{transaction, action, quote, tpsl}` |
| `POST /api/reputation/familia/perps-real/execute` | the wallet-signed tx → Jupiter `/transaction/execute` (actions: increase / decrease-position, create / update / cancel-tpsl) |
| `GET /api/reputation/familia/perps-real/leaders?asset=` | Jupiter's weekly top traders (P&L + volume) — `jup_perps.leaders`, 5 min |
| `GET /api/reputation/familia/kalshi` | Kalshi odds per coin (15-min + nearest strike of the soonest day), 10 s, `tradable` = DFlow key present |
| `GET /familia/kalshi/proof?address=` · `POST /familia/kalshi/order` · `POST /familia/kalshi/send` · `GET /familia/kalshi/status` · `GET /familia/kalshi/positions` | the Kalshi trade path (503 until `DFLOW_API_KEY`) |

- `backend/jup_perps.py` — `clean_open` (+ `tpsl_levels`, `tpsl_item`: Jupiter's LIVE shape `{requestType, triggerPrice ×1e6, desiredMint USDC,
  entirePosition}` — the published spec's `asset / inputToken` shape is rejected by the live API), `close_body` (partial), `tpsl_body`,
  `verify` (user pays + signs, ≤ 2 keeper signers, only Perps / Doves / Solana programs), `positions`.
- `backend/kalshi_odds.py` — `fifteen`, `nearest` (soonest day only), `payout`. Public Kalshi API, `limit=1000` (the ladder is 300+ rows).
- `backend/kalshi_trade.py` — DFlow hosts, `ticket`, `order_params`, `matches` (order = ticket), `verify` (fail-closed: user is the ONLY signer,
  programs ⊆ {DFlow prediction `pReDicT…`, DFlow router `DF1ow4…`, System, Token, Token-2022, ATA, ComputeBudget, Memo}, no top-level token /
  SOL transfers out, no approve / set-authority / nonce), `remember` / `take` (fingerprint = message minus blockhash, 10 min, sent ONCE),
  `redeemable`, `position`. Read on-chain 2026-10-23: real DFlow prediction orders are signed by the user alone.
- Jupiter Perps API spec: `https://perps-api.jup.ag/v1/docs` (Redoc; also `/tpsl`, `/orders/limit`, `/positions/close-all`, `/trades`,
  `/top-traders`, `*-with-fee` execute actions — the owner's own fee, not wired yet).

## 4 · Data rules (true data, always)
- Chart + MARK = **Coinbase Exchange** (US-regulated venue): `api.exchange.coinbase.com/products/{SOL|ETH|BTC}-USD/candles` + `wss://ws-feed.exchange.coinbase.com` `ticker`.
  ONE shared websocket for the page, re-render ≤ 4× / s, reconnect with backoff. Pool-swap candles (`PriceChart`) are never a perps mark.
- The trade fills at **Jupiter's oracle** — shown beside the mark with the basis.
- Pyth's public Hermes stream + benchmarks shim now 401 / 404 (2026-10-23) — not used.

## 5 · Guards (never weaken without a test)
Jupiter: SOL / ETH / BTC · 1.1–100× · $10–$1,000 collateral · 1 % slippage · TP above / SL below a long's price (reverse for a short), SL
between the price and ☠ in the UI · the quote must match the ticket (side, size ±10 %) · `verify` before the wallet sees it and again at execute.
Kalshi: $1–$500 a ticket · Proof verified server-side before a buy (cache `true` only) · order = ticket (mints, in-amount) · fail-closed verify ·
send only a fingerprint FEELESS built, once · redeem only settled winners with redemption open.

## 6 · Tests
`backend/tests/test_jup_perps.py` · `test_kalshi_odds.py` · `test_kalshi_trade.py` · `frontend/src/lib/perps.test.js` · `lib/cbFeed.test.js` ·
`components/PerpsDash.test.js` · `components/perps/PerpTicket.test.jsx` · `components/CityAvenue.test.jsx`.

## 7 · Your first real trade (the owner's test, ~2 min)
1. Fee City → 📉 Perps → **Walk in** (or the Avenue directory). Connect Phantom (Solana) with ≥ $11 USDC + a little SOL for fees.
2. Pick **SOL**, **▲ LONG**, **$10** (Jupiter's floor), **10×**. Tap **+5%** under TAKE PROFIT and **−2%** under STOP LOSS (or drag the lines on
   the chart). The ticket shows the $ + ROE at each and the R : R.
3. **REVIEW** → Jupiter's quote appears (entry, ☠, fee, Jupiter's P&L at each trigger). It must match the ticket or nothing is signed.
4. **⚡ SIGN + OPEN** → Phantom asks once → Jupiter's keeper lands it (a few seconds). POSITIONS shows it with live P&L, its TP / SL chips,
   and its entry / ☠ / TP / SL lines on the chart.
5. Try **50%** (partial close) and moving the TP chip → each is one more Phantom signature. **CLOSE** = all of it, USDC back to the wallet.
Verified 2026-10-23 through FEELESS's backend (build only, nothing signed): $10 SOL long 10× + TP +5 % / SL −3 % → entry $102.47, ☠ $92.50,
fee $0.06, Jupiter's P&L at TP +$4.95 / SL −$2.97; a long's TP under the price is refused.

## 8 · Open (owner actions first)
1. 🔑 **DFlow production key** (requested 2026-10-23 via pond.dflow.net/get-started/api-key; 2–5 days) → `backend/.env` `DFLOW_API_KEY=` →
   restart reputation_service → Kalshi trading turns on (`tradable: true`). Then: first real $1 UP order end to end; confirm the metadata paths
   (`/market/{ticker}`, `/market/by-mint/{mint}`) on the prod host. *PayBox (MoonPay, api.paybox.sh) is NOT the DFlow key — it gives an AI
   agent your wallet / cards; don't connect it to FEELESS.*
2. First real Jupiter open with TP / SL ($10 SOL 10×) + a 50 % close + a TP move — read the position row back.
3. Limit orders (`/orders/limit`) in the ticket · the owner's fee on every open (`increase-position-with-fee`, HQ › Core).
4. Kalshi BTCPERP / Coinbase CFM perps only if the owner wants broker accounts.


---
<a id="brokers"></a>
## ⟪BROKERS⟫ (was docs/BROKERS.md)

# 🏦 THE BROKERAGE — your own broker, linked to your Familia wallet (DECISIONS #9)

> Planning status and remaining requests: [HANDOFF.md](HANDOFF.md) `## TASKS`. This file retains the technical specification/history; do not maintain a second active backlog here.

**What:** users link THEIR broker (Webull · Coinbase · Kraken · Alpaca · E*TRADE · more, via SnapTrade) to their Familia wallet session, see
cash / buying power / positions live in 🏦 THE BROKERAGE (a room inside YOUR MONEY in Fee City), and BUY / SELL stocks · ETFs · crypto from $1
in their own account. US-legal by construction (their own regulated broker). Schwab is read-only via SnapTrade; Robinhood does not allow trading.

**$0 START — NO OWNER SETUP (2026-10-24):** each user pastes their OWN free **Alpaca** keys (alpaca.markets: free account, no minimum,
commission-free US stocks · ETFs · crypto; PAPER keys work the same minute, LIVE after Alpaca's ID check). FEELESS checks the keys live against
the account (`GET /v2/account`), then seals them to the wallet with `BROKER_SECRET_KEY` — or, when that is not set, a key FEELESS makes for
itself (`backend/data/.broker_seal`, 0600). Endpoint: POST `/familia/broker/keys` (`{remove: true}` deletes them); orders with `accountId:
'alpaca'` go to Alpaca `/v2/orders` (stocks `day`, crypto `BTC/USD` `gtc`). Preview `/dev/broker` (`?linked`).

**OWNER'S OWN BROKER — a SnapTrade PERSONAL key (set 2026-10-24, `PERS-…`):** reaches the owner's own linked accounts only (no SnapTrade
users, no userId / userSecret on calls — `brokers.personal`, `_brk_q`). The owner's (staff) wallet sees 🔗 LINK MY BROKER → SnapTrade's portal →
log in to TradeStation (or any broker) ONCE → from then on 🏦 shows it live and trades it. Everyone else gets the Alpaca door. To serve every
user's own broker through SnapTrade, switch to a commercial key (the code already handles both).

**Any broker via SnapTrade — commercial key setup:** sign up at snaptrade.com (Build tier: free, 5 connections with trading; Launch: $100 / mo + $1–2 per user) →
put in `backend/.env`: `SNAPTRADE_CLIENT_ID=`, `SNAPTRADE_CONSUMER_KEY=`, `BROKER_SECRET_KEY=` (any long random string — seals each user's
SnapTrade secret) → restart reputation_service. Until then the building shows 🔒 and every endpoint answers 503.

**User flow:** sign in to Familia (wallet) → 🏦 → 🔗 LINK MY BROKER → SnapTrade's portal (log in to your broker; FEELESS never sees the password)
→ back in FEELESS: accounts + positions live (20 s) → ticker + $ → BUY / SELL (confirmed on screen) → sent to your broker.

**Code:** `backend/brokers.py` (signing — HMAC-SHA256 over {content, path, query} · `seal` / `unseal` · `order_body` guards: your own account,
real ticker, BUY / SELL, Market $1–$2,500 or units, Limit ≤ $2,500 · `view`) · endpoints in reputation_service: GET `/familia/broker`, POST
`/familia/broker/link` · `/order` · `/unlink` (all on `_session_or_401`) · `frontend/src/components/BrokerDesk.jsx` + `styles/brokerDesk.css` ·
`lib/cityPlan.js` place `brokers` (in YOUR MONEY). Tests: `backend/tests/test_brokers.py`, `CityAvenue.test.jsx`.

**Next:** the brokers' totals inside YOUR MONEY's tower · options (SnapTrade `BUY_TO_OPEN` …) · Kalshi BTCPERP / Webull perps when SnapTrade
exposes them · the first real link + $5 SPY buy by the owner.


---
<a id="go_live"></a>
## ⟪GO_LIVE⟫ (was docs/GO_LIVE.md)

# FUSE — go live with real money

> Planning status and remaining requests: [HANDOFF.md](HANDOFF.md) `## TASKS`. This file retains the technical specification/history; do not maintain a second active backlog here.

There are two tracks. **A** puts FEELESS's own tier cards on real money from your **Fuse Circle wallet**; the code is built and
runs on the local server. **B** makes *users'* cards hands-free on-chain (the FUSE Card contract). No Squads: the Fuse Circle
account is the one key for both.

## A · Tier cards on real money (Fuse Circle wallet) — local server

| # | Step | Where | Status |
|---|------|-------|--------|
| 1 | **Circle keys**: `CIRCLE_API_KEY` + `ENTITY_SECRET` in `backend/.env`, then `cd circle && npm install && node setup.mjs`. | terminal | done if HQ › Money › Circle lists wallets |
| 2 | **Signing**: the keeper builds each swap from a Jupiter quote, checks your limits, Circle signs it (sign only), FEELESS broadcasts and books the confirmed fill. | built | ✅ on (you approved) |
| 3 | **Create the Fuse wallet**: HQ › Money › Circle → new **SOL** wallet named "Fuse" → send it SOL (cards + about 0.03 SOL kept back for network fees). | HQ | you |
| 4 | **Jupiter + RPC**: `JUPITER_API_KEY` (Swap API; falls back to lite-api) and a dedicated `HELIUS_RPC_URL` / `SOLANA_RPC_URL`. | `backend/.env` | check |
| 5 | **Pick + limit**: HQ › Fuse › 👛 Fuse wallet → pick the wallet, set max per card / per swap / daily, slippage, max impact. Then 🔍 **Dry run** a tier: real quotes, nothing signed. | HQ | ready now |
| 6 | **Arm + fund one tier small** ($20): the SAME card goes real — same coins, phase, clock and config, time + P&L start over; the keeper buys its coins and every swap shows on the card with its tx + an inbox notice. | HQ | you |
| 7 | **Watch the audit trail**: every order (quote, fill, impact, network fee, tx). After 3 real fills, paper calibrates its impact + fees to match. | HQ › 👛 | automatic |
| 8 | **Scale**: raise the per-card cap, fund more tiers. ⏸ halts a card, ↩ sells it back to SOL (back to paper), the kill switch pauses everything. | HQ › 👛 | you |

Docs: Circle wallets https://developers.circle.com · Jupiter Swap API https://dev.jup.ag/docs · Solana fees https://solana.com/docs/core/fees

## B · Users' cards hands-free (FUSE Card contract)

Users still approve every card action with one tap. To make it truly sign-once (the card runs TP / SL / compound / payout to the
owner's wallet on its own, and FEELESS never holds their keys):

| # | Step | Who | Link |
|---|------|-----|------|
| 1 | **Swap adapter**: Raydium CP-Swap `keeper_sell_cpmm` / `keeper_buy_cpmm` — ✅ built + tested against the REAL Raydium program on localnet (contracts README v0.3). | dev ✅ | https://github.com/raydium-io/raydium-cp-swap |
| 2 | **Price bound**: ✅ Raydium's own on-chain TWAP (≥5 min, spot within ±10%, triggers read the TWAP) — a one-block push can't fire a sell (tested). Pyth / Switchboard optional on top. | dev ✅ | https://docs.pyth.network |
| 3 | **Devnet run**: ✅ deployed `GKE9e3M8shuD2nwTwchgP4BH22fiN6hyQrp4qwhkurpa` (plain build) + config → Raydium devnet `DRaycpLY…` (config `36k9tXVE…`, `migrations/devnet-init.ts`). Next: one card on a devnet Raydium pool for a week (needs the keeper host, B·7). Devnet SOL: Alchemy devnet `requestAirdrop` works (no GitHub needed). | dev ✅ / you | https://solana.com/docs/core/clusters · https://faucet.solana.com |
| 4 | **External audit** of `fuse_card`. | auditor | https://osec.io · https://neodyme.io · https://www.sec3.dev · https://www.halborn.com |
| 5 | **Upgrade authority = a Fuse Circle wallet** (instead of Squads): `solana program set-upgrade-authority <PROGRAM_ID> --new-upgrade-authority <CIRCLE_ADDR>`. Use a **separate** Circle wallet from the trading one, and keep its API key off the server. | you | https://solana.com/docs/programs/deploying |
| 6 | **Mainnet with small caps** ($100 per card), raised as it proves out. | you | https://www.anchor-lang.com/docs |
| 7 | **Keeper host**: an always-on host for the engine loops + keeper. | you | https://railway.app |
| 8 | **Launch hygiene**: `ALLOWED_ORIGINS` = the real domain, re-check fees (HQ › Fuse › 💲 Fees), unpause the season. | you | HQ › Security |

HQ › Fuse › ⛓ Contract tracks B 1–5 (owner only, proof required). A user card goes hands-free only when every step is ✅.

### Is it a real contract or a wallet full of coins?
- **Track A (now):** the tier cards are coins in your Fuse Circle wallet, traded by the FEELESS keeper under server-enforced limits. Every
  trade is on-chain and audited in HQ, but the RULES live on the server.
- **Track B (the FUSE Card program):** the rules are in the contract — the card account holds the coins, only the owner withdraws, the keeper
  can only sell on an on-chain trigger (Raydium TWAP), only through Raydium, with capped slippage, paying only the owner. HQ tier cards can
  move into it (HQ cards = up to 12 legs) once B·3–B·5 are done. Until the audit, it is localnet / devnet only.


---
<a id="counsel_brief"></a>
## ⟪COUNSEL_BRIEF⟫ (was docs/COUNSEL_BRIEF.md)

# ⚖ COUNSEL BRIEF — for the lawyer who reads `docs/RULINGS.md` before real volume

Prepared 2026-10-23 by Claude (an AI, **not a lawyer — this is not legal advice**). Its only job: save the lawyer's time by stating, for
each decision, exactly what the product does today, the question to answer, and the facts they will ask for. Answers go back into
`docs/RULINGS.md`; anything counsel flags waits.

## 0 · Facts that apply to everything
- **Non-custodial.** Users sign every transaction in their own wallet. FEELESS never holds keys, user funds or pooled money (the one
  exception is the owner's own "real card" wallet, run for the owner only).
- **FEELESS earns a swap fee** on user swaps (Jupiter Swap API; the fee lands in FEELESS's own SOL / USDC token accounts). Buying $FEE /
  FEECAT / rFEE is fee-free. Rates are set in HQ › Core.
- **US users** are served. There is **no geo / KYC check in the product today** (verified 2026-10-23: no country detection anywhere in the
  code). The standing rule is "no geo loopholes": features that are closed to US persons must not be routed at all.
- **Tokens the project issued:** $FEE, rFEE, FEECAT. Points: season points + MP (never bought, never cashed out).

## 1 · Paper perps + a venue hand-off (DECISIONS #1)
- Does: simulated perps with real mark / funding / liquidation math; "Take it real" opens Kraken Pro / Coinbase on the user's own account.
- Ask: is a link-out with the user's setup (market, side, size, leverage) "soliciting or accepting orders" — i.e. introducing-broker or
  CTA activity — or plain information? Does showing funding / liquidation math to US users need disclaimers?
- Also: the Perps building lets anyone **buy JLP** (Jupiter's perps-LP token) by swap. Is routing US users into JLP acceptable?

## 2 · Real-money cats, option A (DECISIONS #2)
- Does: an automated "cat" (rule engine or an AI model) PROPOSES a buy / sell with evidence; one tap prefills the swap; the user signs.
- Ask: are per-user automated trade proposals "advice" (investment-adviser / CTA) when the asset is a memecoin? Does the paper record
  shown beside each proposal meet performance-advertising rules? Does a per-decision markup (switchable in HQ) change the answer?

## 3 · One points currency (DECISIONS #3)
- Does: points earned for activity → spent on cosmetics, raffle tickets and family MP (1 pt → 100 MP, ≤ 1,000 pts / week). MP → FEECAT
  redemptions are approved by hand by the owner.
- Ask: is **MP → FEECAT** (points → a token with market value) a prize / sweepstakes / securities issue? Are points-funded **raffles**
  lotteries if the prize has value (no purchase is possible — points are never sold)? Is the free weekly **rep market** (chips on calls)
  outside CFTC event-contract rules because nothing of value is staked?

## 4 · No pooled family money (DECISIONS #4)
- Does: families have no shared wallet; the block reads each member's own positions (display only).
- Ask: confirm a shared leaderboard of members' real positions (opt-in) creates no pooled-investment / club issue.

## 5 · Block readers (DECISIONS #5) — engineering, not legal. No question for counsel.

## 6 · New since DECISIONS (2026-10-23) — please review too
- **The Money Desk** (every Familia money building): shows live APYs, projects compounding, and builds a **Jupiter Lend deposit** (Jupiter
  builds it, FEELESS checks every program in it, the user signs) or a **SOL → liquid-staking-token swap**. Ask: is an interface that
  builds deposits into a third-party lending protocol for US users a broker / "Earn program" (the Gemini / Genesis line) issue? Does the
  APY + "doubles in N years" projection need yield disclaimers beyond the risk line shown on every desk?
- **Tokenized treasuries** (USDY, ONyc, BUIDL, …) are **not routed** — their issuers exclude US persons and FEELESS has no geo check.
  Ask: is showing their APY as information (no action) acceptable?
- **The Launch wizard** (launch a coin with fee routing to the creator, holders, buyback-burn; anti-sniper tax; locked launch). Ask: does
  FEELESS facilitating token issuance + declaring creator revenue shares make it an issuer's agent / platform with securities exposure?
- **⚡ Real leverage (DECISIONS #7)** — the Perps building + the Money Desk's MOON tab build a **Jupiter Lend borrow** from the user's own
  wallet (lock SOL / BTC / JUP, borrow USDC against it, buy more of the coin = 1.3–1.7× long with a liquidation price). Not a futures
  contract; FEELESS never lends, holds the collateral or signs. Ask: is an interface that builds a margined spot purchase through a
  third-party lending protocol a "retail commodity transaction" (CEA 2(c)(2)(D)) issue for US users — does the coins landing in the user's
  own wallet at once count as "actual delivery"? Does it make FEELESS an introducing broker? Is the risk line on the desk enough?
- **The swap fee itself** on non-custodial swaps: confirm no money-transmitter (FinCEN MSB / state MTL) exposure, given FEELESS never
  controls the user's funds and the fee is part of the signed transaction.

## 7 · What counsel will ask for (have it ready)
Entity + jurisdiction · terms of service + privacy policy (the site banner already says "non-custodial … not financial advice") · the fee
schedule (HQ › Core) · token docs for $FEE / rFEE / FEECAT (supply, who holds what, any promises made) · volumes by feature · whether US
traffic can be blocked per feature if they ask (today it cannot — that is engineering work to scope first).
