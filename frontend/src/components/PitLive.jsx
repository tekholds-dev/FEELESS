import React from 'react';
import { useLivePrices } from '../lib/livePrices';
import '../styles/pitReel.css';

// 📈 The Pit, live: a race line of both fighters' % since the bell (their paper books, one point a minute, ending at the live number)
// and a ticker of every coin on both cards moving on live prices. Transform/opacity animation only; static under fx-lite.
export function raceGeometry(a = [], b = [], w = 300, h = 64) {
  const all = [...a, ...b, 0];
  const lo = Math.min(...all); const hi = Math.max(...all); const span = Math.max(0.5, hi - lo);
  const n = Math.max(a.length, b.length, 2);
  const y = v => Math.round((h - 4 - ((v - lo) / span) * (h - 8)) * 10) / 10;
  const pts = arr => arr.map((v, i) => `${Math.round((i / (n - 1)) * w * 10) / 10},${y(v)}`).join(' ');
  return { a: pts(a), b: pts(b), zero: y(0), lo, hi };
}

export function RaceLine({ p }) {
  const a = [...(p.a.spark || []), p.a.now || 0]; const b = [...(p.b.spark || []), p.b.now || 0];
  if (a.length < 2 && b.length < 2) return null;
  const g = raceGeometry(a, b);
  const last = s => s.split(' ').pop().split(',').map(Number);
  const [ax, ay] = last(g.a); const [bx, by] = last(g.b);
  return <div className="pl-race" data-testid="pit-race" data-tip="The fight so far: each card's % since the bell, a point a minute, ending live">
    <div className="pl-plot"><svg viewBox="0 0 300 64" preserveAspectRatio="none" aria-hidden="true">
      <line x1="0" x2="300" y1={g.zero} y2={g.zero} className="pl-zero" />
      <polyline points={g.b} className="pl-b" /><polyline points={g.a} className="pl-a" />
    </svg>
    <i className="pl-dot a" style={{ left: `${(ax / 300) * 100}%`, top: `${(ay / 64) * 100}%` }} />
    <i className="pl-dot b" style={{ left: `${(bx / 300) * 100}%`, top: `${(by / 64) * 100}%` }} /></div>
    <small><b className="m-pos">{p.a.emoji} {(p.a.now || 0) >= 0 ? '+' : ''}{(p.a.now || 0).toFixed(2)}%</b><em>since the bell · {Math.max(a.length, b.length) - 1}m</em><b className="m-neg">{p.b.emoji} {(p.b.now || 0) >= 0 ? '+' : ''}{(p.b.now || 0).toFixed(2)}%</b></small>
  </div>;
}

export function CoinTicker({ legsA = [], legsB = [], nameA, nameB }) {
  const legs = [...legsA.map(l => ({ ...l, side: 'a' })), ...legsB.map(l => ({ ...l, side: 'b' }))].filter(l => l.pairAddress);
  const live = useLivePrices(legs.map(l => l.pairAddress));
  if (!legs.length) return null;
  const row = legs.map((l, i) => { const lp = live.get?.(l.pairAddress); const mv = lp ? lp.m5 : null;
    return <span key={`${l.side}-${l.pairAddress}-${i}`} className={`pl-tick s-${l.side}`} title={l.side === 'a' ? nameA : nameB}>
      <b>${l.symbol}</b><em className={`m-num ${mv == null ? 'm-dim' : mv >= 0 ? 'm-pos' : 'm-neg'}`} key={mv == null ? 'x' : mv.toFixed(2)}>{mv == null ? '—' : `${mv >= 0 ? '+' : ''}${mv.toFixed(2)}%`}</em></span>; });
  return <div className="pl-ticker" data-testid="pit-ticker" aria-label="Live coins on both cards (5 min move)"><span className="pl-live"><i />LIVE · 5M</span>
    <div className="pl-belt"><div className="pl-track">{row}{row}</div></div></div>;
}
