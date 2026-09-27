import { apiUrl } from './api';

// Fire-and-forget: records a real observed price tick server-side so the
// FEELESS candle aggregator keeps building real OHLCV history for this pair,
// shared across every session, not just this browser.
export function recordCandleTick(chain, pairAddress, priceUsd, volumeUsd) {
  if (!chain || !pairAddress || priceUsd == null || !Number.isFinite(Number(priceUsd))) return;
  try {
    fetch(apiUrl('/api/candles/observe'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chain, pairAddress, priceUsd: Number(priceUsd), volumeUsd: volumeUsd != null ? Number(volumeUsd) : null }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    // Never let a tick-recording failure affect the chart the user is looking at.
  }
}

export async function fetchFeelessCandles(chain, pairAddress, interval, before, mint) {
  // `mint` lets the server chart pools it can't identify yet (it verifies the mint on-chain first).
  const res = await fetch(apiUrl(`/api/candles/${chain}/${pairAddress}?interval=${interval}${before ? `&before=${before}` : ''}${mint ? `&mint=${mint}` : ''}`));
  if (!res.ok) throw new Error('FEELESS candle service unavailable.');
  return res.json();
}
