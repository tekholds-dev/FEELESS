import { useEffect, useState } from 'react';

// Live prices for every card on screen: ONE shared poller (DexScreener pairs, 30 per call, every 10s, paused while the
// tab is hidden). Cards subscribe with the pair addresses they show; unsubscribed pairs stop being fetched.
const REFRESH_MS = 10000;
const want = new Map();          // pairAddress -> subscriber count
const prices = new Map();        // pairAddress -> { price, m5, h1, at }
const listeners = new Set();
let timer = null;

async function refresh() {
  if (document.hidden || !want.size) return;
  const all = [...want.keys()];
  const chunks = []; for (let i = 0; i < all.length; i += 30) chunks.push(all.slice(i, i + 30));
  await Promise.all(chunks.map(c => Promise.resolve().then(() => fetch(`https://api.dexscreener.com/latest/dex/pairs/solana/${c.join(',')}`)).then(r => r.json()).then(d => {
    (d.pairs || []).forEach(p => prices.set(p.pairAddress, { price: Number(p.priceUsd) || 0, m5: Number(p.priceChange?.m5) || 0, h1: Number(p.priceChange?.h1) || 0, at: Date.now() }));
  }).catch(() => {})));
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
    if (list.some(p => !prices.has(p))) refresh();
    return () => { list.forEach(p => { const n = (want.get(p) || 1) - 1; if (n) want.set(p, n); else want.delete(p); }); listeners.delete(fn); if (!listeners.size && timer) { clearInterval(timer); timer = null; } };
  }, [key]);
  return prices;
}
