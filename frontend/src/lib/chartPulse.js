// 📊 CHART PULSE — what the candles ON SCREEN say right now (pure; candles = [time, open, high, low, close, volume]).
// It is read from the timeframe being watched, so it changes when the chart does: 1m = the last hour of candles, 15m = the last 15 hours.
// A read of the picture, never a forecast.
export const PULSE_N = 60;
const num = v => (Number.isFinite(Number(v)) ? Number(v) : null);

export function chartPulse(candles, n = PULSE_N) {
  const cs = (Array.isArray(candles) ? candles : []).filter(c => Array.isArray(c) && num(c[4]) > 0 && num(c[2]) > 0 && num(c[3]) > 0).slice(-n);
  if (cs.length < 8) return null;
  const hi = Math.max(...cs.map(c => c[2])); const lo = Math.min(...cs.map(c => c[3])); const last = cs[cs.length - 1][4];
  const pos = hi > lo ? Math.round(((last - lo) / (hi - lo)) * 100) : 50;
  const offHigh = hi > 0 ? Math.round((1 - last / hi) * 1000) / 10 : 0;
  const offLow = lo > 0 ? Math.round((last / lo - 1) * 1000) / 10 : 0;
  const tail = cs.slice(-10);
  const greens = tail.filter(c => c[4] >= c[1]).length;
  let streak = 0; const up = cs[cs.length - 1][4] >= cs[cs.length - 1][1];
  for (let i = cs.length - 1; i >= 0 && (cs[i][4] >= cs[i][1]) === up; i -= 1) streak += 1;
  const body = tail.reduce((a, c) => a + (c[2] > c[3] ? Math.abs(c[4] - c[1]) / (c[2] - c[3]) : 0), 0) / tail.length;
  const vol = c => num(c[5]) || 0; const avg = a => (a.length ? a.reduce((x, c) => x + vol(c), 0) / a.length : 0);
  const recent = avg(cs.slice(-5)); const before = avg(cs.slice(-20, -5));
  const volX = before > 0 && recent > 0 ? Math.round((recent / before) * 10) / 10 : null;
  const move = Math.round((last / cs[0][1] - 1) * 1000) / 10;
  const swing = lo > 0 ? Math.round((hi / lo - 1) * 1000) / 10 : 0;
  const p = { n: cs.length, pos, offHigh, offLow, greens, streak: up ? streak : -streak, conviction: Math.round(body * 100), volX, move, swing };
  return { ...p, call: pulseCall(p) };
}

// one call for the picture: [icon, word, tone]
export function pulseCall(p) {
  if (!p) return ['➖', 'NO CHART', 'warn'];
  if (p.offHigh >= 20 && p.streak <= -3) return ['🔪', 'SLIDING', 'bad'];
  if (p.pos >= 80 && p.greens >= 7) return p.volX != null && p.volX < 0.6 ? ['🪫', 'HIGHS ON FADING VOLUME', 'warn'] : ['🚀', 'PUSHING HIGHS', 'good'];
  if (p.pos <= 30 && p.streak >= 2 && p.offLow >= 3) return ['🧲', 'TURNING UP', 'good'];
  if (p.volX != null && p.volX >= 2 && p.greens >= 6) return ['🌊', 'VOLUME COMING IN', 'good'];
  if (p.pos <= 20 && p.greens <= 3) return ['🩸', 'AT THE LOWS', 'bad'];
  if (p.swing < 6) return ['😴', 'FLAT', 'warn'];
  return ['➖', 'RANGING', 'warn'];
}

// the chart's timeframe → the Jupiter window that fits it (1m candles ≈ the last 5 minutes of flow, 15m ≈ the last 6 hours)
export const TF_WINDOW = { '1m': '5m', '5m': '1h', '15m': '6h', '1h': '24h' };
