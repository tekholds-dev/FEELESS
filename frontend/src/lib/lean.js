// 📐 LEAN (owner, 2026-10-09: "a line for where it's going based on momentum, activity, vitals"): −1 … +1 from the 5-min move, the hour,
// who is buying, the 5-min pace vs the hour and heat − rug. A READ of what the numbers lean toward right now, never a forecast.
// Used by the Rush board (`LeanLine`) and every Fuse card's coin rows (`LegFlow`).
const clamp1 = v => Math.max(-1, Math.min(1, v));
export const leanOf = r => { const c5 = Number(r?.chg5m) || 0, c1 = Number(r?.chg1h) || 0, b = r?.buyShare != null ? Number(r.buyShare) - 50 : 0;
  const v1 = Number(r?.vol1h) || 0, pace = v1 > 0 ? (Number(r?.vol5m) || 0) * 12 / v1 : 1; const hr = ((Number(r?.tv?.heat) || 0) - (Number(r?.rug ?? r?.tv?.rug) || 0)) / 100;
  return Math.round(clamp1(clamp1(c5 / 15) * 0.35 + clamp1(c1 / 60) * 0.2 + clamp1(b / 20) * 0.25 + clamp1((pace - 1) * (c5 >= 0 ? 1 : -1)) * 0.1 + clamp1(hr) * 0.1) * 100) / 100; };

// ⚡ RUSH (mirrors `arena_prime.rush_score` for the engine — change both; the engine also needs the scan to have PASSED): the trench coins
// most worth a small ticket right now. A failed scan, a busted / wash / blow-off read, rug ≥ 50 or a > +15% 5-min candle never rushes.
const RUSH_MIN_LIQ = 20000;   /* a pool thinner than this is pullable ($Emotional: $14K, pulled 4 min after the buy) */
const RUSH_BAD = new Set(['RUG BAIT', 'DUMPING', 'BOND RUN', 'EARLY RUSH', 'SLOW CURVE', 'BREAKOUT', 'FALLING KNIFE', 'WASH TRADED', 'BLOW-OFF TOP', 'DEAD DIP', 'TREND DOWN']);
export const rushScore = r => { if (!r || r.safe === false || RUSH_BAD.has(r.tv?.call?.[1]) || Number(r.rug ?? r.tv?.rug) >= 50 || Number(r.chg5m) > 15 || Number(r.chg5m) < -5 || (Number(r.liq) > 0 && Number(r.liq) < RUSH_MIN_LIQ)) return null;   /* > +15% in one 5-min candle = a buying top · < −5% = falling now */
  const c5 = Number(r.chg5m) || 0; const buys = Number(r.buyShare) || 0;
  return (r.safe === true ? 20 : 0) + (r.brain ? Number(r.brain.est) || 0 : 0) + (Number(r.tv?.heat) || 0) * 0.3 - (Number(r.rug ?? r.tv?.rug) || 0) * 0.4
    + (c5 > 0 && buys >= 55 ? c5 : 0) + (r.site && r.x ? 5 : 0); };
export const rushTop = (rows, n = 3) => (rows || []).map(r => [rushScore(r), r]).filter(([v]) => v != null).sort((a, b) => b[0] - a[0]).slice(0, n).map(([v, r]) => ({ ...r, rush: Math.round(v) }));
