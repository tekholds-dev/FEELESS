# 🧭 DECISIONS — made 2026-10-23 on the owner's go ("you got my ok and do all decisions")

Each decision picks the path that ships now WITHOUT making FEELESS a custodian, a broker or a betting house — those need licences no
code can grant. A lawyer should still read this page before real volume; anything marked LATER waits for that read or for an audit.

## 1 · Perps orders inside FEELESS (F0.1 · A · A1)
**Decided: in-building PAPER perps + a one-tap handoff to the regulated venue for the real order.** FEELESS never places, routes or holds a
perps order or margin. Placing futures orders for US users on someone else's account is introducing-broker territory (CFTC / NFA); offshore
venues stay blocked for US users (rule 1c). So the Perps building now trades **paper**: pick the market, long / short, size, leverage →
a live position with the real mark price, real funding accruing, liquidation at the real distance, P&L ticking — then "Take it real on
Kraken Pro / Coinbase ↗" opens the venue with your setup in hand. LATER: a venue's official partner API (OAuth on the user's own account).

## 2 · Real-money cats (custody + pricing — docs/REAL_CATS.md)
**Decided: option A — the user's own wallet signs every trade (non-custodial).** A real cat watches the board with its brain and limits and
PROPOSES each buy / sell with its evidence; one tap opens the swap with the coins and amount set; the user presses Get quote and signs —
the same engine, guards and receipts as every FEELESS swap. FEELESS never holds a cat's money or keys (option B = custody, rejected).
Option C (an on-chain cat program trading inside the user's signed limits) is LATER — it needs the program, an audit and a devnet run. *owner- do this, put links in for me to signup and have wallets created per user payment- part of payment go to feeless and other goes into new agent wallet, agent teading or general selections must open different selections after for general than trading*
**Pricing:** no extra charge to run a cat*onetime $2 comes out of minimal 10 per agent up to 4 cats per user* — each trade it proposes pays the normal FEELESS swap fee when the user signs it (HQ › Core). AI
brains bill their model calls from the cat's credit as today. A per-decision markup can be switched on later in HQ.
**Honesty rule:** every proposal shows the cat's own paper record (no cat has a proven edge on unseen coins yet — edge-audit).
**Built (2026-10-23):** `backend/cat_real.py` + feecat_service (REAL / PAPER / proposal actions; real needs a wallet-signed session; only the
cat's own wallet answers its proposals; every cat action now needs its owner id) · `CatReal.jsx` on the cat's desk (go real with a per-buy
budget 0.02–0.5 SOL; proposals with a draining 15-min clock; ✍ Sign it → the swap opens with the coins + amount set; a confirmed swap marks it
done with its signature) · each proposal also lands in the wallet's inbox (`/internal/notify`). Preview `/dev/cats`.

## 3 · One points system (economy)
**Decided: season points are the ONE wallet currency, earned everywhere, never bought with money and never cashed out.**
- Earned: daily rewards, calls that hit, rep-market wins (chips → points at the market's own rate), Familia play.
- Spent: the points shop (styles, chat boosts, raffle tickets, badges) and now **your family's bank: 1 point → 100 MP**, at most
  1,000 points a week per wallet (so a family can't be farmed into a FEELESS payout).
- MP stays family money; MP → FEECAT redeems stay owner-approved by hand at the HQ › Core rate.
- **No real-USD rep market / Polymarket**: prediction markets on real money are regulated (CFTC) — the rep market stays free weekly chips.

## 4 · Family wallets · top-pot Fuse ($1K+)
**Decided: no pooled family wallet and no pooled pot held by FEELESS.** Every family member trades from their own wallet (the block reads
each one's positions); a top-pot Fuse is each player funding their own card from their own wallet. LATER: an on-chain pot program, audited.*owner-if i have to create 2 more circle accounts for cats and families? must be a pot/pool creation wallet? that feeless only transfers money from on raids hits etc and payout engine cant be broken or exploitedd to hit one family no more than 3 times in 12hrs*

## 5 · Block readers (Meteora DLMM · marginfi · Save · PumpSwap LP)
**Decided: a reader ships only after its account layout is checked against a real on-chain account** — a wrong "out of range" on real
money is worse than "no reader yet". Until then those buildings say so and stay under construction.

## 6 · Money surfaces lead with risk, honestly (owner, 2026-10-23: "no risk no reward — don't be making safe shit")
**Decided: every money desk has a SAFE · DEGEN · MOON dial; Familia's START COMPOUNDING opens on MOON** (tight v3 / DLMM bands on the busiest
pools) with the risk written next to the number (impermanent loss, out-of-range = 0, memecoins can halve in an hour). SAFE = staking +
Jupiter Lend. Tokenized treasuries (USDY, ONyc, BUIDL…) are never routed — their issuers exclude US persons and FEELESS has no geo check.
Perps: paper only in FEELESS; no link-outs to venues (owner); real orders wait on counsel (#1). Questions for counsel: `docs/COUNSEL_BRIEF.md`.

## 7 · Real leverage without a broker account (owner, 2026-10-23: "too many damn steps to do perps with coinbase — find another way")
**Decided: ⚡ REAL LEVERAGE on Jupiter Lend Borrow, from the user's own wallet; Coinbase / Kraken API orders dropped.** Lock SOL / BTC / JUP
in a Jupiter Lend vault, borrow USDC against it, buy more of the coin through the FEELESS swap engine → a 1.3–1.7× long (leverage capped 10
points under the vault's max loan-to-value) with the liquidation price on screen. Two signatures, no account, no KYC, no link-out, no geo
loophole (it is a loan in a protocol, not an offshore perps venue). FEELESS never lends, holds the collateral or signs; Jupiter builds every
transaction and `lend_borrow.verify` refuses it unless the user pays + signs alone and only Jupiter Lend's vaults program + Solana's own run.
Longs only (Jupiter has no stable-collateral vault to short with); shorts + 50× stay on the paper desk. Guards: SOL · BTC · JUP vs USDC only,
$2,000 per open, Jupiter's own minimum loan, every transaction simulated before the wallet sees it. Counsel question: `COUNSEL_BRIEF.md` §6.
Code: `backend/lend_borrow.py` · GET/POST `/api/reputation/familia/leverage` · `lib/leverage.js` · `components/RealLeverage.jsx` (Perps desk + MOON).
*owner- im sure theres other ecosystems than jupiter that does what jup does thats legal in usa and less entry!!!*

## 8 · Real perps on Jupiter (owner, 2026-10-23: "do jupiter as a provider … we tryna long or short — that's what matters")
**Decided by the owner: real perps through Jupiter Perps, for every user, the 🇺🇸 rule lifted for perps — the owner's call and the owner's legal
risk (#1 and rule 1c stand for everything else).** Jupiter's Perps API builds each open / close with its own quote; `jup_perps.verify` refuses it
unless the user pays + signs, only Jupiter's keeper co-signs, and only Jupiter Perps + its Doves price oracle + Solana's own programs run; the
wallet signs, Jupiter's keeper lands it (/transaction/execute). Guards: SOL · ETH · BTC, 1.1–100×, $10 (Jupiter's minimum) to $1,000 collateral
per open, 1 % price slippage, the quote must match the ticket. Simulated clean on mainnet 2026-10-23 (SOL long 25×, BTC short 50×, ETH long 100×).
NEXT (owner): more venues, any chain, more leverage (gTrade and others) · the owner's own fee on top (HQ › Core).


## 9 · Brokers linked to the Familia wallet (owner, 2026-10-24: "find easy setup brokers … make it happen … smooth for users to hook up a broker via their crypto wallet in fam, log in and get to it, see all data in the buildings")
**Decided by the owner: FEELESS connects a user's OWN broker account through SnapTrade (Webull · Coinbase · Kraken · Alpaca · E*TRADE …;
trading where the broker allows it, read-only elsewhere), keyed to their Familia wallet session.** This is the "official partner API on the
user's own account" item that `CLAUDE.md › LATER` had parked behind a lawyer — the owner chose to ship it; it goes on `COUNSEL_BRIEF.md`.
- FEELESS never sees a broker password: the user logs in on SnapTrade's Connection Portal. FEELESS keeps ONE thing per wallet — SnapTrade's
  per-user secret, sealed with Fernet (`BROKER_SECRET_KEY`); without that key nothing is stored. Unlink deletes the SnapTrade user + connections.
- Orders: only in the user's own linked accounts, a real ticker, BUY / SELL, Market ($1–$2,500 notional or units) or Limit (≤ $2,500), each
  confirmed on screen, every call on the signed Familia session (`brokers.order_body`, `/familia/broker/order`).
- US-legal by construction: the user trades their own regulated broker account (stocks, ETFs, crypto, options later) — no geo loophole.
- Owner setup: a SnapTrade account (free Build tier = 5 connections with trading; Launch $100 / mo + $1–2 per connected user) →
  `SNAPTRADE_CLIENT_ID`, `SNAPTRADE_CONSUMER_KEY` and a long random `BROKER_SECRET_KEY` in `backend/.env`. Doc: `docs/BROKERS.md`.

*brokers is cool for wwebull,snaptrade trype but im looking for better easier oath signup brokers or redirect idk but easy for user wallet to signup and go*
