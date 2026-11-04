// 🕯 CH01 (owner 2026-11-04: "no way we should be talking about fake candles"): a chart draws the source's candles exactly as sent. Only a row that cannot be drawn is dropped.
export function trueCandles(rows) {
  return rows.filter(r => [r[1], r[2], r[3], r[4]].every(v => Number.isFinite(v) && v > 0));
}
