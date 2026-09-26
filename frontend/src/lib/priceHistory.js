// A small, permanent, per-pair price trail recorded locally whenever this browser
// observes a live priceUsd for a pair. When the candle provider (GeckoTerminal) fails,
// this is real — not invented — data to fall back to instead of an error banner: every
// point here was an actual price this app saw, just lower-resolution than real OHLCV.
const KEY_PREFIX = 'feeless-price-trail:';
const MAX_POINTS = 240;
const MAX_AGE_MS = 3 * 24 * 60 * 60 * 1000;

function storageKey(pairAddress) {
  return `${KEY_PREFIX}${pairAddress}`;
}

export function recordPricePoint(pairAddress, priceUsd) {
  if (!pairAddress || priceUsd == null || !Number.isFinite(Number(priceUsd)) || typeof window === 'undefined') return;
  try {
    const key = storageKey(pairAddress);
    const now = Date.now();
    const existing = JSON.parse(localStorage.getItem(key) || '[]');
    const last = existing[existing.length - 1];
    if (last && now - last.t < 20000) return; // don't spam points faster than ~20s apart
    const next = [...existing, { t: now, p: Number(priceUsd) }]
      .filter(point => now - point.t <= MAX_AGE_MS)
      .slice(-MAX_POINTS);
    localStorage.setItem(key, JSON.stringify(next));
  } catch {
    // Storage full or unavailable — the live app still works, it just won't have a fallback trail.
  }
}

export function getPriceTrail(pairAddress) {
  if (!pairAddress || typeof window === 'undefined') return [];
  try {
    return JSON.parse(localStorage.getItem(storageKey(pairAddress)) || '[]');
  } catch {
    return [];
  }
}
