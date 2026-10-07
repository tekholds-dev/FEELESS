import { useEffect, useState } from 'react';

// Live prices for every card on screen: ONE shared poller (DexScreener pairs, 30 per call, every 3s — live like the trenches —
// paused while the tab is hidden, never two calls in flight, backs off to 10s for a minute if DexScreener rate-limits (429)).
// Cards subscribe with the pair addresses they show; unsubscribed pairs stop being fetched.
const REFRESH_MS = process.env.NODE_ENV === 'test' ? 10000 : 3000;   // tests keep the slow clock (jsdom timers)
const SLOW_MS = 10000;
let busy = false;
let slowUntil = 0;
let lastAt = 0;
const want = new Map();          // pairAddress -> subscriber count
const prices = new Map();        // pairAddress -> { price, m5, h1, mc, at }
const listeners = new Set();
let timer = null;

async function refresh(force = false) {
  if (document.hidden || !want.size || busy) return;
  if (!force && Date.now() < slowUntil && Date.now() - lastAt < SLOW_MS) return;
  busy = true; lastAt = Date.now();
  const all = [...want.keys()];
  const chunks = []; for (let i = 0; i < all.length; i += 30) chunks.push(all.slice(i, i + 30));
  await Promise.all(chunks.map(c => Promise.resolve().then(() => fetch(`https://api.dexscreener.com/latest/dex/pairs/solana/${c.join(',')}`)).then(r => { if (r.status === 429) { slowUntil = Date.now() + 60000; return {}; } return r.json(); }).then(d => {
    (d.pairs || []).forEach(p => prices.set(p.pairAddress, { price: Number(p.priceUsd) || 0, m5: Number(p.priceChange?.m5) || 0, h1: Number(p.priceChange?.h1) || 0, mc: Number(p.marketCap) || Number(p.fdv) || 0, at: Date.now() }));
  }).catch(() => {})));
  busy = false;
  listeners.forEach(fn => fn());
}

export function useLivePrices(pairs) {
  const [, setTick] = useState(0);
  const key = (pairs || []).filter(Boolean).join(',');
  useEffect(() => {
    const list = key ? key.split(',') : [];
    if (!list.length) return undefined;
    const fn = () => setTick(t => t + 1);
    list.forEach(p => want.set(p, (want.get(p) || 0) + 1)); listeners.add(fn);
    if (!timer) timer = setInterval(refresh, REFRESH_MS);
    if (list.some(p => !prices.has(p))) refresh(true);
    return () => { list.forEach(p => { const n = (want.get(p) || 1) - 1; if (n) want.set(p, n); else want.delete(p); }); listeners.delete(fn); if (!listeners.size && timer) { clearInterval(timer); timer = null; } };
  }, [key]);
  return prices;
}
