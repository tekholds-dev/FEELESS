/*
Centralized market data access with in-memory caching and deduplication.
All DexScreener calls go through here so components don't independently
hammer the API. Cache TTL: 60s for price data, 5min for token lists.
*/

const DEXSCREENER_BASE = 'https://api.dexscreener.com';
const CACHE_TTL = 60000;
const LIST_TTL = 300000;

const cache = new Map();
const pending = new Map();

function getCached(key, ttl) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > ttl) return null;
  return entry.data;
}

function setCached(key, data) {
  cache.set(key, { data, ts: Date.now() });
}

async function fetchJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function getPairData(mint) {
  const key = `pair:${mint}`;
  const cached = getCached(key, CACHE_TTL);
  if (cached) return cached;

  if (pending.has(key)) return pending.get(key);

  const p = (async () => {
    try {
      const data = await fetchJSON(`${DEXSCREENER_BASE}/token-pairs/v1/solana/${mint}`);
      if (!Array.isArray(data) || data.length === 0) {
        setCached(key, null);
        return null;
      }
      const best = data.sort((a, b) => (b.liquidity?.usd || 0) - (a.liquidity?.usd || 0))[0];
      setCached(key, best);
      return best;
    } catch {
      setCached(key, null);
      return null;
    } finally {
      pending.delete(key);
    }
  })();

  pending.set(key, p);
  return p;
}

export async function getLatestPairs(limit = 50) {
  const key = `latest:${limit}`;
  const cached = getCached(key, LIST_TTL);
  if (cached) return cached;

  try {
    const data = await fetchJSON(`${DEXSCREENER_BASE}/latest/dex/tokens/solana/${limit}`);
    setCached(key, data);
    return data;
  } catch {
    return [];
  }
}

export async function getBoostedTokens() {
  const key = 'boosted';
  const cached = getCached(key, LIST_TTL);
  if (cached) return cached;

  try {
    const data = await fetchJSON(`${DEXSCREENER_BASE}/token-boosts/top/v1/solana`);
    setCached(key, data);
    return data;
  } catch {
    return [];
  }
}

export async function searchTokens(query) {
  if (!query || query.length < 2) return [];
  try {
    const data = await fetchJSON(`${DEXSCREENER_BASE}/latest/dex/search?q=${encodeURIComponent(query)}`);
    return (data?.pairs || []).filter(p => p.chainId === 'solana').slice(0, 20);
  } catch {
    return [];
  }
}

export function formatPrice(n) {
  if (n == null) return '—';
  if (n === 0) return '$0';
  if (n < 0.0001) return `$${Number(n).toExponential(2)}`;
  if (n < 1) return `$${Number(n).toFixed(6)}`;
  if (n < 100) return `$${Number(n).toFixed(4)}`;
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function formatUSD(n) {
  if (n == null) return '—';
  return `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export function formatPct(n) {
  if (n == null) return '—';
  return `${n > 0 ? '+' : ''}${Number(n).toFixed(2)}%`;
}

export function formatAge(t) {
  if (!t) return '—';
  const mins = Math.max(0, Math.floor((Date.now() - t) / 60000));
  if (mins < 60) return `${mins}m`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h`;
  const days = Math.floor(hrs / 24);
  return `${days}d`;
}

export function shortAddr(addr) {
  if (!addr) return '—';
  return `${addr.slice(0, 4)}…${addr.slice(-4)}`;
}
