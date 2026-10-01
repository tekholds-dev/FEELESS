import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// 🪪 TRADER IDS: one shared poller for every trader chip on screen (GET /api/reputation/fuses/ids — ⚛️ score, medals,
// battle W/L from the server's cache). Chips register; one batched request (≤40, 250ms batching) every 60s; wallets
// the server is still warming get one quick retry. Repeat polls pause while the tab is hidden.
const REFRESH_MS = 60000;
const counts = new Map(); const ids = new Map(); const listeners = new Set();
let timer = null; let queued = null; let retry = null;

async function load(list) {
  for (let i = 0; i < list.length; i += 40) {
    try {
      const r = await Promise.resolve().then(() => fetch(apiUrl(`/api/reputation/fuses/ids?addrs=${list.slice(i, i + 40).join(',')}`)));
      if (!r?.ok) continue;
      Object.entries((await r.json()).ids || {}).forEach(([a, v]) => ids.set(a, v));
    } catch { /* keep the last known */ }
  }
  listeners.forEach(fn => fn());
  if (!retry && list.some(a => !ids.has(a))) retry = setTimeout(() => { retry = null; load([...counts.keys()].filter(a => !ids.has(a))); }, 4000);
}
const refresh = () => { if (!document.hidden) load([...counts.keys()].sort()); };

export function useTraderId(address) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!address || !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address)) return undefined;
    counts.set(address, (counts.get(address) || 0) + 1);
    const fn = () => setTick(t => t + 1); listeners.add(fn);
    if (!ids.has(address) && !queued) queued = setTimeout(() => { queued = null; load([...counts.keys()].filter(a => !ids.has(a))); }, 250);
    if (!timer) timer = setInterval(refresh, REFRESH_MS);
    return () => {
      listeners.delete(fn);
      const n = (counts.get(address) || 1) - 1; if (n) counts.set(address, n); else counts.delete(address);
      if (!counts.size && timer) { clearInterval(timer); timer = null; }
    };
  }, [address]);
  return address ? ids.get(address) || null : null;
}
