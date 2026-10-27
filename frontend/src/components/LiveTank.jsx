import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import '../styles/liveTank.css';

// 🫧 THE LIVE INTAKE TANK (owner 2026-10-26: "intakes sitewide need advanced LEVELS — brand-new launches, germ, the regular one from the agents tab,
// pump trending + top new"). One compact glass tank, five levels, every bubble a real coin from a real read:
//   NEW       every pump.fun launch the moment it happens (PumpPortal stream, /api/pump/pulse) — across = age, up = MC, colour = curve progress
//   GERM      the agents' intake coins sitting near their germ floor (−3…+10 %) — the buy zone their chart reads
//   DESK      the agents' whole intake list (READY glows) — across = 5-min move, up = MC
//   TRENDING  pump.fun trending pools — across = 1-hour move, up = MC
//   TOP NEW   the newest pools with real money in them — across = age (24 h), up = MC
// One read per level every few seconds, shared by every tank on the page; paused while hidden; still under fx-lite / reduced motion.
const LEVELS = [
  ['new', '🆕 NEW', 'Every pump.fun launch as it happens', '/api/pump/pulse?limit=40', 4000],
  ['germ', '🦠 GERM', "The agents' intake coins near their germ floor (−3…+10 %)", '/api/reputation/familia/intake', 30000],
  ['desk', '🛰 DESK', "The agents' intake list — READY coins glow", '/api/reputation/familia/intake', 30000],
  ['trend', '🔥 TRENDING', 'pump.fun trending pools', '/api/market/feed?kind=trending&chain=solana&page=1&scope=pump', 15000],
  ['top', '⭐ TOP NEW', 'The newest pools with real money in them', '/api/market/feed?kind=new&chain=solana&page=1', 20000],
];
const reads = new Map();   // url → { d, subs:Set, timer }
function useRead(url, every) {
  const [d, setD] = useState(reads.get(url)?.d || null);
  useEffect(() => {
    let r = reads.get(url);
    if (!r) { r = { d: null, subs: new Set(), timer: null }; reads.set(url, r); }
    const poll = async () => { if (document.hidden) return; try { const x = await fetch(apiUrl(url)); if (x.ok) { r.d = await x.json(); r.subs.forEach(f => f(r.d)); } } catch { /* keep the last read */ } };
    setD(r.d); r.subs.add(setD); if (!r.timer) { poll(); r.timer = setInterval(poll, every); }
    return () => { r.subs.delete(setD); if (!r.subs.size) { clearInterval(r.timer); r.timer = null; } };
  }, [url, every]);
  return d;
}
const lg = (v, lo, hi) => Math.max(0, Math.min(1, Math.log(Math.max(lo, Math.min(hi, Number(v) || lo)) / lo) / Math.log(hi / lo)));
const lin = (v, lo, hi) => Math.max(0, Math.min(1, ((Number(v) || 0) - lo) / (hi - lo)));
const usd = v => (!(v > 0) ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);

