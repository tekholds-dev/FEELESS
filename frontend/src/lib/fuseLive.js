// Live card math from the shared 10s price poller (lib/livePrices) — every % and $ on Fuse cards moves in real time.
// All pure; each falls back to the server's number when the poller has no price for a leg.

// A trader's card: what's still held × live price + what was already taken out, vs what went in.
export function liveRowValue(r, live) {
  let value = 0;
  for (const l of r.legs || []) {
    if (l.soldUsd != null) { value += Number(l.soldUsd) || 0; continue; }
    const px = live?.get(l.pairAddress)?.price;
    const held = px && Number(l.tokens) > 0 ? Number(l.tokens) * px : Number(l.heldUsd ?? l.valueUsd ?? l.usd) || 0;
    value += held + (Number(l.realizedUsd) || 0);
  }
  return value;
}

export function liveRowPnl(r, live) {
  const cost = Number(r.costUsd) || (r.legs || []).reduce((a, l) => a + (Number(l.usd) || 0), 0);
  const value = liveRowValue(r, live);
  return { cost, value, pnlUsd: value - cost, pnlPct: cost > 0 ? (value / cost - 1) * 100 : 0 };
}

// Totals across many cards (My cards header, profile).
export function liveBook(rows, live) {
  const t = rows.reduce((a, r) => { const p = liveRowPnl(r, live); return { cost: a.cost + p.cost, value: a.value + p.value }; }, { cost: 0, value: 0 });
  return { ...t, pnlUsd: t.value - t.cost, pnlPct: t.cost > 0 ? (t.value / t.cost - 1) * 100 : 0 };
}

// Arena stage card: user = real P&L · lit/round = average move since each coin's entry · mega = weighted index vs base.
export function liveStagePct(c, live) {
  const px = l => live?.get(l.pairAddress)?.price || 0;
  if (c.kind === 'user') return c.costUsd ? liveRowPnl(c, live).pnlPct : null;
  if (c.kind === 'mega') {
    const legs = (c.legs || []).filter(l => l.base > 0 && px(l) > 0); const w = legs.reduce((a, l) => a + (Number(l.weight) || 0), 0);
    return legs.length && w ? (legs.reduce((a, l) => a + (Number(l.weight) || 0) * (px(l) / l.base), 0) / w - 1) * 100 : null;
  }
  const legs = (c.legs || []).filter(l => l.entry > 0 && px(l) > 0);
  return legs.length ? (legs.reduce((a, l) => a + px(l) / l.entry, 0) / legs.length - 1) * 100 : null;
}
