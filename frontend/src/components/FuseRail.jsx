import React, { useEffect, useState } from 'react';
import NumInput from './NumInput';
import { apiUrl } from '../lib/api';
import { FuseCard } from './FuseCard';

// Discover rail: one prebuilt Fuse per strategy, bred from live pools right now (server caches 5 min). Swipe / scroll,
// drag a card to tilt, ⟲ to flip for why it won, "Use" loads it into the Lab (then ⚡ one-click). HQ picks the size.
const TIP = { yield: 'Weights fee APR most: busy pools relative to their depth.', momentum: 'Leans on what moved up in the last 24h.',
  steady: 'Grade + calm prices first: deep pools, small swings.', degen: 'High APR + momentum, little care for calm. Biggest swings.',
  dip: 'Buy the dip: coins down on the day whose buyers are back (1h green, 55%+ buys).', meta: 'Pump meta: DEX-paid profiles + momentum + real flow.' };

export function FuseRail({ call, onUse }) {
  const admin = Boolean(call);
  const [legs, setLegs] = useState(3); const [budget, setBudget] = useState(20); const [d, setD] = useState(null); const [err, setErr] = useState('');
  const [custom, setCustom] = useState('');   // any $ amount; breeding uses the nearest bucket, Fuse in uses this exact amount
  const amount = Number(custom) > 0 ? Number(custom) : budget;
  const [asked, setAsked] = useState(amount);   // typing is debounced (250ms) before it re-breeds
  useEffect(() => { const t = setTimeout(() => setAsked(amount), 250); return () => clearTimeout(t); }, [amount]);
  useEffect(() => {
    let alive = true; setD(null); setErr('');
    const path = `/fuses/prebuilt?legs=${legs}&budget=${asked}`;
    (admin ? call(path) : fetch(apiUrl(`/api/reputation${path}`)).then(r => r.json())).then(x => alive && setD(x)).catch(e => alive && setErr(e.message));
    return () => { alive = false; };
  }, [legs, asked, admin]); // eslint-disable-line react-hooks/exhaustive-deps
  return <section className="frail" data-testid="fuse-rail">
    <header className="frail-head"><div><span className="m-label">🃏 PREBUILT FUSES · LIVE</span><small className="m-dim">Best basket per strategy, bred from live pools in the last 5 min. Drag to tilt · ⟲ to flip.</small></div>
      <div className="frail-ctl"><div className="m-seg" aria-label="Card size" data-testid="frail-budget">{[1, 20, 100].map(n => <button type="button" key={n} className={!custom && budget === n ? 'active' : ''} onClick={() => { setBudget(n); setCustom(''); }} data-tip={`Breed $${n} cards — fee drag + size guard are scored for that size`}>${n}</button>)}</div>
        <label className="frail-custom" data-tip="Any amount. Cards are bred for the nearest size; Fuse in uses exactly this."><span>$</span><NumInput className="m-input m-num" inputMode="decimal" placeholder="custom" value={custom} onChange={e => setCustom(e.target.value.replace(/[^0-9.]/g, ''))} data-testid="frail-custom" /></label>
      {admin && <div className="frail-admin"><div className="m-seg" aria-label="Pools per fuse">{[3, 5, 8, 12].map(n => <button type="button" key={n} className={legs === n ? 'active' : ''} onClick={() => setLegs(n)} data-tip={`${n} pools per basket`}>{n}P</button>)}</div></div>}</div>
    </header>
    <div className="frail-track">{err ? <p className="m-dim">{err}</p> : !d ? Array.from({ length: 4 }, (_, i) => <div key={i} className="frail-ghost" />)
      : (d.cards || []).map((c, i) => <article key={c.style} className="frail-item" style={{ animationDelay: `${i * 80}ms` }}>
        <FuseCard c={c} style={c.style} rank={i} budget={amount} />
        <div className="frail-meta" data-tip={TIP[c.style]}><b>{c.style}</b>{c.arena ? <span className={c.arena.avgPct >= 0 ? 'm-pos' : 'm-neg'}>arena {c.arena.avgPct >= 0 ? '+' : ''}{c.arena.avgPct}% · {c.arena.runs} runs</span> : <span className="m-dim">not yet in arena</span>}</div>
        <button type="button" className="m-btn primary m-go" onClick={() => onUse?.(c.legs, d.solUsd ? amount / d.solUsd : null)} data-testid={`frail-use-${c.style}`}>Use this · ${amount}</button>
      </article>)}</div>
    {d?.retired?.length > 0 && <p className="m-note" data-testid="frail-retired" data-tip="The arena retires a strategy once its typical $5 run AND its outlier-proof average are both below 0. It still gets one test run a day and comes back by itself when it wins again.">☠ Retired for losing in the arena: {d.retired.join(' · ')}</p>}
  </section>;
}
