// When the screener has no score, describe the coin from its own live stats (never invented).
export function observedReasons(pair) {
  const out = [];
  const t = pair.txns?.h1 || {}; const b = Number(t.buys) || 0; const sl = Number(t.sells) || 0;
  if (b + sl >= 20) out.push(`${Math.round((b / (b + sl)) * 100)}% buys 1h`);
  const h1 = Number(pair.priceChange?.h1);
  if (Number.isFinite(h1) && pair.priceChange?.h1 != null) out.push(`${h1 >= 0 ? '+' : ''}${h1.toFixed(1)}% 1h`);
  const liq = Number(pair.liquidity?.usd); const vol = Number(pair.volume?.h24);
  if (liq > 0 && vol > 0) out.push(`${(vol / liq).toFixed(1)}× vol/liq`);
  return out;
}
export function observedLabel(pair) {
  const t = pair.txns?.h1 || {}; const b = Number(t.buys) || 0; const sl = Number(t.sells) || 0;
  const h1 = Number(pair.priceChange?.h1); const age = Date.now() - Number(pair.pairCreatedAt);
  if (Number.isFinite(age) && age > 0 && age < 6 * 3600e3) return 'Fresh pool';
  if (h1 >= 10 && b > sl) return 'Heating up';
  if (h1 <= -10) return 'Cooling off';
  if (b + sl >= 20 && b / (b + sl) >= 0.6) return 'Buy pressure';
  if (b + sl >= 20 && b / (b + sl) <= 0.4) return 'Sell pressure';
  const liq = Number(pair.liquidity?.usd); const vol = Number(pair.volume?.h24);
  if (liq > 0 && vol / liq >= 50) return 'High churn';
  if (b + sl > 0 || vol > 0) return 'Steady';
  return null;
}

