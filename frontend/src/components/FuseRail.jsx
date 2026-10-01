import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import { FuseCard } from './FuseCard';

// Discover rail: one prebuilt Fuse per strategy, bred from live pools right now (server caches 5 min). Swipe / scroll,
// drag a card to tilt, ⟲ to flip for why it won, "Use" loads it into the Lab (then ⚡ one-click). Cmd Ctr picks the size.
const TIP = { yield: 'Weights fee APR most: busy pools relative to their depth.', momentum: 'Leans on what moved up in the last 24h.',
  steady: 'Grade + calm prices first: deep pools, small swings.', degen: 'High APR + momentum, little care for calm. Biggest swings.' };

export function FuseRail({ call, onUse }) {
  const admin = Boolean(call);
  const [legs, setLegs] = useState(3); const [budget, setBudget] = useState(20); const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => {
    let alive = true; setD(null); setErr('');
    const path = `/fuses/prebuilt?legs=${legs}&budget=${budget}`;
    (admin ? call(path) : fetch(apiUrl(`/api/reputation${path}`)).then(r => r.json())).then(x => alive && setD(x)).catch(e => alive && setErr(e.message));
    return () => { alive = false; };
  }, [legs, budget, admin]); // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="frail" data-testid="fuse-rail">
    <header className="frail-head"><div><span className="m-label">🃏 PREBUILT FUSES · LIVE</span><small className="m-dim">Best basket per strategy, bred from live pools in the last 5 min. Drag to tilt · ⟲ to flip.</small></div>
      {admin && <div className="frail-ctl"><div className="m-seg" aria-label="Pools per fuse">{[3, 5, 8, 10].map(n => <button type="button" key={n} className={legs === n ? 'active' : ''} onClick={() => setLegs(n)} data-tip={`${n} pools per basket`}>{n}P</button>)}</div>
        <div className="m-seg" aria-label="Budget">{[5, 20, 100].map(n => <button type="button" key={n} className={budget === n ? 'active' : ''} onClick={() => setBudget(n)} data-tip="Budget changes the fee-drag + size-guard penalties">${n}</button>)}</div></div>}
    </header>
    <div className="frail-track">{err ? <p className="m-dim">{err}</p> : !d ? Array.from({ length: 4 }, (_, i) => <div key={i} className="frail-ghost" />)
      : (d.cards || []).map((c, i) => <article key={c.style} className="frail-item" style={{ animationDelay: `${i * 80}ms` }}>
        <FuseCard c={c} style={c.style} rank={i} budget={d.budgetUsd} />
        <div className="frail-meta" data-tip={TIP[c.style]}><b>{c.style}</b>{c.arena ? <span className={c.arena.avgPct >= 0 ? 'm-pos' : 'm-neg'}>arena {c.arena.avgPct >= 0 ? '+' : ''}{c.arena.avgPct}% · {c.arena.runs} runs</span> : <span className="m-dim">not yet in arena</span>}</div>
        <button type="button" className="m-btn primary m-go" onClick={() => onUse?.(c.legs, d.solUsd ? d.budgetUsd / d.solUsd : null)} data-testid={`frail-use-${c.style}`}>Use this · ${d.budgetUsd}</button>
      </article>)}</div>
  </section>;
}
