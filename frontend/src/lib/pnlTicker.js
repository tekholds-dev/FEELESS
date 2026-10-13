// 💹 THE USER'S LIVE P&L TICKER (every coin chart, users' trading — never the Agents tab): each REAL live-price tick is classified by
// how far it moved, which drives the badge's effect level; the numbers themselves glide to the real value at ≤ 30fps (`useEasedNumber`).
// Pure — no request of its own (the badge's existing 2.5s live price is the only input).
export const HEAT_STEPS = [0.2, 1, 3];   // % moved on one tick → heat 1 · 2 · 3 (0 = calm)
export function tickHeat(prev, next) {
  const a = Number(prev); const b = Number(next);
  if (!(a > 0) || !(b > 0) || a === b) return { heat: 0, dir: 0, pct: 0 };
  const pct = ((b - a) / a) * 100; const m = Math.abs(pct);
  return { heat: m >= HEAT_STEPS[2] ? 3 : m >= HEAT_STEPS[1] ? 2 : m >= HEAT_STEPS[0] ? 1 : 0, dir: pct > 0 ? 1 : -1, pct };
}
