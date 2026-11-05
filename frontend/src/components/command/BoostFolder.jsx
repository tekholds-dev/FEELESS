import React, { useEffect, useRef, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { SplitFlow, money } from './SplitFlow';
import { BoostCoin } from './DeskShell';
import '../../styles/boosts.css';

// 🪙 THE BOOST FOLDER (owner 2026-11-04): the live count of what its proofs have earned, what is locked, and what its boost is doing right now. The number comes from the server's ledger: the page only ticks it between reads.
export function useAgentPool(cat, work, every = 30000) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) Promise.resolve().then(() => work(cat.id, { op: 'pool' })).then(j => { if (on && j) setD({ ...j, readAt: Date.now() }); }).catch(() => {}); }; go(); const t = setInterval(go, every); return () => { on = false; clearInterval(t); }; }, [cat?.id, work, every]);
  return d;
}
export function LiveCount({ pool, readAt, testid = 'bst-count' }) {
  const el = useRef(null); const base = Number(pool?.owedUsd) || 0; const rate = Number(pool?.ratePerSecUsd) || 0; const at = readAt || 0;
  useEffect(() => { const paint = () => { if (el.current) el.current.textContent = `$${(base + rate * Math.max(0, Date.now() - at) / 1000).toFixed(8)}`; }; paint(); if (!rate) return undefined; const t = setInterval(() => { if (!document.hidden) paint(); }, 200); return () => clearInterval(t); }, [base, rate, at]);
  return <b ref={el} className="bst-num m-num" data-testid={testid}>$0.00000000</b>;
}
function Lever({ k, from, to, now, text, tip }) {
  const off = Math.abs(to - from) < 1e-9; const part = off ? 0 : Math.max(0, Math.min(1, (now - from) / (to - from)));
  return <div className="bst-lever" data-tip={tip} data-testid={`bst-lever-${k}`}><small>{k}</small><b className="m-num">{text}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, part)})` }} /></i></div>;
}
export function BoostFolder({ cat, work }) {
  const d = useAgentPool(cat, work);
  if (!d) return <p className="dsk-note">reading its count…</p>;
  const p = d.pool || {}; const r = d.rules || {}; const lv = p.levers || {}; const b = Number(d.boostNow) || 0; const rank = r.boostMode === 'rank'; const empty = p.empty || !(p.lockedUsd || p.owedUsd);
  const days = r.halfLifeDays + (r.halfLifeMinDays - r.halfLifeDays) * (rank ? 0 : b); const split = r.splitPct + (r.splitMaxPct - r.splitPct) * (rank ? 0 : b); const weight = 1 + (r.weightMaxX - 1) * (rank ? 0 : b);
  return <div className="bst" data-testid="bst-folder">
    <header className="bst-hero"><span className="bst-coin-big"><BoostCoin /></span>
      <div><small>EARNED FROM PROOFS SENT</small><LiveCount pool={p} readAt={d.readAt} />
        <p>{empty ? 'Its count starts with its first proof sent to the Collective.' : `Counting up from ${money(p.lockedUsd)} locked.`}</p></div>
      <span className="bst-off" data-tip="Its earnings keep counting. Taking them out is switched off for now, and nothing here can be spent yet." data-testid="bst-withdraw-off">WITHDRAWALS OFF</span></header>
    <div className="bst-tiles">{[['LOCKED', money(p.lockedUsd), 'Still releasing. It can\'t be pulled out early.'], ['SENT', money(p.sentUsd), 'What its proofs have sent, at today\'s price'], ['FROM THE FEE POT', money(p.earnedUsd), 'What the fee pot has added to its lock so far. It rises and falls with fees.'], ['BOOST POINTS', d.points ?? 0, 'Earned by verified sends and proved convos. They fade if proofs stop.'], ['PROOFPRINT', d.printLevel ?? 0, 'Graded from its real results. A stronger print makes the same points worth more.']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div>
    <section className="bst-levers" aria-label="What its boost does now"><h4><Ic3 e="⚡" /> BOOST {rank ? 'RANKS ONLY' : `${weight.toFixed(2)}x`}</h4>
      <Lever k="SPLIT" from={r.splitPct} to={r.splitMaxPct} now={split} text={`${split.toFixed(1)} / ${(100 - split).toFixed(1)}`} tip={`What releases goes to the agent first. A full boost moves it from ${r.splitPct}/${100 - r.splitPct} to ${r.splitMaxPct}/${100 - r.splitMaxPct}.`} />
      <Lever k="SPEED" from={r.halfLifeDays} to={r.halfLifeMinDays} now={days} text={`half in ${days.toFixed(0)}d`} tip={`How fast it comes back. A full boost cuts it from ${r.halfLifeDays} to ${r.halfLifeMinDays} days for half.`} />
      <Lever k="FEE POT" from={1} to={r.weightMaxX} now={weight} text={`${weight.toFixed(2)}x`} tip={`Its weight in the fee pot, up to ${r.weightMaxX}x. A bigger part of the pot, which pays the same total.`} /></section>
    {d.boostLog?.length ? <ol className="clx-log bst-log">{d.boostLog.map(x => <li key={x.ref}><em className="m-num">+{x.pts}</em>{x.why}</li>)}</ol> : null}
    <details className="bst-how" open={empty}><summary data-tip="Where a proof's money goes">How the split works</summary><SplitFlow rules={r} boost={null} testid="bst-split" /></details>
  </div>;
}
