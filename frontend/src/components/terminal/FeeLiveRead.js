// Fee's live chart read — rules only, computed from the real candles and pair stats on screen.
// Returns levels to draw and a plain-English read. Nothing here is invented or predicted.
export function computeFeeRead(candles, pair, position) {
  const rows = (candles || []).slice(-40);
  if (rows.length < 5) return null;
  const last = rows[rows.length - 1];
  const price = Number(last[4]);
  const lows = rows.map(r => r[3]); const highs = rows.map(r => r[2]);
  const support = Math.min(...lows); const resistance = Math.max(...highs);
  const volSum = rows.reduce((s, r) => s + (Number(r[5]) || 0), 0);
  const vwap = volSum > 0 ? rows.reduce((s, r) => s + ((r[2] + r[3] + r[4]) / 3) * (Number(r[5]) || 0), 0) / volSum : null;
  const liq = Number(pair?.liquidity?.usd) || 0;
  const mc = Number(pair?.marketCap || pair?.fdv) || 0;
  const liqRatio = mc ? liq / mc : null;
  const t5 = pair?.txns?.m5 || {}; const t1 = pair?.txns?.h1 || {};
  const b5 = Number(t5.buys) || 0; const s5 = Number(t5.sells) || 0; const b1 = Number(t1.buys) || 0; const s1 = Number(t1.sells) || 0;
  const flow1 = b1 + s1 ? b1 / (b1 + s1) : null;
  const toSup = price ? ((price - support) / price) * 100 : 0;
  const toRes = price ? ((resistance - price) / price) * 100 : 0;
  const lines = [];
  lines.push(vwap ? (price >= vwap ? `Holding above fair value (VWAP) — buyers in control of this range.` : `Trading under fair value (VWAP) — sellers still leaning on it.`) : 'No volume data to weigh fair value.');
  lines.push(`Range: support ${toSup.toFixed(1)}% below, resistance ${toRes.toFixed(1)}% above.`);
  if (flow1 != null) lines.push(`Order flow 1h: ${Math.round(flow1 * 100)}% buys (${b1}/${s1})${b5 + s5 ? `, last 5m ${b5}/${s5}` : ''}.`);
  if (liqRatio != null) lines.push(liqRatio < 0.05 ? `⚠️ Liquidity is thin — ${(liqRatio * 100).toFixed(1)}% of MC. Big sells will move it hard.` : liqRatio > 0.25 ? `💧 Deep liquidity (${(liqRatio * 100).toFixed(0)}% of MC) — cleaner fills.` : `💧 Liquidity ${(liqRatio * 100).toFixed(0)}% of MC — normal for its size.`);
  let stance = 'watching';
  if (position) stance = 'in position';
  else if (vwap && price > vwap && flow1 != null && flow1 > 0.55 && toRes > 3) stance = 'leaning long';
  else if (vwap && price < vwap && flow1 != null && flow1 < 0.45) stance = 'staying out';
  if (position) {
    const entry = Number(position.entryPriceUsd);
    if (entry) lines.unshift(`I'm in from $${entry.toPrecision(4)} — ${(((price - entry) / entry) * 100).toFixed(1)}% now. Stop −10%, target +22%.`);
  }
  return { price, support, resistance, vwap, liq, liqRatio, flow1, stance, lines, entry: position ? Number(position.entryPriceUsd) || null : null };
}
