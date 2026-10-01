import { useCallback, useSyncExternalStore } from 'react';
import { apiUrl } from './api';
import { fetchIntel } from './coinIntel';

// A coin room's mood, for its live chat background: one shared poll per coin (30s), however many chats show it.
//   pump  = up ≥3% in 5m or ≥10% in 1h      dump = the mirror
//   clear = every flagged sniper has sold   calm = anything else
export function moodOf(pair, intel) {
  const m5 = Number(pair?.priceChange?.m5) || 0; const h1 = Number(pair?.priceChange?.h1) || 0;
  if (m5 >= 3 || h1 >= 10) return 'pump';
  if (m5 <= -3 || h1 <= -10) return 'dump';
  if ((intel?.sniperWallets || []).length && Number(intel?.snipersHoldingPct) === 0) return 'clear';
  return 'calm';
}
export const roomPair = room => { const m = /^coin-([a-z]+)-([A-Za-z0-9]{20,})/.exec(String(room || '')); return m ? { chain: m[1], pair: m[2] } : null; };

const rooms = new Map(); // key -> { mood, listeners, timer }
function poll(key, chain, pair) {
  const r = rooms.get(key); if (!r || document.hidden) return;
  fetch(apiUrl(`/api/market/pair/${chain}/${pair}`)).then(x => (x.ok ? x.json() : null)).then(async d => {
    const p = d?.pairs?.[0]; if (!p) return;
    const intel = chain === 'solana' ? await fetchIntel(chain, p.baseToken?.address) : null;
    const mood = moodOf(p, intel);
    if (mood !== r.mood) { r.mood = mood; r.listeners.forEach(l => l()); }
  }).catch(() => {});
}
function subscribe(room, l) {
  const rp = roomPair(room); if (!rp) return () => {};
  const key = `${rp.chain}:${rp.pair}`;
  let r = rooms.get(key);
  if (!r) { r = { mood: 'calm', listeners: new Set(), timer: null }; rooms.set(key, r); }
  r.listeners.add(l);
  if (!r.timer) { poll(key, rp.chain, rp.pair); r.timer = setInterval(() => poll(key, rp.chain, rp.pair), 30000); }
  return () => { r.listeners.delete(l); if (!r.listeners.size) { clearInterval(r.timer); rooms.delete(key); } };
}
export function useCoinMood(room) {
  const sub = useCallback(l => subscribe(room, l), [room]);
  return useSyncExternalStore(sub, () => { const rp = roomPair(room); return (rp && rooms.get(`${rp.chain}:${rp.pair}`)?.mood) || 'calm'; });
}
