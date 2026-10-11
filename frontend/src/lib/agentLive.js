// 👁 The Agents tab moves LIVE (owner, 2026-10-11: "all data needs to be realtime live moving $'s and %s"): the agents' payload is a pass
// snapshot (~60s); positions and seats are re-priced from the shared live-price poller (`useLivePrices`, 3s) against each position's own
// ENTRY — the snapshot taken at the buy. Server numbers stay where no live price has landed yet. Pure.
export function livePairs(d) {
  const o = d?.office || {};
  return [...new Set([...(o.positions || []).map(p => p.pair), ...((d?.card?.seats) || []).map(s => s.pair)].filter(Boolean))];
}

export function liveOverlay(d, prices) {
  if (!d || !prices || !prices.size) return d;
  const o = d.office || {};
  const byMint = {};
  const positions = (o.positions || []).map(p => {
    const lp = p.pair && prices.get(p.pair);
    const px = lp && lp.price > 0 ? lp.price : null;
    if (!px || !(p.entry > 0)) return p;
    const pct = Math.round((px / p.entry - 1) * 10000) / 100;
    const usd = p.px > 0 && p.usd != null ? Math.round(p.usd * (px / p.px) * 10000) / 10000 : p.usd;
    const q = { ...p, pct, usd, px, peak: Math.max(Number(p.peak) || pct, pct), liveAt: lp.at };
    if (p.mint) byMint[p.mint] = q;
    return q;
  });
  if (!Object.keys(byMint).length) return d;
  const seatOf = s => (s && s.mint && byMint[s.mint] ? { ...s, pct: byMint[s.mint].pct, live: true } : s);
  return {
    ...d,
    card: d.card ? { ...d.card, seats: (d.card.seats || []).map(seatOf) } : d.card,
    office: { ...o, positions, seatBoard: (o.seatBoard || []).map(seatOf) },
  };
}
