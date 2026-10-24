import { useEffect, useState } from 'react';

// 📈 TRUE MARKET DATA for the perps desk (owner, 2026-10-23: "true chart data ALWAYS"): Coinbase Exchange — a US-regulated venue — public
// candles (REST, 300 per call) + ONE shared websocket of every trade (the `ticker` channel: last price, best bid / ask, 24 h open / high /
// low / volume). The pool-swap candles the coin charts use are not a perps mark (1-minute SOL from one Orca pool read as noise).
export const PRODUCT = { SOL: 'SOL-USD', ETH: 'ETH-USD', BTC: 'BTC-USD' };
const REST = 'https://api.exchange.coinbase.com/products';
const WS = 'wss://ws-feed.exchange.coinbase.com';
export const GRAN = { '1m': 60, '5m': 300, '15m': 900, '1h': 3600 };

// pure: Coinbase rows [time, low, high, open, close, volume] (newest first) → chart bars (oldest first)
export function toBars(rows) {
  return (Array.isArray(rows) ? rows : []).filter(r => Array.isArray(r) && r.length >= 6).map(([t, l, h, o, c, v]) => ({ time: t, open: o, high: h, low: l, close: c, volume: v }))
    .sort((a, b) => a.time - b.time);
}
// pure: one trade folded into the live bar of this bucket (a new bucket opens at the previous close — no gaps, no floating dashes)
export function foldTrade(last, price, size, tSec, gran) {
  const b = Math.floor(tSec / gran) * gran;
  if (!last || b > last.time) return { time: b, open: last ? last.close : price, high: Math.max(price, last ? last.close : price), low: Math.min(price, last ? last.close : price), close: price, volume: size || 0 };
  if (b < last.time) return last;
  return { ...last, high: Math.max(last.high, price), low: Math.min(last.low, price), close: price, volume: (last.volume || 0) + (size || 0) };
}
export async function fetchBars(asset, iv = '1m') {
  const r = await fetch(`${REST}/${PRODUCT[asset]}/candles?granularity=${GRAN[iv] || 60}`);
  if (!r.ok) throw new Error('Coinbase candles unavailable');
  return toBars(await r.json());
}

// ── the one shared trade stream ───────────────────────────────────────────────────────────────────────────────────────────────────
const state = {}; const subs = new Set(); const tradeSubs = new Set(); let ws = null; let retry = 1000; let timer = null; let users = 0; let dirty = false;
function flush() { if (dirty) { dirty = false; subs.forEach(fn => fn()); } }
function open() {
  if (ws || typeof WebSocket === 'undefined') return;
  try { ws = new WebSocket(WS); } catch { ws = null; return; }
  ws.onopen = () => { retry = 1000; ws.send(JSON.stringify({ type: 'subscribe', product_ids: Object.values(PRODUCT), channels: ['ticker'] })); };
  ws.onmessage = e => {
    let m; try { m = JSON.parse(e.data); } catch { return; }
    if (m.type !== 'ticker' || !m.product_id) return;
    const a = Object.keys(PRODUCT).find(k => PRODUCT[k] === m.product_id); if (!a) return;
    const now = Date.now(); const prev = state[a] || { trades: [] };
    const price = Number(m.price); const size = Number(m.last_size) || 0; const t = m.time ? Date.parse(m.time) : now;
    state[a] = { price, bid: Number(m.best_bid) || null, ask: Number(m.best_ask) || null, open24: Number(m.open_24h) || null, high24: Number(m.high_24h) || null,
      low24: Number(m.low_24h) || null, vol24: Number(m.volume_24h) || null, side: m.side, size, at: now, prev: prev.price,
      trades: [...prev.trades.filter(x => now - x < 60000), now].slice(-2000) };
    tradeSubs.forEach(fn => fn(a, price, size, t / 1000));
    dirty = true;
  };
  ws.onclose = () => { ws = null; if (users > 0) { clearTimeout(timer); timer = setTimeout(open, retry); retry = Math.min(15000, retry * 2); } };
  ws.onerror = () => { try { ws?.close(); } catch { /* closing */ } };
}
let pump = null;
function use(on) {
  users += on ? 1 : -1;
  if (users > 0) { open(); if (!pump) pump = setInterval(flush, 250); }   // re-render at most 4× a second, whatever the trade rate
  if (users <= 0) { users = 0; clearInterval(pump); pump = null; clearTimeout(timer); try { ws?.close(); } catch { /* closing */ } ws = null; }
}
// every trade, as it prints (the chart folds them into its live candle)
export function onTrade(fn) { tradeSubs.add(fn); use(true); return () => { tradeSubs.delete(fn); use(false); }; }
// the live ticker of one market: price, bid / ask, 24 h stats, trades in the last minute, ms since the last print
export function useTicker(asset) {
  const [, setN] = useState(0);
  useEffect(() => { const fn = () => setN(n => n + 1); subs.add(fn); use(true); return () => { subs.delete(fn); use(false); }; }, []);
  const s = state[asset] || null;
  return s ? { ...s, tpm: s.trades.length } : null;
}
export function useTickers() {
  const [, setN] = useState(0);
  useEffect(() => { const fn = () => setN(n => n + 1); subs.add(fn); use(true); return () => { subs.delete(fn); use(false); }; }, []);
  return Object.fromEntries(Object.keys(PRODUCT).map(a => [a, state[a] ? { ...state[a], tpm: state[a].trades.length } : null]));
}
