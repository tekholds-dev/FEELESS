import { useEffect, useState } from 'react';

// One shared Jupiter poller for every Solana price on screen: components register mints,
// a single batched request every 2s refreshes them all, subscribers re-render on change.
const counts = new Map();
const prices = new Map();
const listeners = new Set();
let timer = null;

async function poll() {
  if (typeof document !== 'undefined' && document.hidden) return;
  const mints = [...counts.keys()];
  for (let i = 0; i < mints.length; i += 50) {
    try {
      const batch = mints.slice(i, i + 50);
      const res = await fetch(`https://lite-api.jup.ag/price/v3?ids=${batch.join(',')}`);
      if (!res.ok) continue;
      const body = await res.json();
      let changed = false;
      batch.forEach(m => {
        const usd = Number(body?.[m]?.usdPrice);
        if (usd > 0 && prices.get(m) !== usd) { prices.set(m, usd); changed = true; }
      });
      if (changed) listeners.forEach(fn => fn());
    } catch {
      // keep last real price
    }
  }
}

function register(mint) {
  counts.set(mint, (counts.get(mint) || 0) + 1);
  if (!timer) { timer = setInterval(poll, 2000); setTimeout(poll, 50); }
}
function unregister(mint) {
  const n = (counts.get(mint) || 1) - 1;
  if (n <= 0) counts.delete(mint); else counts.set(mint, n);
  if (!counts.size && timer) { clearInterval(timer); timer = null; }
}

// Returns { usd, change24h } — live price, and 24h % measured against DexScreener's own
// 24h-ago baseline so it agrees with the rest of the site. Falls back to the snapshot.
export function useLivePrice(pair) {
  const mint = pair?.chainId === 'solana' ? pair?.baseToken?.address : null;
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!mint || typeof fetch !== 'function') return undefined;
    const fn = () => setTick(t => t + 1);
    listeners.add(fn);
    register(mint);
    return () => { listeners.delete(fn); unregister(mint); };
  }, [mint]);
  const snap = Number(pair?.priceUsd);
  const live = mint ? prices.get(mint) : undefined;
  const usd = live ?? (Number.isFinite(snap) ? snap : null);
  const h24 = Number(pair?.priceChange?.h24);
  const base = snap > 0 && Number.isFinite(h24) ? snap / (1 + h24 / 100) : null;
  const change24h = live && base ? (live / base - 1) * 100 : (Number.isFinite(h24) ? h24 : null);
  const ratio = snap > 0 && usd ? usd / snap : 1;
  return { usd, change24h, live: Boolean(live), scale: ratio };
}
