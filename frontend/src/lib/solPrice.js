import { useEffect, useState } from 'react';

// SOL/USD for "≈ $" hints. One request per minute shared by every caller.
const SOL = 'So11111111111111111111111111111111111111112';
let cache = { at: 0, p: null, pending: null };
export function getSolPrice() {
  if (cache.p && Date.now() - cache.at < 60000) return Promise.resolve(cache.p);
  if (!cache.pending) cache.pending = fetch(`/api/candles/prices?mints=${SOL}`).then(r => r.json())   // the server's shared live price (the browser never calls Jupiter itself: it 429'd)
    .then(d => { cache = { at: Date.now(), p: Number(d?.[SOL]) || null, pending: null }; return cache.p; })
    .catch(() => { cache.pending = null; return cache.p; });
  return cache.pending;
}
export function useSolPrice() {
  const [p, setP] = useState(cache.p);
  useEffect(() => { let alive = true; getSolPrice().then(v => alive && setP(v)); return () => { alive = false; }; }, []);
  return p;
}
export const usd = (sol, p) => (p && Number(sol) > 0 ? `≈ $${(Number(sol) * p).toLocaleString(undefined, { maximumFractionDigits: Number(sol) * p < 10 ? 2 : 0 })}` : '');
