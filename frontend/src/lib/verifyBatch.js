import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Verified checks for every logo on screen: pooled into one request per ~150ms, cached 10 min.
// A board with 200 coins costs one call. The server verifies unknown coins in the background.
const cache = new Map(); // mint -> { v, at }
const waiters = new Map();
let queue = new Set(); let timer = null;
const TTL = 600000;

function flush() {
  const list = [...queue]; queue = new Set(); timer = null;
  if (!list.length || typeof fetch !== 'function') return;
  Promise.resolve().then(() => fetch(apiUrl(`/api/reputation/verify/batch?mints=${list.join(',')}`))).then(r => r.json()).then(({ verify = {} } = {}) => {
    const missing = [];
    list.forEach(m => {
      const v = verify[m] || null;
      if (v) { cache.set(m, { v, at: Date.now() }); waiters.get(m)?.forEach(fn => fn(v)); } else missing.push(m);
    });
    if (missing.length) setTimeout(() => missing.forEach(m => want(m, true)), 8000);   // background check lands
  }).catch(() => {});
}
function want(m, retry) {
  const hit = cache.get(m);
  if (hit && Date.now() - hit.at < TTL) return;
  if (!retry && queue.has(m)) return;
  queue.add(m); if (!timer) timer = setTimeout(flush, 150);
}
export function useVerified(mint) {
  const [v, setV] = useState(() => cache.get(mint)?.v || null);
  useEffect(() => {
    if (!mint || !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(mint)) return undefined;
    const set = waiters.get(mint) || new Set(); set.add(setV); waiters.set(mint, set);
    if (cache.get(mint)) setV(cache.get(mint).v);
    want(mint);
    return () => { set.delete(setV); };
  }, [mint]);
  return v;
}
export const clearVerified = mint => { cache.delete(mint); };
