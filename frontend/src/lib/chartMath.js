// Drop bars that can't be real (e.g. a quote-token price recorded as the coin's) and clamp
// runaway wicks, so one bad print never flattens the whole chart.
export function scrubCandles(rows) {
  if (rows.length < 2) return rows;
  const closes = rows.map(r => r[4]);
  const med = (i) => { const w = closes.slice(Math.max(0, i - 3), i).concat(closes.slice(i + 1, i + 4)).filter(v => v > 0).sort((x, y) => x - y); return w.length ? w[Math.floor(w.length / 2)] : closes[i]; };
  const out = [];
  rows.forEach((r, i) => {
    const [t, o, h, l, c, v] = r;
    const m = med(i);
    // A bar 4x away from its neighbours is a bad print (wrong pool / quote), not a move.
    // Never drop it (that skips a candle): redraw it flat at the previous close instead.
    if (!(c > 0) || c > m * 4 || c < m / 4) {
      const prev = out.length ? out[out.length - 1][4] : m;
      if (prev > 0) out.push([t, prev, prev, prev, prev, v]);
      return;
    }
    // Continuous market: every candle opens where the last one closed, so bars connect and never "jump" or float as
    // detached dashes (sparse provider points used to draw as one-price bars at random heights).
    const prevClose = out.length ? out[out.length - 1][4] : null;
    const open = prevClose > 0 && prevClose < c * 4 && prevClose > c / 4 ? prevClose : o > 0 && o < c * 4 && o > c / 4 ? o : c;
    const top = Math.max(open, c), bot = Math.min(open, c);
    out.push([t, open, Math.max(top, Math.min(h, top * 3)), Math.min(bot, Math.max(l, bot / 3) || bot), c, v]);
  });
  return out.length >= 2 ? out : rows;
}
