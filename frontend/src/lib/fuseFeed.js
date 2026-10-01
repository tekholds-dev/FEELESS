import { useEffect, useState } from 'react';
import { apiUrl } from './api';

// Published Fuses: ONE shared /fuses poll (60s) for every chat card / panel on screen.
const REFRESH_MS = 60000;
let fuses = null;
const listeners = new Set();
let timer = null;

async function refresh() {
  try { const r = await fetch(apiUrl('/api/reputation/fuses')); if (r.ok) { fuses = (await r.json()).fuses || []; listeners.forEach(fn => fn()); } } catch { /* keep last */ }
}

export function useFuses() {
  const [, setTick] = useState(0);
  useEffect(() => {
    const fn = () => setTick(t => t + 1);
    listeners.add(fn);
    if (!timer) { refresh(); timer = setInterval(() => !document.hidden && refresh(), REFRESH_MS); }
    return () => { listeners.delete(fn); if (!listeners.size && timer) { clearInterval(timer); timer = null; } };
  }, []);
  return fuses;
}

export const FUSE_TAG = /⚛️\s?fuse:([a-z0-9]{6,16})/i;
// `/fuse [name]` → the published Fuse to share (name match, else the best-graded).
export function pickFuse(list, q) {
  const s = String(q || '').trim().toLowerCase();
  return (s && (list || []).find(f => f.name.toLowerCase().includes(s))) || (list || [])[0] || null;
}
