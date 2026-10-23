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
Option C (an on-chain cat program trading inside the user's signed limits) is LATER — it needs the program, an audit and a devnet run.
**Pricing:** no extra charge to run a cat — each trade it proposes pays the normal FEELESS swap fee when the user signs it (HQ › Core). AI
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
each one's positions); a top-pot Fuse is each player funding their own card from their own wallet. LATER: an on-chain pot program, audited.

## 5 · Block readers (Meteora DLMM · marginfi · Save · PumpSwap LP)
**Decided: a reader ships only after its account layout is checked against a real on-chain account** — a wrong "out of range" on real
money is worse than "no reader yet". Until then those buildings say so and stay under construction.
