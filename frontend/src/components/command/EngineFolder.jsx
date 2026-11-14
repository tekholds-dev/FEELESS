import React, { useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/proposals.css';

// 📡 AGT-12 Engines (owner: "live data showing what each engine does for agents and the Collective"): every engine that runs on its own,
// as live counts from the server (op engines), refreshed every 15 s while the window is visible. No wallet, prompt or page.
const ago = t => (t ? `${Math.max(0, Math.round((Date.now() / 1000 - t) / 60))} min ago` : 'not yet');
const usd = n => (n ? `$${n < 0.01 ? n.toFixed(4) : n.toFixed(2)}` : '$0');

// 🔎 owner 2026-11-14 ("cant open these to see, review and approve"): every proposal opens — the full check, how often it failed, the real
// proofs that failed it with what OSSY / G4 said, and exactly what a yes changes. Approve stays one tap, inside and outside the open row.
export function PropRow({ id, title, meter, bad = false, side, children, onApprove, approveTip, testid }) {
  const [open, setOpen] = useState(false);
  return <li className={`eng-prop${open ? ' is-open' : ''}`} data-testid={testid}>
    <button type="button" className="eng-prop-h" aria-expanded={open} onClick={() => setOpen(o => !o)} data-tip={open ? 'Close it' : 'Open it: the evidence and what a yes changes'} data-testid={`${testid}-open`}>
      <span>{title}</span><em aria-hidden="true">{open ? '−' : '+'}</em></button>
    {meter != null ? <i className={`eng-meter${bad ? ' is-bad' : ''}`} aria-hidden="true"><u style={{ transform: `scaleX(${meter})` }} /></i> : null}
    {open ? <div className="eng-prop-body" data-testid={`${testid}-body`}>{children}</div> : null}
    {onApprove ? <button type="button" className="m-btn m-go" onClick={() => onApprove(id)} data-tip={approveTip} data-testid={`eng-approve-${id}`}>Approve</button> : side}
  </li>;
}
const Said = ({ ex }) => (ex || []).length ? <ol className="eng-ex">{ex.map((e, i) => <li key={i}><b>{e.agent}{e.n ? ` · #${e.n}` : ''}</b>{e.title ? <small>{e.title}</small> : null}
  {(e.said || []).map((s, k) => <q key={k}><i>{s.who}</i>{s.note || 'failed it, no note'}</q>)}</li>)}</ol> : null;

export function EngineFolder({ cat, work }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [said, setSaid] = useState('');
  useEffect(() => {
    let on = true; const go = () => { if (document.hidden) return; Promise.resolve().then(() => work(cat.id, { op: 'engines' })).then(j => { if (on) { setD(j); setErr(''); } }).catch(e => on && setErr(e.message)); };
    go(); const t = setInterval(go, 15000); return () => { on = false; clearInterval(t); };
  }, [cat.id, work]);
  if (!d) return <p className="dsk-note" data-testid="eng-wait">{err ? `⚠ ${err}` : 'Reading the engines…'}</p>;
  const rv = d.reviewer || {}; const kits = d.kits || {}; const rd = d.reads || {}; const mk = d.methods || {}; const top = Math.max(1, ...(d.routes || []).map(r => r.calls));
  const pct = rv.graded + rv.waiting ? rv.graded / (rv.graded + rv.waiting) : 0;
  const pr = d.proposals || {};
  const approve = async id => { setSaid(''); try { const j = await work(cat.id, { op: 'kit_method_approve', text: id }); setD(x => ({ ...x, proposals: { ...x.proposals, approved: j.approved, kits: (x.proposals?.kits || []).filter(r => r.id !== id) } })); setSaid(`Approved: every proof of its kind now follows ${id}`); } catch (e) { setSaid(e.message); } };
  return <div className="eng" data-testid="eng">
    <section className="eng-card m-card m-live" style={{ '--i': 0 }} data-testid="eng-reviewer"><h4><Ic3 e="🧑‍⚖️" /> REVIEWER <small>The Collective grades every closed proof · one every {rv.everyS}s · {rv.scope?.join(', ')}</small></h4>
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
    <section className="eng-card m-card eng-wide" style={{ '--i': 4 }} data-testid="eng-proposals"><h4>🧪 THE COLLECTIVE PROPOSES <small>from its own reviews and the asks no proof covers; nothing changes until the owner says yes</small></h4>
      <div className="eng-props">
        <div><small className="m-label">METHOD KITS · checks The Collective keeps failing</small>{(pr.kits || []).length ? <ul className="eng-list">{pr.kits.map(r => <PropRow key={r.id} id={r.id} testid={`eng-prop-${r.id}`} title={`${r.kind.toUpperCase()} · ${r.what}`} meter={r.failRate} bad
          onApprove={pr.canApprove ? approve : null} approveTip="Every proof of this kind is told to pass this check, and it is measured like the other kits" side={<b className="m-num">{Math.round(r.failRate * 100)}%</b>}>
          <p className="eng-prop-q">{r.full || r.what}</p>
          <p className="eng-prop-n"><b className="m-num">{r.failed ?? Math.round(r.failRate * r.seen)}</b> of <b className="m-num">{r.seen}</b> reviewed {r.kind.toUpperCase()}s failed this check ({Math.round(r.failRate * 100)}%).</p>
          <Said ex={r.examples} />
          <p className="eng-prop-yes"><b>If you approve:</b> every new {r.kind.toUpperCase()} brief is told to pass this check. It is scored like the other kits (followed vs skipped, settled from outside) and quarantined if proofs that follow it do worse. Nothing about money or limits changes.</p>
        </PropRow>)}</ul>
          : <p className="dsk-note">None yet: a check must fail in 60%+ of 4+ reviewed proofs of a kind.</p>}</div>
        <div data-testid="eng-combos"><small className="m-label">🧩 KITS THAT WORK BETTER TOGETHER · settled proofs that followed both</small>{(pr.combos || []).filter(r => r.settled).length ? <ul className="eng-list">{pr.combos.filter(r => r.settled).slice(0, 5).map(r => <PropRow key={r.id} id={r.id} testid={`eng-combo-${r.id}`} title={r.combo.join(' + ')} meter={r.bothWin || 0}
          onApprove={!r.approved && r.proposed && pr.canApprove ? approve : null} approveTip="Both kits together join every brief of these kinds, measured like any kit" side={r.approved ? <b>✓ ON</b> : <b className="m-num">{r.settled}/10</b>}>
          <p className="eng-prop-n"><b className="m-num">{r.settled}</b> settled proofs followed both: <b className="m-num">{r.bothWin == null ? '–' : `${Math.round(r.bothWin * 100)}%`}</b> right. The better kit alone: <b className="m-num">{r.bestAlone == null ? '–' : `${Math.round(r.bestAlone * 100)}%`}</b>.</p>
          <p className="eng-prop-yes"><b>{r.approved ? 'On:' : r.proposed ? 'If you approve:' : 'Not proposed yet:'}</b> {r.approved ? 'both kits join every brief of these kinds together.' : r.proposed ? 'both kits join every brief of these kinds together, measured like any kit and quarantined if worse.' : 'it needs 10+ settled proofs and 5 points better than the better kit alone.'}</p>
        </PropRow>)}</ul>
          : <p className="dsk-note">None measured yet: pairs show once settled proofs followed both.</p>}</div>
        <div><small className="m-label">NEW PROOF TYPES · asks no proof covers</small>{(pr.proofs || []).length ? <ul className="eng-list">{pr.proofs.map(g => <PropRow key={g.word} id={g.word} testid={`eng-gap-${g.word}`} title={g.name} side={<b className="m-num">{g.asks} asks</b>}>
          <p className="eng-prop-n"><b className="m-num">{g.asks}</b> asks with no proof type for them. What people asked:</p>
          <ol className="eng-ex">{(g.examples || []).map((x, i) => <li key={i}><q>{x}</q></li>)}</ol>
          <p className="eng-prop-yes"><b>To act on it:</b> this is a new proof type to build, not a switch. Ask a Claude to build it.</p>
        </PropRow>)}</ul>
          : <p className="dsk-note">None yet: the same kind of ask, 3+ times, with no proof for it.</p>}</div>
        <div><small className="m-label">APPROVED · HISTORY</small><ul className="eng-list">{(pr.approved || []).map(a => <li key={a.id}><span>✓ {a.id}</span><b>{a.kind?.toUpperCase()}</b></li>)}
          {(pr.history || []).slice(0, 5).map((h, i) => <li key={`h${i}`}><span>{h.kit}: {h.from || 'new'} → {h.to}</span><b className="m-num">{ago(h.at)}</b></li>)}
          {!(pr.approved || []).length && !(pr.history || []).length ? <li><span>Nothing approved or moved yet</span><b>—</b></li> : null}</ul></div>
      </div>{said ? <p className="dsk-note" role="status" data-testid="eng-said">{said}</p> : null}</section>
    <section className="eng-card m-card eng-wide" style={{ '--i': 4 }} data-testid="eng-routes"><h4><Ic3 e="🛰" /> MODEL ROUTES · LAST HOUR <small>who really answered, how fast, what it cost</small></h4>
      {(d.routes || []).length ? <ul className="eng-routes">{d.routes.map(r => <li key={r.route} data-tip={`${r.calls} calls · ${r.okPct}% ok · avg ${Math.round(r.avgMs / 100) / 10}s · ${usd(r.usd)}`}><span>{r.route}</span><i aria-hidden="true"><u style={{ transform: `scaleX(${r.calls / top})` }} /></i><b className="m-num">{r.calls}</b><small className="m-num">{r.okPct}% · {Math.round(r.avgMs / 100) / 10}s · {usd(r.usd)}</small></li>)}</ul>
        : <p className="dsk-note">No model call in the last hour.</p>}</section>
  </div>;
}
