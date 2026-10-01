import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// COIN EDGE: ONE shared poller for every coin on screen (GET /api/reputation/edge — pulse, snipers out, verification,
// forensics, runner gates + bond boxes, Fuse sources, elite flow). Mounted coins register; one batched request (≤60 per
// call, 250ms batching) every 15s; repeat polls pause while the tab is hidden (the first load always runs).
// usePumpPulse / useSnipersOut / useVerified / fetchIntel all read from here — never add another per-coin poller.
const REFRESH_MS = 15000;
const counts = new Map();      // mint -> mounted consumers
const edges = new Map();       // mint -> edge record
const listeners = new Set();
let timer = null; let queued = null;

async function load(list) {
  for (let i = 0; i < list.length; i += 60) {
    try {
      const r = await Promise.resolve().then(() => fetch(apiUrl(`/api/reputation/edge?mints=${list.slice(i, i + 60).join(',')}`)));
      if (!r?.ok) continue;
      const { edge = {} } = await r.json();
      Object.entries(edge).forEach(([m, v]) => edges.set(m, v));
    } catch { /* keep the last known edge */ }
  }
  listeners.forEach(fn => fn());
}
const refresh = () => { if (!document.hidden) load([...counts.keys()].sort()); };
function schedule() {
  if (!queued) queued = setTimeout(() => { queued = null; load([...counts.keys()].filter(m => !edges.has(m))); }, 250);
  if (!timer) timer = setInterval(refresh, REFRESH_MS);
}

export function useCoinEdge(mint) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (!mint || !/^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(mint)) return undefined;
    counts.set(mint, (counts.get(mint) || 0) + 1);
    const fn = () => setTick(t => t + 1); listeners.add(fn);
    if (!edges.has(mint)) schedule(); else if (!timer) timer = setInterval(refresh, REFRESH_MS);
    return () => {
      listeners.delete(fn);
      const n = (counts.get(mint) || 1) - 1; if (n) counts.set(mint, n); else counts.delete(mint);
      if (!counts.size && timer) { clearInterval(timer); timer = null; }
    };
  }, [mint]);
  return mint ? edges.get(mint) || null : null;
}

export const edgeOf = mint => edges.get(mint) || null;           // non-hook read (null until a hook loaded it)
export const dropEdge = mint => { edges.delete(mint); };

// One coin's edge WITH forensics (runs the holder scan server-side if it isn't cached) — the tape's wallet tags.
const intelReq = new Map();
export function fetchEdgeIntel(mint) {
  const hit = intelReq.get(mint);
  if (hit && Date.now() - hit.at < 60000) return hit.p;
  const p = Promise.resolve().then(() => fetch(apiUrl(`/api/reputation/edge?mints=${mint}&intel=1`))).then(r => (r?.ok ? r.json() : null))
    .then(d => { const e = d?.edge?.[mint]; if (e) { edges.set(mint, e); listeners.forEach(fn => fn()); } return e?.intel || null; }).catch(() => null);
  intelReq.set(mint, { at: Date.now(), p });
  return p;
}
