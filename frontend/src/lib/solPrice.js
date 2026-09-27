import { useEffect, useState } from 'react';

// SOL/USD for "≈ $" hints. One request per minute shared by every caller.
const SOL = 'So11111111111111111111111111111111111111112';
let cache = { at: 0, p: null, pending: null };
export function getSolPrice() {
  if (cache.p && Date.now() - cache.at < 60000) return Promise.resolve(cache.p);
  if (!cache.pending) cache.pending = fetch(`https://lite-api.jup.ag/price/v3?ids=${SOL}`).then(r => r.json())
    .then(d => { cache = { at: Date.now(), p: Number(d?.[SOL]?.usdPrice) || null, pending: null }; return cache.p; })
    .catch(() => { cache.pending = null; return cache.p; });
  return cache.pending;
}
export function useSolPrice() {
  const [p, setP] = useState(cache.p);
  useEffect(() => { let alive = true; getSolPrice().then(v => alive && setP(v)); return () => { alive = false; }; }, []);
  return p;
}
export const usd = (sol, p) => (p && Number(sol) > 0 ? `≈ $${(Number(sol) * p).toLocaleString(undefined, { maximumFractionDigits: Number(sol) * p < 10 ? 2 : 0 })}` : '');
