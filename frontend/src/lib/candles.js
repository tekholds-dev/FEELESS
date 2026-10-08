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

// One request per (pair, timeframe) in flight: the chart's own load, the all-timeframes prefetch and a hover warm-up share it
// (they used to fire the same timeframe twice + five more at once on every open → each waited on the others).
const inflight = new Map();
export function fetchFeelessCandles(chain, pairAddress, interval, before, mint) {
  // `mint` lets the server chart pools it can't identify yet (it verifies the mint on-chain first).
  const k = before ? null : `${chain}:${pairAddress}:${interval}`;
  if (k && inflight.has(k)) return inflight.get(k);
  const p = fetch(apiUrl(`/api/candles/${chain}/${pairAddress}?interval=${interval}${before ? `&before=${before}` : ''}${mint ? `&mint=${mint}` : ''}`))
    .then(res => { if (!res.ok) throw new Error('FEELESS candle service unavailable.'); return res.json(); })
    .finally(() => { if (k) inflight.delete(k); });
  if (k) inflight.set(k, p);
  return p;
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
// ONE timeframe, for a hover warm-up: hovering down a list used to start all six timeframes for every row passed over
// (dozens of coins × 6 builds × 3 providers) and stalled the chart service for the coin actually opened.
export function prefetchInterval(chain, pair, mint, iv = '1m') {
  if (!pair || cache.has(key(chain, pair, iv))) return;
  fetchFeelessCandles(chain, pair, iv, undefined, mint).then(res => cacheCandles(chain, pair, iv, res)).catch(() => {});
}
export function prefetchAllIntervals(chain, pair, mint) {
  INTERVALS.forEach(iv => {
    if (cache.has(key(chain, pair, iv))) return;
    fetchFeelessCandles(chain, pair, iv, undefined, mint).then(res => cacheCandles(chain, pair, iv, res)).catch(() => {});
  });
}
