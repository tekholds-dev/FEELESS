// Snap chart pins (your trades, calls) onto a point the series really has, so none are silently hidden.
export function snapMarkers(markers, times, bucket) {
  const valid = (markers || []).filter(m => Number.isFinite(m.time));
  if (!times.length) return valid.map(m => ({ ...m, time: Math.floor(m.time / bucket) * bucket })).sort((x, y) => x.time - y.time);
  const out = [];
  valid.forEach(m => {
    if (m.time < times[0] - bucket) return;
    let lo = 0; let hi = times.length - 1;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (times[mid] <= m.time) lo = mid; else hi = mid - 1; }
    out.push({ ...m, time: times[lo] });
  });
  return out.sort((x, y) => x.time - y.time);
}

// One level per trade at the exact pool price it filled at: B1, B2… for buys, S1… for sells (last 6 shown).
export function tradeLevels(trades, max = 6) {
  let b = 0; let s = 0;
  return (trades || []).filter(t => Number(t.fillPrice) > 0).map(t => {
    const sell = t.side === 'sell'; const n = sell ? `S${++s}` : `B${++b}`;
    return { side: sell ? 'sell' : 'buy', price: Number(t.fillPrice), title: `${n} ${sell ? 'sold' : 'bought'} $${Number(t.usd || 0).toFixed(t.usd >= 100 ? 0 : 2)}` };
  }).slice(-max);
}
