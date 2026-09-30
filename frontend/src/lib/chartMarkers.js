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
