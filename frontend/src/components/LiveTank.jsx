import React, { useEffect, useRef, useState } from 'react';
import { apiUrl } from '../lib/api';
import { openWarRoom } from './WarRoomHost';
import '../styles/liveTank.css';

// 🫧 THE LIVE INTAKE (owner 2026-10-27: "the same intake from the agents tab in all the other spots — different water levels and colour dots, a
// simple legend"): the HQ › Agents intake band's look, site-wide. Five WATER LEVELS, each a lane, every dot a real coin from a real read:
//   GERM      the agents' intake coins sitting near their germ floor (−3…+10 %) — the buy zone            (top)
//   DESK      the agents' whole intake list (READY = gold)
//   TOP NEW   the newest pools with real money in them
//   TRENDING  pump.fun trending pools
//   NEW       every pump.fun launch the moment it happens (PumpPortal stream)                              (bottom)
// Across = live market cap (log $1K … $10M). Colour = what it's doing: rising · falling · hot (≥ +20 %, READY, or about to graduate) · at its germ
// floor · quiet. Tap a dot → its war room (a fresh launch opens on pump.fun). One read per level, shared by every tank on the page; paused hidden.
export const TANK_LEVELS = [
  ['germ', 'GERM', "The agents' intake coins near their germ floor (−3…+10 %) — the buy zone"],
  ['desk', 'DESK', "The agents' intake list — READY coins glow gold"],
  ['top', 'TOP NEW', 'The newest pools with real money in them'],
  ['trend', 'TRENDING', 'pump.fun trending pools'],
  ['new', 'NEW', 'Every pump.fun launch as it happens'],
];
export const TANK_LEGEND = [['up', 'rising'], ['dn', 'falling'], ['hot', 'hot · READY · graduating'], ['germ', 'at its germ floor'], ['q', 'quiet']];
const READS = { pump: ['/api/pump/pulse?limit=40', 4000], intake: ['/api/reputation/familia/intake', 30000], trend: ['/api/market/feed?kind=trending&chain=solana&page=1&scope=pump', 15000], top: ['/api/market/feed?kind=new&chain=solana&page=1', 20000] };
const TICKS = [[1e3, '$1K'], [1e4, '$10K'], [1e5, '$100K'], [1e6, '$1M'], [1e7, '$10M']];
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
// pure: market cap → across (log $1K … $10M)
export const capX = v => (Number(v) > 0 ? Math.max(0, Math.min(1, (Math.log10(Number(v)) - 3) / 4)) : 0);
const usd = v => (!(v > 0) ? '—' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v)}`);
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const tone = (move, hot) => (hot ? 'hot' : move == null || Math.abs(move) < 1 ? 'q' : move > 0 ? 'up' : 'dn');

// pure: every read → dots {id, sym, lane (index in TANK_LEVELS), x, tone, tip, href | pair}
export function tankDots({ pump, intake, trend, top } = {}) {
  const lane = k => TANK_LEVELS.findIndex(l => l[0] === k); const out = [];
  for (const l of (pump?.launches || []).slice(0, 40)) {
    const cp = Number(l.curveProgress) || 0;
    out.push({ id: `n-${l.mint}`, sym: l.symbol, lane: lane('new'), x: capX(l.marketCapUsd), tone: cp >= 80 ? 'hot' : cp >= 30 ? 'up' : 'q', href: `https://pump.fun/coin/${l.mint}`,
      tip: `$${l.symbol} · NEW · ${usd(l.marketCapUsd)} MC · ${Math.round(cp)}% up the bonding curve${l.devBuySol ? ` · dev ${Number(l.devBuySol).toFixed(2)} SOL` : ''}` });
  }
  for (const c of intake?.coins || []) {
    const pair = c.pair ? { chainId: 'solana', pairAddress: c.pair, baseToken: { address: c.mint, symbol: c.sym } } : null; const ready = /READY/i.test(c.status || '');
    const at = c.germ != null && c.germ >= -3 && c.germ <= 10;
    const base = { sym: c.sym, x: capX(c.mc), pair, href: c.pair ? null : `https://dexscreener.com/solana/${c.mint}` };
    out.push({ ...base, id: `d-${c.mint}`, lane: lane('desk'), tone: tone(c.ch, ready), tip: `$${c.sym} · DESK · ${c.status || ''} · ${usd(c.mc)} MC · 5m ${pc(c.ch)}` });
    if (at) out.push({ ...base, id: `g-${c.mint}`, lane: lane('germ'), tone: 'germ', tip: `$${c.sym} · ${pc(c.germ)} vs its germ floor — the agents' buy zone · ${usd(c.mc)} MC` });
  }
  const pairs = (rows, k, move, word) => (rows?.pairs || []).filter(p => p?.baseToken?.address).slice(0, 30).forEach(p => {
    const m = Number(move(p)); out.push({ id: `${k}-${p.pairAddress}`, sym: p.baseToken.symbol, lane: lane(k), x: capX(p.marketCap ?? p.fdv), tone: tone(m, m >= 20), pair: { ...p, chainId: p.chainId || 'solana' },
      tip: `$${p.baseToken.symbol} · ${word} · ${usd(p.marketCap ?? p.fdv)} MC · ${k === 'trend' ? '1h' : '24h'} ${pc(m)}` });
  });
  pairs(trend, 'trend', p => p.priceChange?.h1, 'TRENDING'); pairs(top, 'top', p => p.priceChange?.h24, 'TOP NEW');
  return out.filter(d => d.x > 0);
}
export const laneCounts = dots => TANK_LEVELS.map((_, i) => dots.filter(d => d.lane === i).length);

