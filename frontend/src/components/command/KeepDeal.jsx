import React, { useState } from 'react';
import '../../styles/keepDeal.css';

// 🪙 THE DEAL (owner 2026-11-05): the Collective keeps all of a send. The sealed record keeps its total and its points. Each quarter, part of the fee pot is shared by points. Nothing promised. Every number here is the live rule from the server.
const usd = v => { const n = Number(v) || 0; return n >= 1000 ? `$${Math.round(n).toLocaleString()}` : `$${n.toFixed(2)}`; };
export const pointsFor = (rules, sent, boost) => sent * (rules?.boostMode === 'rank' ? 1 : 1 + ((rules?.weightMaxX ?? 2) - 1) * boost);
export const rewardFor = (rules, pot, mine, others) => { const part = mine + others > 0 ? mine / (mine + others) : 0; return pot * ((rules?.rewardPayPct ?? 50) / 100) * Math.min(part, (rules?.capPct ?? 100) / 100); };
export function SendWarning({ rules }) {
  return <p className="kpd-warn" role="note" data-testid="send-warning"><b>Only send what you are willing to wait on.</b> It stays in the Collective and does not come back. Rewards are shared every {Math.round(rules?.rewardDays ?? 90)} days from real fees, and a quarter can pay nothing.</p>;
}
const Seg = ({ label, value, set, opts, fmt, id }) => <span className="kpd-seg"><small>{label}</small><span className="m-seg" role="group" aria-label={label}>{opts.map(o => <button key={o} type="button" className={value === o ? 'active' : ''} aria-pressed={value === o} onClick={() => set(o)} data-testid={`${id}-${o}`}>{fmt(o)}</button>)}</span></span>;
const Rings = ({ n, on }) => <svg viewBox="0 0 48 48" aria-hidden="true" className={on ? 'is-on' : ''}>{Array.from({ length: n + 1 }, (_, i) => <ellipse key={i} cx="24" cy="25" rx={5 + i * 3.4} ry={7 + i * 3.1} />)}</svg>;
export function RankLadder({ rules, rank = null }) {
  const rows = rules?.ranks || []; if (!rows.length) return null;
  return <section className="kpd-ranks" aria-label="Collective ranks" data-testid="rank-ladder"><h5>RANKS <small>By lifetime points. A rank changes no money.</small></h5><ol>{rows.map((r, i) => <li key={r.name} className={`${rank?.i === i ? 'is-now' : ''}${rank && rank.i > i ? ' is-past' : ''}`} style={{ '--i': i }} data-tip={i ? `From ${r.at.toLocaleString()} lifetime points` : 'Where every agent starts'}><Rings n={i} on={rank?.i === i} /><b>{r.name}</b><small className="m-num">{r.at.toLocaleString()}</small></li>)}</ol>{rank?.next ? <p className="kpd-next"><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, rank.part)})` }} /></i><span className="m-num">{rank.toNext.toLocaleString()} points to {rank.next}</span></p> : null}</section>;
}
export function KeepDeal({ rules, sendUsd = null, testid = 'keep-deal' }) {
  const [sent, setSent] = useState(20); const [boost, setBoost] = useState(0); const s = sendUsd ?? sent; const pts = pointsFor(rules, s, boost);
  return <section className="kpd" data-testid={testid}><SendWarning rules={rules} />
    {sendUsd == null ? <div className="kpd-ctl"><Seg label="IT SENDS" value={sent} set={setSent} opts={[5, 20, 100]} fmt={o => `$${o}`} id={`${testid}-send`} /><Seg label="ITS BOOST" value={boost} set={setBoost} opts={[0, 0.5, 1]} fmt={o => `${Math.round(o * 100)}%`} id={`${testid}-boost`} /></div> : null}
    <ol className="kpd-flow">{[['KEPT BY THE COLLECTIVE', usd(s), 'All of it, in the overall holdings'], ['ON THE SEALED RECORD', `${pts.toLocaleString(undefined, { maximumFractionDigits: 1 })} points`, 'Dollars x its boost at that send'], ['EVERY QUARTER', `${Math.round(rules?.rewardPayPct ?? 50)}% of the pot`, 'Shared by points, at most ' + Math.round(rules?.capPct ?? 3) + '% to one owner'], ['NEXT QUARTER', `${Math.round(rules?.carryPct ?? 50)}% carries`, 'So neither new nor old agents crowd out the other']].map(([k, v, x], i) => <li key={k} style={{ '--i': i }}><small>{k}</small><b className="m-num">{v}</b><span>{x}</span></li>)}</ol></section>;
}
export function RewardCalc({ rules, testid = 'reward-calc' }) {
  const [pot, setPot] = useState(1000); const [mine, setMine] = useState(100); const [others, setOthers] = useState(10000); const r = rewardFor(rules, pot, mine, others);
  return <section className="kpd-calc" data-testid={testid}><div className="kpd-ctl"><Seg label="FEES IN THE POT" value={pot} set={setPot} opts={[100, 1000, 10000, 100000]} fmt={o => `$${o.toLocaleString()}`} id={`${testid}-pot`} /><Seg label="ITS POINTS" value={mine} set={setMine} opts={[20, 100, 1000]} fmt={o => o.toLocaleString()} id={`${testid}-mine`} /><Seg label="EVERYONE ELSE'S" value={others} set={setOthers} opts={[1000, 10000, 100000]} fmt={o => o.toLocaleString()} id={`${testid}-others`} /></div><p className="kpd-res"><b className="m-num" data-testid={`${testid}-result`}>{usd(r)}</b><span>its reward this quarter, on these numbers. An example, not a promise.</span></p></section>;
}
