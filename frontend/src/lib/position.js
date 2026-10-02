// Instant position: fold a just-confirmed trade into the current position before the server re-reads the chain,
// so the entry line, P&L and pins move the moment your wallet's trade confirms. The server's exact numbers replace it seconds later.
export function applyFill(pos, f) {
  const tokens = Number(f?.tokens) || 0; const usd = Number(f?.usd) || 0;
  if (!(tokens > 0) || !(usd > 0) || !f?.signature) return pos;
  if ((pos?.trades || []).some(t => t.tx === f.signature)) return pos;
  const trade = { ts: Date.now() / 1000, side: f.side === 'sell' ? 'sell' : 'buy', usd, price: usd / tokens, tokens, tx: f.signature, via: 'pending' };
  if (!pos) return trade.side === 'buy' ? { avgEntry: trade.price, tokensHeld: tokens, costUsd: usd, realizedUsd: 0, investedUsd: usd, feesUsd: 0, buys: 1, sells: 0, lastTradeAt: trade.ts, trades: [trade], pending: true } : pos;
  const held = Number(pos.tokensHeld) || 0; const avg = Number(pos.avgEntry) || trade.price;
  if (trade.side === 'buy') {
    const nextHeld = held + tokens; const nextAvg = (avg * held + usd) / nextHeld;
    return { ...pos, avgEntry: nextAvg, tokensHeld: nextHeld, costUsd: nextAvg * nextHeld, investedUsd: (pos.investedUsd || 0) + usd, buys: (pos.buys || 0) + 1, lastTradeAt: trade.ts, trades: [...(pos.trades || []), trade], pending: true };
  }
  const pnl = usd - tokens * avg;
  return { ...pos, tokensHeld: Math.max(0, held - tokens), costUsd: avg * Math.max(0, held - tokens), realizedUsd: (pos.realizedUsd || 0) + pnl, soldUsd: (pos.soldUsd || 0) + usd, sells: (pos.sells || 0) + 1,
    lastTradeAt: trade.ts, trades: [...(pos.trades || []), { ...trade, pnlUsd: pnl }], pending: true };
}

// The position panel the big terminals show: Bought / Sold / Holding / total P&L. Total P&L = realized on sells +
// unrealized on what you still hold, against the POOL-side cost (fees out — they're on the receipt, never in P&L).
export function pnlSummary(pos, live) {
  // Entry = where your trade actually filled (after fees, once your wallet confirmed). Fees are paid in the background,
  // so P&L starts at $0 on the entry and moves with the live price — no break-even line.
  const held = Number(pos?.tokensHeld) || 0; const px = Number(live) || 0;
  const entry = Number(pos?.fillPrice) || Number(pos?.avgEntry) || 0;
  const value = px * held;
  // 🔒 fees never in P&L: pool-side money (what reached the pool) when the server has it; else the fee-free entry × coins
  const bought = Number(pos?.investedPoolUsd) || Number(pos?.investedUsd) || entry * held;
  const sold = Number(pos?.soldUsd) || 0;
  const unrealized = (px - entry) * held;
  const realized = pos?.realizedPoolUsd != null ? Number(pos.realizedPoolUsd) : Number(pos?.realizedUsd) || 0;
  const pnl = realized + unrealized;
  // % = total P&L on the money you put in (same sign as the $ P&L, also after partial sells).
  const pct = bought > 0 ? (pnl / bought) * 100 : 0;
  return { entry, value, bought, sold, unrealized, realized, pnl, pct };
}
