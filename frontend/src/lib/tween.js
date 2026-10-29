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


// 🕯 TRUE DATA AT THE LIVE EDGE (owner, 2026-10-12: "one candle can't be glitching — only true market data"): a new live bucket opens at the
// previous close only when the history is CURRENT (≤ STALE_BUCKETS behind) — that is a real continuation. When the history ended minutes ago
// (a coin the provider indexed late), opening at that stale close drew ONE fake candle from the old price to the live one (entry → 2× on
// $STREAM) and the old flat filler invented minutes of trades. Then the gap stays a gap and the candle opens at the FIRST REAL TICK.
export const STALE_BUCKETS = 2;
export function liveBar(last, value, t, bucket) {
  if (!last || !(value > 0)) return { fill: [], bar: null };
  if (t <= last.time) return { fill: [], bar: { ...last, high: Math.max(last.high, value), low: Math.min(last.low, value), close: value } };
  const behind = Math.round((t - last.time) / bucket);
  if (behind > STALE_BUCKETS) return { fill: [], bar: { time: t, open: value, high: value, low: value, close: value } };
  const fill = [];
  for (let gt = last.time + bucket; gt < t; gt += bucket) fill.push({ time: gt, open: last.close, high: last.close, low: last.close, close: last.close });
  return { fill, bar: { time: t, open: last.close, high: Math.max(last.close, value), low: Math.min(last.close, value), close: value } };
}

// 🕯 THE CANDLE CLOCK (owner 2026-10-29: "chart still has issues with new candles, not updating true realtime"): a new candle used to appear only
// when the first trade of the new minute landed — a quiet second at the boundary left the old candle on screen past its time. At each bucket
// boundary the new candle opens ON TIME at the previous close (exactly the flat bar `liveBar` would fill in later — every bucket exists, every
// candle opens at the previous close), and the next real tick shapes it. Pure: null when there is nothing to roll (same bucket, or a stale history
// the first real tick must open instead).
export function rollBar(last, t, bucket) {
  if (!last || !(t > last.time)) return null;
  const close = last.close ?? last.value;
  if (!(close > 0) || Math.round((t - last.time) / bucket) > STALE_BUCKETS) return null;
  if (last.close == null) return { fill: [], bar: { time: t, value: close } };   // a line series: the point carries on
  return liveBar(last, close, t, bucket);
}
export const msToNextBucket = (bucket, now = Date.now()) => Math.max(20, Math.ceil(now / 1000 / bucket) * bucket * 1000 - now + 20);
