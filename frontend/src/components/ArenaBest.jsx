import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import '../styles/arenaBest.css';

// 🏆 BEST SETTINGS FOR THE ARENA (owner, 2026-10-22): which card styles score best in the Arena (median of its own fitness score, how many cards
// back it), what the TOP QUARTER of cards share vs the rest (coins per card · biggest leg · % in majors), and the three best cards. Evidence from
// the Arena's own record (GET /fuses/arena-best, 5 min cache) — never a promise.
export function ArenaBest() {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; fetch(apiUrl('/api/reputation/fuses/arena-best')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {}); return () => { on = false; }; }, []);
  if (!d?.n) return null;
  const max = Math.max(1, ...d.styles.map(s => s.medFit));
  const row = (label, k, unit = '') => <li key={k}><em>{label}</em><b className="up">{d.top?.[k]}{unit}</b><b>{d.rest?.[k] ?? '—'}{unit}</b></li>;
  return <section className="abs m-card" data-testid="arena-best">
    <header><b>🏆 BEST SETTINGS</b><small>from {d.n} scored Arena cards</small></header>
    <div className="abs-grid">
      <ol className="abs-styles">{d.styles.map((s, i) => <li key={s.style} style={{ '--i': i }} data-tip={`${s.style}: median Arena score ${s.medFit} across ${s.n} cards`}>
        <span>{s.style}</span><u aria-hidden="true"><s style={{ transform: `scaleX(${s.medFit / max})` }} /></u><b className="m-num">{s.medFit}</b><small>{s.n}</small></li>)}</ol>
      <ul className="abs-cmp"><li className="abs-h"><em /><b>TOP 25 %</b><b>REST</b></li>{row('score', 'fit')}{row('coins', 'legs')}{row('biggest leg', 'maxW', '%')}{row('in majors', 'majorW', '%')}</ul>
    </div>
    <div className="abs-cards">{d.cards.map((c, i) => <span key={c.id || i} style={{ '--i': i }} data-tip={`${c.style} · score ${c.fitness}`}><b>#{i + 1} · {c.fitness}</b>
      <small>{c.legs.map(l => `${l.symbol} ${Math.round(l.weight)}%`).join(' · ')}</small></span>)}</div>
  </section>;
}
