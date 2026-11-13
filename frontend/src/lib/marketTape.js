import { useCallback, useSyncExternalStore } from 'react';
import { apiUrl } from './api';

// 📟 The live market tape behind the chat scenes (owner 2026-11-12: "live effects and animations in chat, as true real data"): ONE shared poll of
// /api/market/feed (Solana trending, DexScreener + our launchpad index) every 60s, paused while the tab is hidden, however many chats show it.
// Rows keep only pools that really traded in the last 5 minutes. Nothing here is sample data: before the first answer the scenes draw no coins.
export function tapeRows(pairs, n = 12) {
  const out = []; const seen = new Set();
  for (const p of pairs || []) {
    const sym = String(p?.baseToken?.symbol || '').trim(); const m5 = p?.txns?.m5 || {}; const buys = Number(m5.buys) || 0; const sells = Number(m5.sells) || 0;
    const ch = Number(p?.priceChange?.h1); const vol = Number(p?.volume?.m5) || 0;
    if (!sym || buys + sells < 1 || !Number.isFinite(ch) || seen.has(sym.toUpperCase())) continue;
    seen.add(sym.toUpperCase());
    out.push({ sym: sym.slice(0, 10), ch, m5: Number(p?.priceChange?.m5) || 0, buys, sells, vol5m: vol, avgUsd: vol / (buys + sells) });
  }
  return out.sort((a, b) => b.vol5m - a.vol5m).slice(0, n);
}
export const pctText = v => `${v >= 0 ? '+' : '−'}${Math.abs(v) >= 100 ? Math.round(Math.abs(v)) : Math.abs(v).toFixed(1)}%`;

const store = { rows: [], at: 0, listeners: new Set(), timer: null };
function poll() {
  if (document.hidden) return;
  fetch(apiUrl('/api/market/feed?kind=trending&chain=solana')).then(r => (r.ok ? r.json() : null)).then(d => {
    const rows = tapeRows(d?.pairs); if (!rows.length) return;
    store.rows = rows; store.at = Date.now(); store.listeners.forEach(l => l());
  }).catch(() => {});
}
function subscribe(l) {
  store.listeners.add(l);
  if (!store.timer) { poll(); store.timer = setInterval(poll, 60000); }
  return () => { store.listeners.delete(l); if (!store.listeners.size) { clearInterval(store.timer); store.timer = null; } };
}
const empty = [];
export function useMarketTape(on) {
  const sub = useCallback(l => (on ? subscribe(l) : () => {}), [on]);
  return useSyncExternalStore(sub, () => (on ? store.rows : empty));
}
