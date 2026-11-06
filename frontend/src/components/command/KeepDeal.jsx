import React, { useState } from 'react';
import '../../styles/keepDeal.css';

// 🪙 THE DEAL (owner 2026-11-06, ledger: collective_stake.py). A send is a stake in the owner's auto-ranged pools. Its grade makes its boost: grade 87 is 1.87x. It may earn up to that many times what it sent, only from real pool profit. The boost is also its cut of every profit. Every number here is the live rule from the server.
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const boostX = grade => 1 + Math.max(0, Math.min(100, Number(grade) || 0)) / 100;
export const pointsFor = (sent, grade) => (Number(sent) || 0) * boostX(grade);
// Dollars lift the cut: $10 1x, $100 2x, $1,000 3x. Past the knee each 10x adds only part of a step. Same rule as size_of on the server.
export const sizeOf = (rules, usd) => { const n = Number(usd) || 0; if (n <= 0) return 0; const knee = rules?.kneeUsd ?? 1000; return Math.max(0.25, 1 + Math.log10(Math.min(n, knee) / 10)) + (n > knee ? Math.log10(n / knee) * ((rules?.sizeAbovePct ?? 50) / 100) : 0); };
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only stake what you can lose.</b> What it sends goes into the Collective's pools and does not come back as such. It earns only from real pool profit, up to its points, and pools can lose money. No profit means no pay, and taking rewards out is off for now. {rules?.collectivePoolPct != null ? `The Collective takes ${Math.round(rules.collectivePoolPct)}% of each profit.` : ''}</p>;
}
const Seg = ({ label, value, set, opts, fmt, id }) => <span className="kpd-seg"><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(o => <button key={o} type="button" className={value === o ? 'active' : ''} aria-pressed={value === o} onClick={() => set(o)} data-testid={`${id}-${o}`}>{fmt(o)}</button>)}</span></span>;
export function KeepDeal({ rules, sendUsd = null, testid = 'keep-deal' }) {
  const [sent, setSent] = useState(10); const [grade, setGrade] = useState(87); const s = sendUsd ?? sent; const x = boostX(grade); const cut = x * sizeOf(rules, s) * (rules?.cutPerX ?? 1);
  return <section className="kpd" data-testid={testid}><SendWarning rules={rules} />
    <div className="kpd-ctl">{sendUsd == null ? <Seg label="IT SENDS" value={sent} set={setSent} opts={[10, 100, 1000, 10000]} fmt={o => `$${o}`} id={`${testid}-send`} /> : null}<Seg label="THE GRADE" value={grade} set={setGrade} opts={[40, 70, 87, 100]} fmt={String} id={`${testid}-grade`} /></div>
    <ol className="kpd-flow" data-testid={`${testid}-flow`}>{[['STAKED IN THE POOLS', usd(s), 'All of it works in the pools the Collective opens'], ['ITS BOOST', `${x.toFixed(2)}x`, `Grade ${grade}: 1 + ${grade}/100`], ['BOOST POINTS', pointsFor(s, grade).toLocaleString(undefined, { maximumFractionDigits: 2 }), `What this proof holds: the most it can earn is ${usd(pointsFor(s, grade))}. Burn some to run at a bigger seat`], ['ITS SEAT', `${cut.toFixed(2)}%`, `Of every pool profit: ${x.toFixed(2)}x boost times ${sizeOf(rules, s).toFixed(2)}x for its dollars, and past $${(rules?.kneeUsd ?? 1000).toLocaleString()} that grows slowly`]].map(([k, v, t], i) => <li key={k} style={{ '--i': i }}><small>{k}</small><b className="m-num">{v}</b><span>{t}</span></li>)}</ol></section>;
}
