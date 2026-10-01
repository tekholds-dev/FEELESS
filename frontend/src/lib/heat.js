// Pump radar 🔥 Heat: one score from what's actually happening right now (no extra requests).
//  buy pressure (5m buy share) · momentum (5m + 1h move, capped) · volume pace (5m vs the hour's average)
//  · calls in chat · snipers out (cleanest charts) · thin pools (<$5K liquidity) sink.
export function heatScore(pair, { calls = 0, snipersOut = false } = {}) {
  const tx = pair?.txns?.m5 || {}; const buys = Number(tx.buys) || 0; const sells = Number(tx.sells) || 0;
  const share = buys + sells ? buys / (buys + sells) : 0.5;
  const m5 = Number(pair?.priceChange?.m5) || 0; const h1 = Number(pair?.priceChange?.h1) || 0;
  const v5 = Number(pair?.volume?.m5) || 0; const vh = Number(pair?.volume?.h1) || 0;
  const pace = vh > 0 ? Math.min(4, (v5 * 12) / vh) : 0;
  const liq = Number(pair?.liquidity?.usd) || 0;
  let s = (share - 0.5) * 60 + Math.max(-20, Math.min(30, m5 * 2)) + Math.max(-15, Math.min(20, h1 / 2)) + pace * 8 + Math.min(5, calls) * 4 + (snipersOut ? 15 : 0);
  if (buys + sells < 5) s -= 10;
  if (liq < 5000) s -= 25;
  return Math.round(s);
}
