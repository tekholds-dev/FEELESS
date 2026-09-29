import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Pump Pulse hub: every mounted bolt/banner registers its mint; one batched request every 15s
// covers all of them (the server caps at 60 mints and checks DexScreener's 5m flow).
const REFRESH_MS = 15000;
const counts = new Map();       // mint -> number of mounted consumers
const stats = new Map();        // mint -> latest pulse stats
const listeners = new Set();
let timer = null;
let queued = null;

async function refresh() {
  const mints = [...counts.keys()].sort();
  if (!mints.length) return;
  for (let i = 0; i < mints.length; i += 60) {
    try {
      const res = await fetch(apiUrl(`/api/market/pulse?mints=${mints.slice(i, i + 60).join(',')}`));
      if (!res.ok) continue;
      const body = await res.json();
      Object.entries(body.coins || {}).forEach(([mint, value]) => stats.set(mint, value));
    } catch { /* keep the last known pulse */ }
  }
  listeners.forEach(fn => fn());
}

function schedule() {
  // Batch registrations from one render pass into a single request.
  if (!queued) queued = setTimeout(() => { queued = null; refresh(); }, 250);
  if (!timer) timer = setInterval(refresh, REFRESH_MS);
}

export function usePumpPulse(mint) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!mint) return undefined;
    counts.set(mint, (counts.get(mint) || 0) + 1);
    const listener = () => setTick(t => t + 1);
    listeners.add(listener);
    if (!stats.has(mint)) schedule(); else if (!timer) timer = setInterval(refresh, REFRESH_MS);
    return () => {
      listeners.delete(listener);
      const left = (counts.get(mint) || 1) - 1;
      if (left) counts.set(mint, left); else counts.delete(mint);
      if (!counts.size && timer) { clearInterval(timer); timer = null; }
    };
  }, [mint]);
  return mint ? stats.get(mint) || null : null;
}

export const pulseSummary = s => {
  if (!s) return '';
  const change = Number.isFinite(s.m5Change) ? `${s.m5Change >= 0 ? '+' : ''}${s.m5Change.toFixed(1)}%` : '—';
  return `${change} · ${s.buys + s.sells} trades (${s.buyShare}% buys) · $${Math.round(s.volumeM5).toLocaleString()} vol`;
};
