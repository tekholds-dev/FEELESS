// 📐 chart indicators (pure, `indicators.test.js`) — every one from the true candles {time, open, high, low, close, volume}; each returns
// [{time, value}] (Bollinger: {upper, mid, lower}) with points only where the window is full (never an invented early value).
export function ema(bars, n) {
  const out = []; const k = 2 / (n + 1); let e = null; let sum = 0;
  (bars || []).forEach((b, i) => { if (i < n) { sum += b.close; if (i === n - 1) { e = sum / n; out.push({ time: b.time, value: e }); } return; }
    e = b.close * k + e * (1 - k); out.push({ time: b.time, value: e }); });
  return out;
}
// VWAP over the loaded window: Σ(typical price × volume) / Σ volume
export function vwap(bars) {
  let pv = 0; let v = 0; const out = [];
  (bars || []).forEach(b => { const tp = (b.high + b.low + b.close) / 3; pv += tp * (b.volume || 0); v += b.volume || 0; if (v > 0) out.push({ time: b.time, value: pv / v }); });
  return out;
}
export function bollinger(bars, n = 20, k = 2) {
  const up = []; const mid = []; const lo = []; const c = (bars || []).map(b => b.close);
  for (let i = n - 1; i < c.length; i += 1) {
    const w = c.slice(i - n + 1, i + 1); const m = w.reduce((a, x) => a + x, 0) / n; const sd = Math.sqrt(w.reduce((a, x) => a + (x - m) ** 2, 0) / n); const t = bars[i].time;
    up.push({ time: t, value: m + k * sd }); mid.push({ time: t, value: m }); lo.push({ time: t, value: m - k * sd });
  }
  return { upper: up, mid, lower: lo };
}
// Wilder's RSI
export function rsi(bars, n = 14) {
  const c = (bars || []).map(b => b.close); const out = []; if (c.length <= n) return out;
  let g = 0; let l = 0;
  for (let i = 1; i <= n; i += 1) { const d = c[i] - c[i - 1]; if (d > 0) g += d; else l -= d; }
  g /= n; l /= n; out.push({ time: bars[n].time, value: l === 0 ? 100 : 100 - 100 / (1 + g / l) });
  for (let i = n + 1; i < c.length; i += 1) { const d = c[i] - c[i - 1]; g = (g * (n - 1) + Math.max(0, d)) / n; l = (l * (n - 1) + Math.max(0, -d)) / n;
    out.push({ time: bars[i].time, value: l === 0 ? 100 : 100 - 100 / (1 + g / l) }); }
  return out;
}
export const INDICATORS = [['ema', 'EMA 9/21', 'Exponential moving averages: 9 (fast) over 21 (slow) = momentum up'], ['vwap', 'VWAP', 'Volume-weighted average price of the loaded window — above it buyers are in control'],
  ['bb', 'BB 20·2', 'Bollinger Bands: 20-candle mean ± 2 standard deviations — a squeeze before a move, tags on the extremes'], ['rsi', 'RSI 14', 'Relative strength (Wilder, 14): over 70 stretched up, under 30 stretched down']];
