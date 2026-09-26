import { useEffect, useMemo, useState } from 'react';

const cache = new Map();
const TTL = 20000;

// Live DexScreener market state per token mint, batched 30 per request.
// Used to fill cards whose upstream feed (e.g. pump.fun's coin index) carries no price.
export function useLiveTokenMarkets(chain, mints) {
  const key = useMemo(() => [...new Set(mints.filter(Boolean))].sort().join(','), [mints]);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    if (!key || !chain) return undefined;
    let alive = true;
    const load = async () => {
      const list = key.split(',');
      const stale = list.filter(m => !cache.has(m) || Date.now() - cache.get(m).at > TTL);
      for (let i = 0; i < stale.length; i += 30) {
        try {
          const res = await fetch(`https://api.dexscreener.com/tokens/v1/${chain}/${stale.slice(i, i + 30).join(',')}`);
          const pairs = res.ok ? await res.json() : [];
          const best = {};
          (Array.isArray(pairs) ? pairs : []).forEach(p => {
            const m = p?.baseToken?.address;
            if (!m) return;
            if (!best[m] || (Number(p.liquidity?.usd) || 0) > (Number(best[m].liquidity?.usd) || 0)) best[m] = p;
          });
          stale.slice(i, i + 30).forEach(m => cache.set(m, { at: Date.now(), pair: best[m] || null }));
        } catch {
          // Keep last known values; never invent a price.
        }
      }
      if (alive) setTick(t => t + 1);
    };
    load();
    const timer = setInterval(() => { if (!document.hidden) load(); }, TTL);
    return () => { alive = false; clearInterval(timer); };
  }, [chain, key]);
  return useMemo(() => {
    const out = new Map();
    key.split(',').forEach(m => { const hit = cache.get(m); if (hit?.pair) out.set(m, hit.pair); });
    return out;
  }, [key, tick]); // eslint-disable-line react-hooks/exhaustive-deps
}

export function withLiveMarket(pair, live) {
  const p = live?.get(pair?.baseToken?.address);
  if (!p) return pair;
  return {
    ...pair,
    priceUsd: p.priceUsd ?? pair.priceUsd,
    priceNative: p.priceNative ?? pair.priceNative,
    priceChange: { ...(pair.priceChange || {}), ...(p.priceChange || {}) },
    liquidity: p.liquidity?.usd != null ? p.liquidity : pair.liquidity,
    volume: p.volume || pair.volume,
    txns: p.txns || pair.txns,
    marketCap: p.marketCap ?? pair.marketCap,
    fdv: p.fdv ?? pair.fdv,
    liveSource: 'DexScreener',
  };
}
