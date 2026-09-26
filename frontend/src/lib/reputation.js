import { useEffect, useRef, useState } from 'react';
import { apiUrl } from './api';

const seenPairs = new Set();
const memoryCache = new Map();

export const BADGE_LABEL = {
  trusted: 'Trusted creator',
  building: 'Building track record',
  unproven: 'Unproven creator',
  flagged: 'Flagged creator',
  risky: 'Risky creator',
};

async function observe(pair) {
  const address = pair?.baseToken?.address;
  const pairAddress = pair?.pairAddress;
  const chain = pair?.chainId;
  if (!address || !pairAddress || !chain) return null;
  try {
    const res = await fetch(apiUrl('/api/reputation/observe'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chain, pairAddress, baseTokenAddress: address,
        symbol: pair.baseToken?.symbol, dexId: pair.dexId,
        liquidityUsd: pair.liquidity?.usd ?? null, marketCap: pair.marketCap ?? null,
        pairCreatedAt: pair.pairCreatedAt ?? null,
      }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export function useReputation(pair) {
  const [result, setResult] = useState(() => memoryCache.get(pair?.pairAddress) || null);
  const key = pair?.pairAddress;
  const mounted = useRef(true);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!key) return;
    const cached = memoryCache.get(key);
    if (cached) setResult(cached);
    if (seenPairs.has(key)) return;
    seenPairs.add(key);
    observe(pair).then(data => {
      if (!data) return;
      memoryCache.set(key, data);
      if (mounted.current) setResult(data);
    });
  }, [key]); // eslint-disable-line react-hooks/exhaustive-deps
  return result;
}

export async function fetchLeaderboard(chain, view) {
  const params = new URLSearchParams();
  if (chain) params.set('chain', chain);
  if (view) params.set('view', view);
  const res = await fetch(apiUrl(`/api/reputation/leaderboard?${params.toString()}`));
  if (!res.ok) throw new Error('Reputation leaderboard unavailable.');
  return res.json();
}

export async function fetchCreator(chain, address) {
  const res = await fetch(apiUrl(`/api/reputation/creator/${chain}/${address}`));
  if (!res.ok) throw new Error('No observations recorded for this creator yet.');
  return res.json();
}

export async function watchCreator(ownerWallet, chain, address, options = {}) {
  const res = await fetch(apiUrl('/api/reputation/watch'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ownerWallet, chain, address, notifyNewToken: true, notifyFlag: true, botEnabled: false, ...options }),
  });
  if (!res.ok) throw new Error('Could not save this wallet to your watchlist.');
  return res.json();
}

export async function unwatchCreator(ownerWallet, chain, address) {
  const res = await fetch(apiUrl('/api/reputation/unwatch'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ownerWallet, chain, address }),
  });
  if (!res.ok) throw new Error('Could not remove this wallet from your watchlist.');
  return res.json();
}

export async function fetchWatchlist(ownerWallet) {
  const res = await fetch(apiUrl(`/api/reputation/watchlist?ownerWallet=${encodeURIComponent(ownerWallet)}`));
  if (!res.ok) throw new Error('Watchlist unavailable.');
  return res.json();
}

export async function fetchWatchlistFeed(ownerWallet) {
  const res = await fetch(apiUrl(`/api/reputation/watchlist/feed?ownerWallet=${encodeURIComponent(ownerWallet)}`));
  if (!res.ok) throw new Error('Notification feed unavailable.');
  return res.json();
}

export async function fetchClusters(chain = 'solana') {
  const res = await fetch(apiUrl(`/api/reputation/clusters?chain=${chain}`));
  if (!res.ok) throw new Error('Cluster detection unavailable.');
  return res.json();
}

const creatorCache = new Map();
// Cached, failure-silent lookup: most chat posters have never launched a token (404).
export function useCreatorTrust(chain, address) {
  const key = chain && address ? `${chain}:${address}` : null;
  const [value, setValue] = useState(null);
  useEffect(() => {
    if (!key) return undefined;
    let alive = true;
    if (!creatorCache.has(key)) {
      creatorCache.set(key, fetch(apiUrl(`/api/reputation/creator/${chain}/${address}`))
        .then(res => (res.ok ? res.json() : null)).then(d => d?.scoring || null).catch(() => null));
    }
    creatorCache.get(key).then(scoring => { if (alive) setValue(scoring); });
    return () => { alive = false; };
  }, [key, chain, address]);
  return value;
}
