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

// Every order shown for review must match what's on screen: same coins, same side, same amount.
export const orderMatches = (o, order) => Boolean(order) && order.input_mint === o.request.input_mint && order.output_mint === o.request.output_mint
  && Math.abs(Number(order.amount) - Number(o.request.amount)) < 1e-9;

// Exact atoms → decimal string (never an extra decimal the API would reject).
const atomsToUi = (raw, dec) => { const s = raw.toString().padStart(dec + 1, '0'); const w = s.slice(0, s.length - dec); const f = s.slice(s.length - dec).replace(/0+$/, ''); return f ? `${w}.${f}` : w; };

// Unfuse: sell each leg's coin back to SOL — the smaller of what this Fuse bought and what the wallet still holds.
// balances = {mint: {raw, decimals}} from /balance. Legs with nothing left are skipped (already sold elsewhere).
export function unfuseOrders(legs, balances, wallet, slippageBps = 150) {
  return (legs || []).map(leg => {
    const b = balances?.[leg.mint];
    if (leg.soldUsd != null) return { leg, skip: 'Already unfused' };
    if (!b || b.decimals == null || !wallet) return { leg, skip: 'Balance unavailable' };
    const held = BigInt(b.raw || 0); const bought = BigInt(Math.floor(Number(leg.tokens || 0) * 10 ** b.decimals));
    const atoms = held < bought ? held : bought;
    if (atoms <= 0n) return { leg, skip: 'Nothing left to sell' };
    return { leg, target: { mint: leg.mint, symbol: leg.symbol }, request: { input_mint: leg.mint, output_mint: SOL_MINT, amount: atomsToUi(atoms, b.decimals), slippage_bps: slippageBps, wallet } };
  });
}
