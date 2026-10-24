# 🏦 THE BROKERAGE — your own broker, linked to your Familia wallet (DECISIONS #9)

**What:** users link THEIR broker (Webull · Coinbase · Kraken · Alpaca · E*TRADE · more, via SnapTrade) to their Familia wallet session, see
cash / buying power / positions live in 🏦 THE BROKERAGE (a room inside YOUR MONEY in Fee City), and BUY / SELL stocks · ETFs · crypto from $1
in their own account. US-legal by construction (their own regulated broker). Schwab is read-only via SnapTrade; Robinhood does not allow trading.

**Owner setup (once, ~5 min):** sign up at snaptrade.com (Build tier: free, 5 connections with trading; Launch: $100 / mo + $1–2 per user) →
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
