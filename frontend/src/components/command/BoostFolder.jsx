import React, { Suspense, lazy, useEffect, useRef, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { PLAN_NAMES, PlanPicker, SplitFlow, money } from './SplitFlow';
import { BoostCoin } from './DeskShell';
import '../../styles/boosts.css';

const Coin3D = lazy(() => import('./Coin3D'));

// 🪙 THE BOOST FOLDER (owner 2026-11-04): the live count of what its proofs have earned, what is locked, and what its boost is doing right now. The number comes from the server's ledger: the page only ticks it between reads.
export function useAgentPool(cat, work, every = 30000) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; let first = true; const go = () => { if (first || !document.hidden) { first = false; Promise.resolve().then(() => work(cat.id, { op: 'pool' })).then(j => { if (on && j) setD({ ...j, readAt: Date.now() }); }).catch(() => {}); } }; go(); const t = setInterval(go, every); return () => { on = false; clearInterval(t); }; }, [cat?.id, work, every]);
  return d;
}
export function LiveCount({ pool, readAt, testid = 'bst-count' }) {
  const el = useRef(null); const base = Number(pool?.owedUsd) || 0; const rate = Number(pool?.ratePerSecUsd) || 0; const at = readAt || 0;
  useEffect(() => { const paint = () => { if (el.current) el.current.textContent = `$${(base + rate * Math.max(0, Date.now() - at) / 1000).toFixed(8)}`; }; paint(); if (!rate) return undefined; const t = setInterval(() => { if (!document.hidden) paint(); }, 200); return () => clearInterval(t); }, [base, rate, at]);
  return <b ref={el} className="bst-num m-num" data-testid={testid}>$0.00000000</b>;
}
function Lever({ k, part, text, tip }) {
  return <div className="bst-lever" data-tip={tip} data-testid={`bst-lever-${k}`}><small>{k}</small><b className="m-num">{text}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, part))})` }} /></i></div>;
}
// One send: exactly how much, by what date, how far along, and points that bring the date closer.
function Stream({ r, rules, left, onSpend, busy }) {
  const now = Date.now() / 1000; const v = r.plan === 'vault'; const total = Math.max(1, (r.end || now) - (r.start || r.at)); const part = v ? 1 : Math.min(1, (now - (r.start || r.at)) / total); const days = v ? null : Math.max(0, (r.end - now) / 86400); const canSpend = !v && !r.done && left >= 1; const cost = Math.min(Math.floor(left), rules.ptsPerDay || 10);
  return <li className={`bst-stream${r.done ? ' is-done' : ''}${v ? ' is-vault' : ''}`} data-testid={`bst-stream-${r.id}`}><div className="bst-s-top"><span><b>{r.name || 'Proof'}{r.sym ? ` · $${r.sym}` : ''}</b><small>{PLAN_NAMES[r.plan]?.[0] || r.plan} · sent {money(r.sentUsd)}</small></span>
      <span className="bst-s-amt">{v ? <><b className="m-num">{money(r.vaultUsd)}</b><small>in the Vault for good</small></> : <><b className="m-num">{money(r.backUsd)}</b><small>{r.done ? 'all back' : `back by ${new Date(r.end * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`}</small></>}</span></div>
    <i className="bst-s-bar" aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.01, part)})` }} /></i>
    <div className="bst-s-foot"><small>{v ? 'Earns from the fee pot while it keeps sending' : r.done ? 'Finished' : `${money(r.soFarUsd)} back so far · ${days < 1 ? 'under a day' : `${Math.ceil(days)} days`} left`}</small>{canSpend ? <button type="button" className="m-btn" disabled={busy} onClick={() => onSpend(r.id, cost)} data-tip={`Spend ${cost} points to bring this date ${(cost / (rules.ptsPerDay || 10)).toFixed(1)} days closer`} data-testid={`bst-spend-${r.id}`}>⚡ {(cost / (rules.ptsPerDay || 10)).toFixed(1)}d sooner</button> : null}{r.sig ? <a href={`https://solscan.io/tx/${r.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Its transaction on Solscan">Tx ↗</a> : null}</div></li>;
}
export function BoostFolder({ cat, work }) {
  const d0 = useAgentPool(cat, work); const [over, setOver] = useState(null); const [busy, setBusy] = useState(false); const [err, setErr] = useState(''); const d = d0 && over ? { ...d0, ...over } : d0;
  if (!d) return <p className="dsk-note">reading its count…</p>;
  const p = d.pool || {}; const r = d.rules || {}; const b = Number(d.boostNow) || 0; const rank = r.boostMode === 'rank'; const empty = p.empty || !(p.lockedUsd || p.owedUsd || p.vaultUsd); const weight = 1 + ((r.weightMaxX || 2) - 1) * (rank ? 0 : b); const backPlus = (r.boostBackPts || 0) * (rank ? 0 : b); const left = Number(d.pointsLeft) || 0; const plan = d.plan || p.plan || 'month';
  const act = async (op, body) => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op, ...body }); setOver(x => ({ ...(x || {}), ...j, ...(j.plan ? { plan: j.plan } : null) })); } catch (e) { setErr(e.message || 'Not saved'); } setBusy(false); };
  const next = p.nextEnd ? new Date(p.nextEnd * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : null;
  return <div className="bst" data-testid="bst-folder">
    <header className="bst-hero"><span className="bst-coin-big"><Suspense fallback={<BoostCoin />}><Coin3D energy={p.ratePerSecUsd ? 1 : 0.45} size={132} /></Suspense></span>
      <div><small>EARNED FROM PROOFS SENT</small><LiveCount pool={p} readAt={d.readAt} />
        <p>{empty ? 'Its count starts with its first proof sent to the Collective.' : <><b className="m-num">{money(p.backLeftUsd)}</b> still coming{next ? `, next finishing ${next}` : ''}.</>}</p></div>
      <span className="bst-off" data-tip="Its earnings keep counting. Taking them out is switched off for now, and nothing here can be spent yet." data-testid="bst-withdraw-off">WITHDRAWALS OFF</span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <section className="bst-sec"><h4>ITS NEXT SENDS FOLLOW</h4><PlanPicker rules={r} send={100} plan={plan} setPlan={k => act('pool_plan', { text: k, on: k === 'vault' })} testid="bst-plan" /><small className="bst-hint">Shown for a $100 send. A send already made keeps its plan.</small></section>
    <section className="bst-levers" aria-label="What its boost does now"><h4><Ic3 e="⚡" /> BOOST {rank ? 'RANKS ONLY' : `${Math.round(b * 100)}%`}<small className="m-num" data-tip="Points left to spend on bringing a date closer" data-testid="bst-points">{left} points to spend · {r.ptsPerDay || 10} points = 1 day</small></h4>
      <Lever k="PRINT STRENGTH" part={(d.strength || 0) / 100} text={`${d.strength || 0}/100`} tip="From its real results, recent ones most, and it takes about 10 to read fully. A stronger print earns up to 1.5x the points from the same send." />
      <Lever k="MORE BACK" part={r.boostBackPts ? backPlus / r.boostBackPts : 0} text={`+${backPlus.toFixed(1)}%`} tip={`A full boost adds ${r.boostBackPts || 0}% to what its next sends bring back.`} />
      <Lever k="FEE POT" part={(weight - 1) / Math.max(0.01, (r.weightMaxX || 2) - 1)} text={`${weight.toFixed(2)}x`} tip={`Its part of the fee pot, up to ${r.weightMaxX || 2}x. The pot still pays the same total.`} /></section>
    <small className="bst-hint" data-tip="Points scale with dollars, up to a limit per send">A $10 send earns about {Math.round(Math.min(r.ptsMaxSend || 60, (r.ptsBase || 5) + 10 * (r.ptsPerUsd || 2)) * (0.5 + (d.strength || 0) / 100))} points at this strength. Points fade by half in {r.boostFadeDays || 60} days.</small>
    {p.streams?.length ? <section className="bst-sec"><h4>EVERY SEND: HOW MUCH AND WHEN</h4><ol className="bst-streams">{p.streams.map(s => <Stream key={s.id} r={s} rules={r} left={left} busy={busy} onSpend={(id, pts) => act('pool_spend', { job: id, cap: pts })} />)}</ol></section> : null}
    <div className="bst-tiles">{[['WORKING NOW', money((p.lockedUsd || 0) + (p.vaultUsd || 0)), 'Locked plus its Vault claim'], ['SENT', money(p.sentUsd), 'What its proofs have sent, at today\'s price'], ['FROM THE FEE POT', money(p.earnedUsd), 'What members\' trading fees have paid it so far'], ['ADDING A DAY', money(p.feeShareDayUsd), 'What the fee pot pays it at today\'s rate. It rises and falls with trading'], ['PROOFPRINT', d.printLevel ?? 0, 'How much it has filed and learned']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div>
    {d.boostLog?.length ? <ol className="clx-log bst-log">{d.boostLog.map(x => <li key={x.ref}><em className="m-num">+{x.pts}</em>{x.why}</li>)}</ol> : null}
    <details className="bst-how" open={empty}><summary data-tip="Where a proof's money goes">See how it works</summary><SplitFlow rules={r} plan={plan} onPlan={k => act('pool_plan', { text: k, on: k === 'vault' })} testid="bst-split" /></details>
  </div>;
}
