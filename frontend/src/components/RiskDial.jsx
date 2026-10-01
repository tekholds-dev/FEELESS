import React from 'react';
import { RISK_DIALS, useDialProof } from '../lib/riskDial';
import '../styles/fuseLab.css';

// 🎚 One dial instead of ten settings. Each option shows how that dial did on the Arena's auto paper cards (24h) so you pick
// with evidence. `value` 'custom' = hand-tuned. Used in the Lab card plan, My cards and (engine variant) Cmd Ctr.
const pc = v => `${v >= 0 ? '+' : ''}${(v || 0).toFixed(1)}%`;

export function RiskDial({ value, onChange, dials = RISK_DIALS, proofs, testid = 'risk', noProof = false }) {
  const live = useDialProof();
  const pr = proofs === undefined ? live : proofs;
  return <div className="rdial" role="radiogroup" aria-label="Risk dial" data-testid={`${testid}-dial`}>
    {Object.entries(dials).map(([k, d]) => { const p = pr?.[k]; return <button key={k} type="button" role="radio" aria-checked={value === k} className={`rdial-opt r-${k} ${value === k ? 'active' : ''}`}
      onClick={() => onChange(k)} data-tip={d.why} data-testid={`${testid}-${k}`}>
      <b>{d.label}</b>{noProof ? <small className="m-dim">{d.why.split(',')[0]}</small> : p?.rounds ? <small className={p.avgPct >= 0 ? 'm-pos' : 'm-neg'}>{pc(p.avgPct)} · {p.winRate}% won{p.lit ? ' · 🔥' : ''}</small> : <small className="m-dim">proving…</small>}</button>; })}
    {value === 'custom' && <span className="rdial-custom" data-tip="You tuned the coins by hand. Pick a dial to reset everything to it.">✎ Custom</span>}
  </div>;
}

// 🏟 Which dial is winning: the Arena's auto paper cards — every round played with each dial's TP/SL. Before configs go auto
// live, this is the evidence. Used on the Arena tab and in Cmd Ctr › ⚔ Arena.
export function DialBoard({ dials }) {
  if (!dials) return null;
  const best = Object.entries(dials).filter(([, p]) => p.rounds).sort((a, b) => b[1].avgPct - a[1].avgPct)[0]?.[0];
  return <section className="m-card dboard" data-testid="dial-board"><header><span className="m-label">🎚 AUTO PAPER CARDS · WHICH DIAL WINS</span>
    <small className="m-dim">every runner round also played with each dial's take-profit / stop-loss on real prices (24h). Configs go auto live only after this proves it.</small></header>
    <div className="dboard-row">{Object.entries(dials).map(([k, p]) => <div key={k} className={`dboard-tile r-${k} ${k === best ? 'is-best' : ''} ${p.lit ? 'is-lit' : ''}`} data-tip={p.why}>
      <b>{p.label || RISK_DIALS[k]?.label}</b><em className={`m-num ${p.avgPct >= 0 ? 'm-pos' : 'm-neg'}`}>{p.rounds ? pc(p.avgPct) : '—'}</em>
      <small className="m-dim">{p.rounds ? `${p.rounds} rounds · ${p.winRate}% won · $1 → $${(p.per1 || 1).toFixed(2)}` : 'first rounds dealing'}</small>
      {p.lit && <span className="dboard-lit">🔥 proven</span>}</div>)}</div></section>;
}
