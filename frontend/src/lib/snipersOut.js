import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Snipers-out hub: one shared /radar poll for every coin card on screen. A coin is tagged for
// WINDOW_MS after all of its flagged snipers/bundlers sold out (server: token intel forensics).
const REFRESH_MS = 30000;
const WINDOW_MS = 6 * 3600 * 1000;
const out = new Map(); // mint or pair address -> radar event
const listeners = new Set();
let timer = null;

async function refresh() {
  try {
    const res = await fetch(apiUrl('/api/reputation/radar'));
    if (!res.ok) return;
    const { events = [] } = await res.json();
    out.clear();
    events.filter(e => e.kind === 'snipers-out' && Date.now() - e.at * 1000 < WINDOW_MS).forEach(e => {
      out.set(e.pair, e);
      if (e.mint) out.set(e.mint, e);
    });
    listeners.forEach(fn => fn());
  } catch { /* keep the last known state */ }
}

export function useSnipersOut(pair) {
  const [, setTick] = useState(0);
  useEffect(() => {
    const listener = () => setTick(t => t + 1);
    listeners.add(listener);
    if (!timer) { refresh(); timer = setInterval(refresh, REFRESH_MS); }
    return () => {
      listeners.delete(listener);
      if (!listeners.size && timer) { clearInterval(timer); timer = null; }
    };
  }, []);
  if (pair?.chainId !== 'solana') return null;
  return out.get(pair?.baseToken?.address) || out.get(pair?.pairAddress) || null;
}
