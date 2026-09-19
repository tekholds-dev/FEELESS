// DexScreener API wrapper - no API key required
const BASE = 'https://api.dexscreener.com';

export async function searchTokenByAddress(address) {
  try {
    const res = await fetch(`${BASE}/latest/dex/tokens/${address}`);
    if (!res.ok) throw new Error('lookup failed');
    const data = await res.json();
    return data.pairs || [];
  } catch (e) {
    console.error('DexScreener token lookup error', e);
    return [];
  }
}

export async function searchTokens(query) {
  try {
    const res = await fetch(`${BASE}/latest/dex/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error('search failed');
    const data = await res.json();
    return data.pairs || [];
  } catch (e) {
    console.error('DexScreener search error', e);
    return [];
  }
}

export async function getTrendingByChain(chainId) {
  // DexScreener trending: use search with chain filter
  try {
    const res = await fetch(`${BASE}/token-boosts/top/v1`);
    if (!res.ok) throw new Error('trending failed');
    const data = await res.json();
    // Filter by chain
    const arr = Array.isArray(data) ? data : [];
    return arr.filter(t => !chainId || t.chainId === chainId).slice(0, 20);
  } catch (e) {
    console.error('DexScreener trending error', e);
    return [];
  }
}

export async function getLatestBoosts() {
  try {
    const res = await fetch(`${BASE}/token-boosts/latest/v1`);
    if (!res.ok) throw new Error('latest failed');
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
}

export async function getPairsByTokenAddress(chainId, address) {
  try {
    const res = await fetch(`${BASE}/token-pairs/v1/${chainId}/${address}`);
    if (!res.ok) throw new Error('pairs failed');
    const data = await res.json();
    return Array.isArray(data) ? data : [];
  } catch (e) {
    return [];
  }
}

export function detectChainFromPair(pair) {
  return pair?.chainId || null;
}

export function formatUSD(n) {
  if (n === null || n === undefined || isNaN(n)) return '—';
  const num = Number(n);
  if (num >= 1e9) return `$${(num / 1e9).toFixed(2)}B`;
  if (num >= 1e6) return `$${(num / 1e6).toFixed(2)}M`;
  if (num >= 1e3) return `$${(num / 1e3).toFixed(2)}K`;
  if (num >= 1) return `$${num.toFixed(2)}`;
  if (num > 0) return `$${num.toFixed(6)}`;
  return '$0';
}

export function formatAge(ts) {
  if (!ts) return '—';
  const now = Date.now();
  const diff = now - ts;
  const days = Math.floor(diff / 86400000);
  const hrs = Math.floor((diff % 86400000) / 3600000);
  if (days > 0) return `${days}d ${hrs}h`;
  const mins = Math.floor(diff / 60000);
  if (hrs > 0) return `${hrs}h ${mins % 60}m`;
  return `${mins}m`;
}
