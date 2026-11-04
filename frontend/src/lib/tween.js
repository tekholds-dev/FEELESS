// 🎞 ease-out cubic from the drawn close to the new REAL close; k ≥ 1 is exactly the tick (never past it, never a made-up price)
export function tweenClose(from, to, k) {
  if (!(k > 0)) return from;
  if (k >= 1 || !Number.isFinite(from)) return to;
  return from + (to - from) * (1 - Math.pow(1 - k, 3));
}


// 🕯 A history reload (every 15–60s) must never overwrite the forming candle the LIVE feed built: same bucket → keep the loaded open, widen
// high / low to the live ones, close = the live close (it is newer); a newer live bucket is appended. Pure; returns the bars to draw.
export function mergeLiveBar(bars, lb, interval, pool) {
  const out = [...(bars || [])];
  if (!lb || lb.iv !== interval || lb.pool !== pool || !out.length) return out;
  const last = out[out.length - 1];
  if (lb.time === last.time) out[out.length - 1] = { ...last, high: Math.max(last.high, lb.high), low: Math.min(last.low, lb.low), close: lb.close };
  else if (lb.time > last.time) out.push({ time: lb.time, open: lb.open, high: lb.high, low: lb.low, close: lb.close });
  return out;
}


// 🕯 THE FORMING CANDLE (CH01): a live price shapes this minute's candle. A new minute's candle starts at the first new price, never as a flat bar at the old close, and a quiet minute draws nothing. → the bar, or null.
export function liveBar(last, value, t) {
  if (!last || !(value > 0)) return null;
  if (t <= last.time) return { ...last, high: Math.max(last.high, value), low: Math.min(last.low, value), close: value };
  if (value === last.close) return null;
  return { time: t, open: value, high: value, low: value, close: value };
}
