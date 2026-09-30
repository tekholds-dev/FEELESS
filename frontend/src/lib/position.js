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
  return { ...pos, tokensHeld: Math.max(0, held - tokens), costUsd: avg * Math.max(0, held - tokens), realizedUsd: (pos.realizedUsd || 0) + pnl, sells: (pos.sells || 0) + 1,
    lastTradeAt: trade.ts, trades: [...(pos.trades || []), { ...trade, pnlUsd: pnl }], pending: true };
}
