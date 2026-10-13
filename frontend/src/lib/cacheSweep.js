// 🧹 AUTO CACHE CLEAN (owner, 2026-10-13: "finish site wide lag … cache clean auto"): two dozen module-level caches were keyed by coin,
// wallet or URL and NEVER evicted — a tab left open for days (the owner's had been up six) kept every candle history, price, profile and
// answer it ever saw, so memory and GC pauses only grew. Every such cache registers here; ONE sweep a minute (and when the tab is
// hidden) drops entries past their age and trims each cache to its size, oldest first. Entries something on screen still uses
// (`keep`) are never dropped. Dropping a cached answer only costs the next reader one request.
const regs = [];
let timer = null;

export function sweepable(name, map, { ttl = 0, max = 300, at = v => v?.at, keep = null } = {}) {
  regs.push({ name, map, ttl, max, at, keep });
  if (!timer && typeof window !== 'undefined' && process.env.NODE_ENV !== 'test') {
    timer = setInterval(sweepNow, 60000);
    document.addEventListener('visibilitychange', () => { if (document.hidden) sweepNow(); });
  }
  return map;
}

export function sweepNow(now = Date.now()) {
  let dropped = 0;
  for (const r of regs) {
    const t0 = typeof now === 'number' ? now : Date.now();
    if (r.ttl > 0) for (const [k, v] of r.map) {
      const t = Number(r.at(v));
      if (t > 0 && t0 - t > r.ttl && !(r.keep && r.keep(k))) { r.map.delete(k); dropped += 1; }
    }
    if (r.map.size > r.max) for (const k of [...r.map.keys()]) {   // a Map keeps insertion order: the first keys are the oldest
      if (r.map.size <= r.max) break;
      if (r.keep && r.keep(k)) continue;
      r.map.delete(k); dropped += 1;
    }
  }
  return dropped;
}

export const cacheSizes = () => Object.fromEntries(regs.map(r => [r.name, r.map.size]));   // for a look from the console / tests
