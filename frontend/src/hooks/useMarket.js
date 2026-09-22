import { useCallback, useEffect, useState } from 'react';
import useSWR from 'swr';
import { marketRequest, tokenKey } from '../lib/dexscreener';

const FEED_CACHE_PREFIX = 'feeless-market-feed:';
const FEED_CACHE_TTL = 14 * 24 * 60 * 60 * 1000;

function isFeedPath(path) {
  return typeof path === 'string' && path.startsWith('/feed?');
}

function readFeedCache(path) {
  if (!isFeedPath(path) || typeof window === 'undefined') return null;
  try {
    const now = Date.now();
    const entries = Object.keys(localStorage).filter(key => key.startsWith(FEED_CACHE_PREFIX));
    entries.forEach(key => {
      const entry = JSON.parse(localStorage.getItem(key) || 'null');
      if (!entry?.savedAt || now - entry.savedAt > FEED_CACHE_TTL) localStorage.removeItem(key);
    });
    const entry = JSON.parse(localStorage.getItem(`${FEED_CACHE_PREFIX}${path}`) || 'null');
    return entry?.savedAt && now - entry.savedAt <= FEED_CACHE_TTL ? entry : null;
  } catch {
    return null;
  }
}

function writeFeedCache(path, data) {
  if (!isFeedPath(path) || typeof window === 'undefined') return;
  try {
    localStorage.setItem(`${FEED_CACHE_PREFIX}${path}`, JSON.stringify({ savedAt: Date.now(), data }));
  } catch {
    // A full or unavailable browser cache must never block the live provider request.
  }
}

export function useMarket(path, refresh = 90000) {
  const cached = readFeedCache(path);
  const fetchMarket = async key => {
    const result = await marketRequest(key);
    writeFeedCache(key, result);
    return result;
  };
  const { data, error, isLoading, isValidating, mutate } = useSWR(path, fetchMarket, {
    refreshInterval: refresh, dedupingInterval: 20000, revalidateOnFocus: false,
    shouldRetryOnError: false, keepPreviousData: true, fallbackData: cached?.data,
  });
  return {
    data,
    error: error?.message,
    loading: isLoading && !data,
    refreshing: Boolean(isValidating && data),
    cached: Boolean(cached && data === cached.data),
    cacheAgeMs: cached ? Date.now() - cached.savedAt : 0,
    reload: mutate,
  };
}

export function useWatchlist() {
  const [watchlist, setWatchlist] = useState(() => {
    try { const data = JSON.parse(localStorage.getItem('feeless-watchlist') || '[]'); return Array.isArray(data) ? data : []; } catch { return []; }
  });
  useEffect(() => { localStorage.setItem('feeless-watchlist', JSON.stringify(watchlist)); }, [watchlist]);
  const toggle = useCallback(pair => setWatchlist(list => list.some(p => tokenKey(p) === tokenKey(pair))
    ? list.filter(p => tokenKey(p) !== tokenKey(pair)) : [...list, pair]), []);
  return { watchlist, toggle, has: p => watchlist.some(w => tokenKey(w) === tokenKey(p)) };
}