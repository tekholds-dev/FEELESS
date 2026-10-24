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
    const now = Date.now(); const prev = state[a] || { trades: [], flow: [], px: [] };
    const price = Number(m.price); const size = Number(m.last_size) || 0; const t = m.time ? Date.parse(m.time) : now;
    const buy = m.side === 'sell';   // Coinbase's `side` is the MAKER's: a resting sell filled = a taker BUY (an up-tick)
    const flow = [...prev.flow.filter(x => now - x.t < 300000), { t: now, usd: price * size, buy }].slice(-6000);
    const px = prev.px.length && now - prev.px[prev.px.length - 1].t < 1000 ? prev.px : [...prev.px.filter(x => now - x.t < 3600000), { t: now, p: price }].slice(-3700);
    state[a] = { price, bid: Number(m.best_bid) || null, ask: Number(m.best_ask) || null, open24: Number(m.open_24h) || null, high24: Number(m.high_24h) || null,
      low24: Number(m.low_24h) || null, vol24: Number(m.volume_24h) || null, side: m.side, size, at: now, prev: prev.price,
      trades: [...prev.trades.filter(x => now - x < 60000), now].slice(-2000), flow, px };
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

// ── order flow (pure): taker buy vs sell $ in a window, the whale prints, the move over a window, realized volatility ────────────────
export const WHALE_USD = { BTC: 50000, ETH: 25000, SOL: 10000 };
export function flowOf(flow, ms, now) {
  let b = 0; let s = 0; let n = 0; let top = null;
  (flow || []).forEach(x => { if (now - x.t > ms) return; n += 1; if (x.buy) b += x.usd; else s += x.usd; if (!top || x.usd > top.usd) top = x; });
  return { buy: b, sell: s, n, top, share: b + s > 0 ? b / (b + s) : null };
}
export const whales = (flow, min, k = 8) => (flow || []).filter(x => x.usd >= min).slice(-k).reverse();
export function moveOf(px, ms, now) {
  const w = (px || []).filter(x => now - x.t <= ms); if (w.length < 2) return null;
  return (w[w.length - 1].p / w[0].p - 1) * 100;
}
// realized volatility over the last hour of 1-second samples → annualized % (√ of seconds a year)
export function rvol(px) {
  const p = (px || []).map(x => x.p); if (p.length < 30) return null;
  const r = []; for (let i = 1; i < p.length; i += 1) if (p[i - 1] > 0) r.push(Math.log(p[i] / p[i - 1]));
  const m = r.reduce((a, b) => a + b, 0) / r.length; const v = r.reduce((a, b) => a + (b - m) ** 2, 0) / Math.max(1, r.length - 1);
  return Math.sqrt(v) * Math.sqrt(365 * 24 * 3600) * 100;
}
