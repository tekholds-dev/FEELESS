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
export function unfuseOrders(legs, balances, wallet, slippageBps = 150, pct = 100) {
  return (legs || []).map(leg => {
    const b = balances?.[leg.mint];
    if (leg.soldUsd != null) return { leg, skip: 'Already unfused' };
    if (!b || b.decimals == null || !wallet) return { leg, skip: 'Balance unavailable' };
    const held = BigInt(b.raw || 0); const bought = BigInt(Math.floor(Number(leg.tokens || 0) * 10 ** b.decimals));
    const all = held < bought ? held : bought;
    const atoms = pct >= 100 ? all : (all * BigInt(Math.round(Math.max(1, Math.min(100, pct)) * 100))) / 10000n;   // take-profit slice
    if (atoms <= 0n) return { leg, skip: 'Nothing left to sell' };
    return { leg, target: { mint: leg.mint, symbol: leg.symbol }, request: { input_mint: leg.mint, output_mint: SOL_MINT, amount: atomsToUi(atoms, b.decimals), slippage_bps: slippageBps, wallet } };
  });
}

// Rebalance a card back to its original weights (each leg's share of what was put in). Over-weight legs sell the excess,
// under-weight legs buy the gap with SOL — all in one approval. Legs within `tolPct` of target, unpriced or sold are left
// alone. r = a /fuses/pnl row; balances = {mint: {raw, decimals}}; px = {pairAddress: usd price}.
export function rebalanceOrders(r, balances, px, solUsd, wallet, tolPct = 5, slippageBps = 150) {
  const open = (r.legs || []).filter(l => l.soldUsd == null && px[l.pairAddress] > 0 && l.mint);
  const cost = open.reduce((a, l) => a + (Number(l.usd) || 0), 0);
  const held = open.reduce((a, l) => a + (Number(l.heldUsd) || 0), 0);
  if (!(cost > 0) || !(held > 0) || !(solUsd > 0)) return [];
  const out = [];
  for (const l of open) {
    const target = held * (Number(l.usd) || 0) / cost; const diff = (Number(l.heldUsd) || 0) - target;
    if (Math.abs(diff) < held * tolPct / 100) continue;
    if (diff > 0) {
      const b = balances?.[l.mint]; if (!b || b.decimals == null) continue;
      const atoms = BigInt(Math.floor(diff / px[l.pairAddress] * 10 ** b.decimals)); const cap = BigInt(b.raw || 0);
      const amt = atoms < cap ? atoms : cap; if (amt <= 0n) continue;
      out.push({ leg: { ...l, role: l.role }, target: { mint: l.mint, symbol: l.symbol }, why: `−$${diff.toFixed(2)} (over target)`,
        request: { input_mint: l.mint, output_mint: SOL_MINT, amount: atomsToUi(amt, b.decimals), slippage_bps: slippageBps, wallet } });
    } else {
      const sol = -diff / solUsd; if (sol < 0.001) continue;
      out.push({ leg: { ...l, role: l.role }, target: { mint: l.mint, symbol: l.symbol }, why: `+$${(-diff).toFixed(2)} (under target)`,
        request: { input_mint: SOL_MINT, output_mint: l.mint, amount: sol.toFixed(9).replace(/\.?0+$/, ''), slippage_bps: slippageBps, wallet } });
    }
  }
  return out.sort((a, b) => (a.request.input_mint === SOL_MINT) - (b.request.input_mint === SOL_MINT));   // sells first
}

// ＋ Top up a card with SOL: 'equal' = same SOL into every open coin · 'weight' = by each coin's share of the card now ·
// 'one' = all of it into the coin you pick. Buys only (one approval for all); they merge into the card like a switch-in.
export function topupOrders(legs, sol, mode, wallet, pick, slippageBps = 150) {
  const open = (legs || []).filter(l => l.soldUsd == null && l.mint);
  const amt = Number(sol) || 0;
  if (!open.length || amt < 0.001 || !wallet) return [];
  const val = l => Math.max(0, Number(l.heldUsd ?? l.valueUsd) || 0);
  const total = open.reduce((a, l) => a + val(l), 0);
  const share = l => (mode === 'one' ? (l.pairAddress === pick ? 1 : 0) : mode === 'weight' && total > 0 ? val(l) / total : 1 / open.length);
  return open.map(l => ({ l, s: amt * share(l) })).filter(x => x.s >= 0.0005).map(({ l, s }) => ({ leg: l, target: { mint: l.mint, symbol: l.symbol },
    request: { input_mint: SOL_MINT, output_mint: l.mint, amount: s.toFixed(9).replace(/\.?0+$/, ''), slippage_bps: slippageBps, wallet } }));
}