// pure: one pump launch → where it floats (the NEW level)
export function place(l, now = Date.now()) {
  const age = Math.max(0, Math.min(1, (now - Number(l.at || now)) / (10 * 60000)));
  return { x: 1 - age, y: lg(l.marketCapUsd, 2000, 100000), r: 6 + Math.min(14, Math.sqrt(Math.max(0, Number(l.devBuySol) || 0)) * 9), p: Math.max(0, Math.min(1, (Number(l.curveProgress) || 0) / 100)) };
}
// pure: a level's read → bubbles {id, sym, x, y, r, p (0 green … 1 gold), tip, href} + the axis words
export function bubbles(level, d, now = Date.now()) {
  if (level === 'new') return { axis: ['$2K', '$100K', 'NOW →'], rows: (d?.launches || []).slice(0, 40).map(l => ({ id: l.mint, sym: l.symbol, ...place(l, now), href: `https://pump.fun/coin/${l.mint}`,
    tip: `$${l.symbol} · ${usd(l.marketCapUsd)} MC · ${Math.round(l.curveProgress || 0)}% up the curve${l.devBuySol ? ` · dev ${l.devBuySol.toFixed(2)} SOL` : ''}` })) };
  if (level === 'germ' || level === 'desk') {
    const coins = (d?.coins || []).filter(c => level === 'desk' || (c.germ != null && c.germ >= -3 && c.germ <= 10));
    return { axis: ['$10K', '$10M', '5M MOVE →'], rows: coins.map(c => ({ id: c.mint, sym: c.sym, x: lin(c.ch, -20, 40), y: lg(c.mc, 1e4, 1e7), r: /READY/i.test(c.status || '') ? 13 : 8,
      p: level === 'germ' ? lin(c.germ, -3, 10) : /READY/i.test(c.status || '') ? 1 : 0.15, href: c.pair ? `https://dexscreener.com/solana/${c.pair}` : null,
      tip: `$${c.sym} · ${usd(c.mc)} MC · 5m ${c.ch != null ? `${c.ch >= 0 ? '+' : ''}${Number(c.ch).toFixed(1)}%` : '—'} · ${c.status || ''}${c.germ != null ? ` · ${c.germ >= 0 ? '+' : ''}${Number(c.germ).toFixed(1)}% vs its germ floor` : ''}` })) };
  }
  const pairs = (d?.pairs || []).filter(p => p?.baseToken?.address).slice(0, 40);
  if (level === 'trend') return { axis: ['$10K', '$10M', '1H MOVE →'], rows: pairs.map(p => ({ id: p.pairAddress, sym: p.baseToken.symbol, x: lin(p.priceChange?.h1, -30, 100), y: lg(p.marketCap ?? p.fdv, 1e4, 1e7),
    r: 6 + Math.min(12, Math.sqrt((Number(p.volume?.h1) || 0) / 2000)), p: lin(p.priceChange?.h1, 0, 100), href: `https://dexscreener.com/solana/${p.pairAddress}`,
    tip: `$${p.baseToken.symbol} · ${usd(p.marketCap ?? p.fdv)} MC · 1h ${Number(p.priceChange?.h1 || 0).toFixed(1)}% · ${usd(p.volume?.h1)} traded 1h` })) };
  return { axis: ['$10K', '$10M', 'NEWEST →'], rows: pairs.map(p => ({ id: p.pairAddress, sym: p.baseToken.symbol, x: 1 - lin((now - Number(p.pairCreatedAt || now)) / 3.6e6, 0, 24), y: lg(p.marketCap ?? p.fdv, 1e4, 1e7),
    r: 6 + Math.min(12, Math.sqrt((Number(p.liquidity?.usd) || 0) / 5000)), p: lin(p.priceChange?.h24, 0, 200), href: `https://dexscreener.com/solana/${p.pairAddress}`,
    tip: `$${p.baseToken.symbol} · ${usd(p.marketCap ?? p.fdv)} MC · liq ${usd(p.liquidity?.usd)} · 24h ${Number(p.priceChange?.h24 || 0).toFixed(0)}%` })) };
}

export function LiveTank({ start = 'new', compact = true }) {
  const [level, setLevel] = useState(() => { try { return localStorage.getItem('feeless.tank') || start; } catch { return start; } });
  const pick = k => { setLevel(k); try { localStorage.setItem('feeless.tank', k); } catch { /* private */ } };
  const L = LEVELS.find(x => x[0] === level) || LEVELS[0];
  const d = useRead(L[3], L[4]); const seen = useRef(new Set()); const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick(n => n + 1), 2000); return () => clearInterval(t); }, []);
  const { axis, rows } = bubbles(L[0], d);
  const fresh = new Set(rows.filter(r => !seen.current.has(r.id)).map(r => r.id)); rows.forEach(r => seen.current.add(r.id));
  const per = L[0] === 'new' ? d?.launchesPerMinute || [] : null;
  return <section className={`ltk ${compact ? 'is-compact' : ''}`} data-testid="live-tank">
    <header><i className={`ltk-dot ${rows.length ? 'is-on' : ''}`} /><b>LIVE INTAKE</b>
      <span className="ltk-levels" role="tablist" aria-label="Intake level">{LEVELS.map(([k, l, tip]) => <button key={k} type="button" role="tab" aria-selected={L[0] === k} className={L[0] === k ? 'is-on' : ''} onClick={() => pick(k)} data-tip={tip} data-testid={`ltk-${k}`}>{l}</button>)}</span>
      <span className="ltk-k m-num">{per ? `${d?.lastMinute ?? '—'} / min · ${per.reduce((a, x) => a + x, 0)} in 15m` : `${rows.length} coins`}</span></header>
    <div className="ltk-tank" aria-label={`${L[2]}: bubbles by real numbers`}>
      <i className="ltk-water" aria-hidden="true" /><i className="ltk-glass" aria-hidden="true" />
      <em className="ltk-tick" style={{ bottom: '8%' }}>{axis[0]}</em><em className="ltk-tick" style={{ bottom: '86%' }}>{axis[1]}</em><em className="ltk-now">{axis[2]}</em>
      {rows.map(r => <a key={r.id} href={r.href || undefined} target="_blank" rel="noopener noreferrer" className={`ltk-b ${fresh.has(r.id) ? 'is-new' : ''} ${r.p >= 0.6 ? 'is-hot' : ''}`}
        style={{ left: `${4 + r.x * 92}%`, bottom: `${8 + r.y * 80}%`, '--r': `${r.r}px`, '--p': r.p }} data-tip={r.tip}><span>{String(r.sym || '').slice(0, 6)}</span></a>)}
      {!rows.length ? <p className="ltk-wait">{d ? (L[0] === 'germ' ? 'No intake coin at its germ floor right now' : 'Waiting for the next coin…') : 'Connecting…'}</p> : null}
    </div>
  </section>;
}
