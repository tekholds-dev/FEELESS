# 📉 FEELESS PERPS — everything about the perps / options desk (one page)

Owner, 2026-10-23: *"perps / options TRADING DASH, quick trades, as low as $1 … all mechanics a real perps desk has … only realtime vitals …
true chart data ALWAYS … live TP / SL before the trade on the chart … look better than other perps dashes."* Read this before touching
anything perps. Money rules (CLAUDE.md › Money rules) and `docs/DECISIONS.md` #1 / #8 still apply.

## 1 · Venues — the truth (researched 2026-10-23)
| Venue | Status in FEELESS | US users | Min | Notes |
| --- | --- | --- | --- | --- |
| **Jupiter Perps** (Solana) | ✅ LIVE — wallet signs | owner lifted the 🇺🇸 rule for Jupiter only (DECISIONS #8, owner's legal risk) | **$10 collateral** | SOL · ETH · BTC, 1.1–100× (API allows 250×), TP / SL ≤ 150× |
| **Kalshi via DFlow** (Solana tokens) | ⏳ built, waits on DFlow's production key | ✅ CFTC-regulated, US-legal | **$1** (contracts $0.01–$1) | 15-min UP / DOWN + hourly / daily strike ladders = binary options; Proof KYC |
| Hyperliquid · gTrade · Drift · dYdX | ❌ not wired | ❌ bar US persons in their own terms | — | would break standing rule 1 — owner: "how ima use HYPE in the US" |
| Coinbase CFM nano perps · Kalshi BTCPERP · Webull (Nov 2026) | ❌ | ✅ but KYC'd broker accounts, no wallet signing | — | owner dropped broker-API orders ("too many steps") |

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
- **⏱ Kalshi 15-MIN** (`perps/KalshiDesk.jsx`) — live odds (target vs true price, countdown, $1 pays UP / DOWN, the nearest ladder strike);
  with the key: 🪪 Proof → UP / DOWN from $1 → fill status → your contracts → REDEEM winners.
- **🧪 Practice** — `PaperPerps` (paper book at the real mark).
- Pure math + signing: `lib/perps.js` (`perpPlan`, `quoteMatches`, `atPrice`, `tpOk`, `slOk`, `levelAt`, `rr`, `liveRow`, `signTx`, `signRun`).

## 3 · Backend
| Endpoint | What |
| --- | --- |
| `GET /api/reputation/familia/perps` | the global board (mark, 24 h, funding APR, OI, max lev) — `perps_desk.py`, 1 read / min |
| `GET /api/reputation/familia/perps-real?address=` | Jupiter pools (fee, borrow / h, utilisation, room) 60 s · **market-stats** (Jupiter mark, 24 h hi / lo / vol) 10 s · the wallet's positions (+ TP / SL requests, fees, borrow) |
| `POST /api/reputation/familia/perps-real` | `act`: open (default; `tp` / `sl` + `mark` ride the open) · `close` (`pct` 25 / 50 / 75 / 100 + `size`) · `tpsl-add` · `tpsl-edit` · `tpsl-cancel` → Jupiter builds, `jup_perps.verify` checks, returns `{transaction, action, quote, tpsl}` |
| `POST /api/reputation/familia/perps-real/execute` | the wallet-signed tx → Jupiter `/transaction/execute` (actions: increase / decrease-position, create / update / cancel-tpsl) |
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
