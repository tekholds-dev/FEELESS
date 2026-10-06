import React, { useEffect, useRef, useState } from 'react';
import '../styles/cardPops.css';

const POP = { compound: ['♻', 'COMPOUND'], skim: ['💰', 'PROFIT'], 'lock-bank': ['🏦', 'BANKED'], 'peak-sell': ['🏔', 'OFF PEAK'], tp: ['💰', 'PROFIT'], recycle: ['♻', 'RECYCLE'], ride: ['🔒', 'LOCKED'] };
const key = e => `${Math.round((e.at || 0) * 10)}-${e.kind}-${e.symbol || ''}-${e.n || 0}`;
const money = v => (v >= 1 ? `$${v.toFixed(2)}` : `$${v.toFixed(2)}`);

// What pops off the card for the events that arrived since `seen` (a Set of keys): money going back to work or being banked.
export function popsFrom(events, seen) {
  const out = [];
  for (const e of events || []) {
    const p = POP[e.kind]; const k = key(e);
    if (!p || seen.has(k)) continue;
    const usd = Number(e.lastUsd ?? e.usd) || 0;   /* compounds fold into one running line: pop the LATEST amount, not the half-hour total */
    if (e.kind !== 'ride' && usd < 0.01) continue;
    out.push({ k, ico: p[0], label: p[1], text: e.kind === 'ride' ? `$${e.symbol}` : `+${money(usd)}`, symbol: e.symbol || '' });
  }
  return out.slice(-3);
}

// Coins charging toward their lock / take-profit line: within the last quarter of the way there (not riding, not waiting on a buy).
export function nearTargets(legs, cfg, cardTp) {
  const lock = Number(cfg?.rideAt) || 0;
  return (legs || []).map(l => { const target = lock > 0 ? lock : Number(l.tp) || Number(cardTp) || 0; const g = Number(l.pnlPct);
    if (!(target > 0) || !Number.isFinite(g) || l.ride || l.frozen || l.buying || !(l.usd > 0) || g < target * 0.75 || g >= target) return null;
    return { symbol: l.symbol, gain: g, target, fill: Math.max(0, Math.min(1, g / target)), kind: lock > 0 ? 'lock' : 'take profit' }; }).filter(Boolean).sort((a, b) => b.fill - a.fill).slice(0, 2);
}

// ✨ The card reacts like a game piece: a number floats up when money compounds or profit is taken (+$0.25 ♻), and a coin close
// to its lock / take-profit line charges up at the foot of the card. Overlay only — transform / opacity, off in lite mode.
export function CardPops({ events, legs, cfg, tp }) {
  const seen = useRef(null);
  const [pops, setPops] = useState([]);
  useEffect(() => {
    if (!seen.current) { seen.current = new Set((events || []).map(key)); return undefined; }   // nothing bursts for what was already there
    const fresh = popsFrom(events, seen.current);
    (events || []).forEach(e => seen.current.add(key(e)));
    if (!fresh.length) return undefined;
    setPops(p => [...p, ...fresh].slice(-4));
    const t = setTimeout(() => setPops(p => p.filter(x => !fresh.some(f => f.k === x.k))), 2400);
    return () => clearTimeout(t);
  }, [events]);
  const near = nearTargets(legs, cfg, tp);
  if (!pops.length && !near.length) return null;
  return <div className="cpop" aria-hidden data-testid="card-pops">
    {pops.map((p, i) => <span key={p.k} className={`cpop-num is-${p.label === 'COMPOUND' || p.label === 'RECYCLE' ? 'in' : p.label === 'LOCKED' ? 'lock' : 'out'}`} style={{ '--i': i }} data-testid="card-pop"><b>{p.text}</b><small>{p.ico} {p.label}</small></span>)}
    {near.length > 0 && <div className="cpop-near" data-testid="card-near">{near.map(n => <span key={n.symbol} className="cpop-charge"><i style={{ transform: `scaleX(${n.fill})` }} /><b>⚡ ${n.symbol} +{n.gain.toFixed(0)}%</b><small>{n.kind} +{n.target}%</small></span>)}</div>}
  </div>;
}
