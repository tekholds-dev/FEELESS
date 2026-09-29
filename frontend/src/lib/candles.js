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

// Per-pair candle cache so timeframe switches paint instantly; all timeframes are
// prefetched in parallel the moment a pair opens.
const INTERVALS = ['1m', '5m', '15m', '1h', '4h', '1d'];
const cache = new Map();
const key = (chain, pair, interval) => `${chain}:${pair}:${interval}`;
export const getCachedCandles = (chain, pair, interval) => cache.get(key(chain, pair, interval)) || null;
export function cacheCandles(chain, pair, interval, res) {
  if (Array.isArray(res?.candles) && res.candles.length) cache.set(key(chain, pair, interval), res);
}
export function prefetchAllIntervals(chain, pair, mint) {
  INTERVALS.forEach(iv => {
    if (cache.has(key(chain, pair, iv))) return;
    fetchFeelessCandles(chain, pair, iv, undefined, mint).then(res => cacheCandles(chain, pair, iv, res)).catch(() => {});
  });
}
