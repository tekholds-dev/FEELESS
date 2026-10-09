// 📐 LEAN (owner, 2026-10-09: "a line for where it's going based on momentum, activity, vitals"): −1 … +1 from the 5-min move, the hour,
// who is buying, the 5-min pace vs the hour and heat − rug. A READ of what the numbers lean toward right now, never a forecast.
// Used by the Rush board (`LeanLine`) and every Fuse card's coin rows (`LegFlow`).
const clamp1 = v => Math.max(-1, Math.min(1, v));
export const leanOf = r => { const c5 = Number(r?.chg5m) || 0, c1 = Number(r?.chg1h) || 0, b = r?.buyShare != null ? Number(r.buyShare) - 50 : 0;
  const v1 = Number(r?.vol1h) || 0, pace = v1 > 0 ? (Number(r?.vol5m) || 0) * 12 / v1 : 1; const hr = ((Number(r?.tv?.heat) || 0) - (Number(r?.rug ?? r?.tv?.rug) || 0)) / 100;
  return Math.round(clamp1(clamp1(c5 / 15) * 0.35 + clamp1(c1 / 60) * 0.2 + clamp1(b / 20) * 0.25 + clamp1((pace - 1) * (c5 >= 0 ? 1 : -1)) * 0.1 + clamp1(hr) * 0.1) * 100) / 100; };
