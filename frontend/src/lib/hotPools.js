import { useEffect, useState } from 'react';

// 🔥 HOT POOLS (owner, 2026-10-23: "$5–10 should make $0.50–1 — find better pools"): the Meteora DAMM v2 SOL pools paying their LPs the most
// RIGHT NOW (Meteora's own data API, read straight from the browser — no GeckoTerminal), each joinable in place (lib/lpBuilder.js). A new buy
// door, so it ships with GUARDS (memory: new-buy-doors-need-guards): SOL-paired · not blacklisted · ≥ $20K deep · ≥ $50K traded in 24h ·
// ≥ 6 h old · the coin's freeze authority off · ≥ 300 holders. One shared read a minute for every desk on the page.
const URL = 'https://damm-v2.datapi.meteora.ag/pools?page_size=100&sort_by=volume_24h:desc';
const SOL = 'So11111111111111111111111111111111111111112';
export const GUARD = { tvl: 20000, vol: 50000, ageH: 6, holders: 300 };

// pure: one API row → a hot pool (or null when a guard says no); feeDay = what LPs kept of the last 24h of fees ÷ the pool's depth
export function hotRow(r, now = Date.now()) {
  if (!r?.address || r.is_blacklisted) return null;
  const xSol = r.token_x?.address === SOL; const ySol = r.token_y?.address === SOL; if (xSol === ySol) return null;
  const coin = xSol ? r.token_y : r.token_x; const tvl = Number(r.tvl) || 0; const vol = Number(r.volume?.['24h']) || 0; const ageH = (now - (Number(r.created_at) || now)) / 3.6e6;
  if (tvl < GUARD.tvl || vol < GUARD.vol || ageH < GUARD.ageH || coin?.freeze_authority_disabled === false || (Number(coin?.holders) || 0) < GUARD.holders) return null;
  const lp = (Number(r.fees?.['24h']) || 0) - (Number(r.protocol_fees?.['24h']) || 0); const feeDay = lp > 0 ? lp / tvl : 0; if (!feeDay) return null;
  return { id: r.address, pool: r.address, sym: `${coin.symbol}-SOL`, coin: coin.address, coinSym: coin.symbol, mc: Number(coin.market_cap) || null, holders: Number(coin.holders) || 0,
    tvl, vol, feeDay, apy: feeDay * 365 * 100, ageH, hour: (Number(r.fees?.['1h']) || 0) / tvl, proto: 'Meteora DAMM v2', kind: 'damm' };
}
export const hotRows = (data, now = Date.now()) => (data?.data || []).map(r => hotRow(r, now)).filter(Boolean).sort((a, b) => b.feeDay - a.feeDay);

let last = { at: 0, p: null };
// tests never touch the network: under jsdom the feed is empty unless a test hands in its own fetch
const jsdom = () => typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent || '');
let fetchHot = () => (jsdom() ? Promise.resolve(null) : fetch(URL).then(r => (r.ok ? r.json() : null)));
export const _setHotFetch = fn => { fetchHot = fn; last = { at: 0, p: null }; };
export function readHot() {
  if (last.p && Date.now() - last.at < 60000) return last.p;
  last = { at: Date.now(), p: Promise.resolve().then(() => fetchHot()).then(d => hotRows(d)).catch(() => { last.at = 0; return []; }) };
  return last.p;
}
export function useHotPools(on = true) {
  const [rows, setRows] = useState(null);
  useEffect(() => { if (!on) return undefined; let alive = true; const go = () => readHot().then(x => alive && setRows(x));
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); return () => { alive = false; clearInterval(t); }; }, [on]);
  return rows;
}
