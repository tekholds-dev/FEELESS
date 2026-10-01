// One-click Fuse in: the pure part. Each picked pool becomes ONE normal FEELESS swap paid in SOL (same /quote →
// /simulate → wallet signs → /execute path as Quick trade; no new money path). The wallet approves all of them at once
// (signAllTransactions), the server still checks every signed message equals its quote.
export const SOL_MINT = 'So11111111111111111111111111111111111111112';

// The coin a leg buys: the pool's base token; for a SOL/X pool (base is SOL) it buys the other side.
export function legTarget(leg) {
  if (leg.baseAddress && leg.baseAddress !== SOL_MINT) return { mint: leg.baseAddress, symbol: leg.symbol };
  if (leg.quoteAddress && leg.quoteAddress !== SOL_MINT) return { mint: leg.quoteAddress, symbol: leg.quote };
  return null;
}

// Quote requests for every leg with something to buy and a positive SOL amount (dust under 0.001 SOL is skipped).
export function fuseOrders(legs, wallet, slippageBps = 100) {
  return (legs || []).map(leg => {
    const t = legTarget(leg); const sol = Number(leg.sol);
    if (!t || !(sol >= 0.001) || !wallet) return { leg, skip: !t ? 'Nothing to buy in a SOL/SOL pool' : 'Too small (< 0.001 SOL)' };
    return { leg, target: t, request: { input_mint: SOL_MINT, output_mint: t.mint, amount: sol.toFixed(9).replace(/\.?0+$/, ''), slippage_bps: slippageBps, wallet } };
  });
}

// Every order shown for review must match what's on screen: same coin, buy side, same SOL amount.
export const orderMatches = (o, order) => Boolean(order) && order.input_mint === SOL_MINT && order.output_mint === o.request.output_mint
  && Math.abs(Number(order.amount) - Number(o.request.amount)) < 1e-9;
