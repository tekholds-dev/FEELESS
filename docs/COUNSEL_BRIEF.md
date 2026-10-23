# ⚖ COUNSEL BRIEF — for the lawyer who reads `docs/DECISIONS.md` before real volume

Prepared 2026-10-23 by Claude (an AI, **not a lawyer — this is not legal advice**). Its only job: save the lawyer's time by stating, for
each decision, exactly what the product does today, the question to answer, and the facts they will ask for. Answers go back into
`docs/DECISIONS.md`; anything counsel flags waits.

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
