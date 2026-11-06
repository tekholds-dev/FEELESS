import React, { useState } from 'react';
import '../../styles/keepDeal.css';

// 🪙 THE DEAL (owner 2026-11-06, ledger: collective_stake.py). A send is a stake in the owner's auto-ranged pools. Its grade makes its boost: grade 87 is 1.87x. It may earn up to that many times what it sent, only from real pool profit. The boost is also its cut of every profit. Every number here is the live rule from the server.
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const boostX = grade => 1 + Math.max(0, Math.min(100, Number(grade) || 0)) / 100;
export const pointsFor = (sent, grade) => (Number(sent) || 0) * boostX(grade);
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only stake what you can lose.</b> What it sends goes into the Collective's pools and does not come back as such. It earns only from real pool profit, up to its points, and pools can lose money. No profit means no pay, and taking rewards out is off for now. {rules?.collectivePoolPct != null ? `The Collective takes ${Math.round(rules.collectivePoolPct)}% of each profit.` : ''}</p>;
}
const Seg = ({ label, value, set, opts, fmt, id }) => <span className="kpd-seg"><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(o => <button key={o} type="button" className={value === o ? 'active' : ''} aria-pressed={value === o} onClick={() => set(o)} data-testid={`${id}-${o}`}>{fmt(o)}</button>)}</span></span>;
export function KeepDeal({ rules, sendUsd = null, testid = 'keep-deal' }) {
  const [sent, setSent] = useState(10); const [grade, setGrade] = useState(87); const s = sendUsd ?? sent; const x = boostX(grade); const cut = x * (rules?.cutPerX ?? 1);
  return <section className="kpd" data-testid={testid}><SendWarning rules={rules} />
    <div className="kpd-ctl">{sendUsd == null ? <Seg label="IT SENDS" value={sent} set={setSent} opts={[10, 50, 200]} fmt={o => `$${o}`} id={`${testid}-send`} /> : null}<Seg label="THE GRADE" value={grade} set={setGrade} opts={[40, 70, 87, 100]} fmt={String} id={`${testid}-grade`} /></div>
    <ol className="kpd-flow" data-testid={`${testid}-flow`}>{[['STAKED IN THE POOLS', usd(s), 'All of it works in the pools the Collective opens'], ['ITS BOOST', `${x.toFixed(2)}x`, `Grade ${grade}: 1 + ${grade}/100`], ['POINTS', pointsFor(s, grade).toLocaleString(undefined, { maximumFractionDigits: 2 }), `The most it can ever earn: ${usd(pointsFor(s, grade))}. Each dollar paid takes one off`], ['ITS CUT', `${cut.toFixed(2)}%`, 'Of every pool profit, while it has points']].map(([k, v, t], i) => <li key={k} style={{ '--i': i }}><small>{k}</small><b className="m-num">{v}</b><span>{t}</span></li>)}</ol></section>;
}
