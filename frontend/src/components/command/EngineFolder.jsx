import React, { useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';

// 📡 AGT-12 Engines (owner: "live data showing what each engine does for agents and the Collective"): every engine that runs on its own,
// as live counts from the server (op engines), refreshed every 15 s while the window is visible. No wallet, prompt or page.
const ago = t => (t ? `${Math.max(0, Math.round((Date.now() / 1000 - t) / 60))} min ago` : 'not yet');
const usd = n => (n ? `$${n < 0.01 ? n.toFixed(4) : n.toFixed(2)}` : '$0');

export function EngineFolder({ cat, work }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => {
    let on = true; const go = () => { if (document.hidden) return; Promise.resolve().then(() => work(cat.id, { op: 'engines' })).then(j => { if (on) { setD(j); setErr(''); } }).catch(e => on && setErr(e.message)); };
    go(); const t = setInterval(go, 15000); return () => { on = false; clearInterval(t); };
  }, [cat.id, work]);
  if (!d) return <p className="dsk-note" data-testid="eng-wait">{err ? `⚠ ${err}` : 'Reading the engines…'}</p>;
  const rv = d.reviewer || {}; const kits = d.kits || {}; const rd = d.reads || {}; const mk = d.methods || {}; const top = Math.max(1, ...(d.routes || []).map(r => r.calls));
  const pct = rv.graded + rv.waiting ? rv.graded / (rv.graded + rv.waiting) : 0;
  return <div className="eng" data-testid="eng">
    <section className="eng-card m-card m-live" style={{ '--i': 0 }} data-testid="eng-reviewer"><h4><Ic3 e="🧑‍⚖️" /> REVIEWER <small>OSSY + G4 grade every closed proof · one every {rv.everyS}s · {rv.scope?.join(', ')}</small></h4>
      <div className="eng-hero"><b className="m-num" data-tip="Proofs graded at the current review version">{rv.graded}</b><small>graded</small><b className="m-num">{rv.waiting}</b><small>waiting</small><b className="m-num">{rv.passPct == null ? '—' : `${rv.passPct}%`}</b><small>pass</small></div>
      <i className="eng-meter" aria-hidden="true"><u style={{ transform: `scaleX(${pct})` }} /></i>
      <ul className="eng-list">{(rv.answered || []).map(a => <li key={a.who}><span>{a.who}</span><b className="m-num">{a.calls}</b></li>)}</ul><small className="eng-foot">last grade {ago(rv.lastAt)}</small></section>
    <section className="eng-card m-card" style={{ '--i': 1 }} data-testid="eng-kits"><h4><Ic3 e="♻" /> KIT FRESHNESS <small>npm daily · smoke-tested in a headless browser · rolls back</small></h4>
      <div className="eng-hero"><b className="m-num">{kits.live}</b><small>kits live</small><b className="m-num">{kits.moved}</b><small>moved up</small><b className="m-num">{kits.everyH}h</b><small>cycle</small></div>
      {(kits.held || []).length ? <ul className="eng-list">{kits.held.map(h => <li key={h.kit + h.to}><span>{h.kit} {h.to} held back</span><b>{String(h.why || '').slice(0, 40)}</b></li>)}</ul> : null}<small className="eng-foot">checked {ago(kits.checkedAt)}</small></section>
    <section className="eng-card m-card" style={{ '--i': 2 }} data-testid="eng-reads"><h4><Ic3 e="🧠" /> SHARED READS <small>one read serves every agent's next proof while fresh: never researched twice</small></h4>
      <ul className="eng-list">{(rd.kinds || []).length ? rd.kinds.map(r => <li key={r.kind}><span>{r.kind.toUpperCase()} · {r.sites} sites · {r.ageMin}/{r.freshMin} min</span><b className="m-num">{r.reused}× reused</b></li>) : <li><span>No live read right now</span><b>—</b></li>}
        <li><span>PoB topic reads live</span><b className="m-num">{rd.topics} · {rd.topicReuses}× reused</b></li></ul></section>
    <section className="eng-card m-card" style={{ '--i': 3 }} data-testid="eng-methods"><h4><Ic3 e="🧰" /> METHOD KITS <small>followed vs skipped, settled from outside; quarantined when clearly worse</small></h4>
      <div className="eng-hero"><b className="m-num">{mk.active}</b><small>active</small><b className="m-num">{mk.unmeasured}</b><small>measuring</small><b className="m-num">{mk.quarantined}</b><small>quarantined</small></div></section>
    <section className="eng-card m-card eng-wide" style={{ '--i': 4 }} data-testid="eng-routes"><h4><Ic3 e="🛰" /> MODEL ROUTES · LAST HOUR <small>who really answered, how fast, what it cost</small></h4>
      {(d.routes || []).length ? <ul className="eng-routes">{d.routes.map(r => <li key={r.route} data-tip={`${r.calls} calls · ${r.okPct}% ok · avg ${Math.round(r.avgMs / 100) / 10}s · ${usd(r.usd)}`}><span>{r.route}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${r.calls / top})` }} /></i><b className="m-num">{r.calls}</b><small className="m-num">{r.okPct}% · {Math.round(r.avgMs / 100) / 10}s · {usd(r.usd)}</small></li>)}</ul>
        : <p className="dsk-note">No model call in the last hour.</p>}</section>
  </div>;
}