export function LiveTank({ compact = true, title = 'LIVE INTAKE' }) {
  const pump = useRead(...READS.pump); const intake = useRead(...READS.intake); const trend = useRead(...READS.trend); const top = useRead(...READS.top);
  const dots = tankDots({ pump, intake, trend, top }); const n = laneCounts(dots); const seen = useRef(new Set());
  const fresh = new Set(dots.filter(d => !seen.current.has(d.id)).map(d => d.id)); dots.forEach(d => seen.current.add(d.id));
  const open = d => { if (d.pair) openWarRoom(d.pair); else if (d.href) window.open(d.href, '_blank', 'noopener'); };
  return <section className={`ltk ${compact ? 'is-compact' : ''}`} style={{ '--n': TANK_LEVELS.length }} data-testid="live-tank">
    <header className="ltk-head"><i className={`ltk-dot ${dots.length ? 'is-on' : ''}`} /><b>🫧 {title}</b><small>five water levels · across = live MC · tap a coin</small>
      <span className="ltk-rate m-num" data-tip="pump.fun launches in the last minute · the last 15 minutes">{pump ? <><b>+{pump.lastMinute ?? 0}</b>/min · {(pump.launchesPerMinute || []).reduce((a, x) => a + x, 0)} in 15m</> : 'connecting…'}</span></header>
    <div className="ltk-body">
      <div className="ltk-field">
        {TANK_LEVELS.map(([k, l, tip], i) => <i key={k} className={`ltk-lane is-${k}`} style={{ '--l': i }} data-tip={tip}><small>{l}</small></i>)}
        {TICKS.map(([v, l]) => <em key={l} className="ltk-tick" style={{ left: `${capX(v) * 100}%` }}>{l}</em>)}
        {dots.map(d => <button key={d.id} type="button" className={`ltk-b t-${d.tone} ${fresh.has(d.id) ? 'is-new' : ''}`} style={{ left: `${d.x * 100}%`, '--l': d.lane }} onClick={() => open(d)}
          aria-label={d.tip} data-tip={d.tip}><i /></button>)}
        {!dots.length ? <p className="ltk-wait">{pump || intake ? 'The feeds are quiet — the next coin lands here' : 'Connecting to the feeds…'}</p> : null}
      </div>
      <ol className="ltk-funnel">{TANK_LEVELS.map(([k, l, tip], i) => <li key={k} className={`is-${k}`} data-tip={tip}><b className="m-num">{n[i]}</b><small>{l}</small></li>)}</ol>
    </div>
    <p className="ltk-legend" aria-label="Legend">{TANK_LEGEND.map(([k, l]) => <span key={k} className={`t-${k}`}><i />{l}</span>)}</p>
  </section>;
}
