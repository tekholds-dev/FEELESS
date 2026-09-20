import { useCallback, useEffect, useState } from 'react';
import useSWR from 'swr';
import { marketRequest, tokenKey } from '../lib/dexscreener';

export function useMarket(path, refresh = 90000) {
  const { data, error, isLoading, mutate } = useSWR(path, marketRequest, {
    refreshInterval: refresh, dedupingInterval: 20000, revalidateOnFocus: false,
    shouldRetryOnError: false, keepPreviousData: false,
  });
  return { data, error: error?.message, loading: isLoading, reload: mutate };
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