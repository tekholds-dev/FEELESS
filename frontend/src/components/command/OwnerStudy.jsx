import React from 'react';
import '../../styles/ownerStudy.css';

// 👤 YOU — the owner study (backend owner_study.py, payload `ownerStudy`): how your own moves graded 30 min later, your seats vs where the
// agents would have sold, your dragged SL / TP vs their lines, and what the study suggests (each one waits for your ✅ in 🧠 Brain › Fix).
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
export function OwnerStudy({ study, memory }) {
  const s = study || {};
  const kinds = (s.kinds || []).filter(k => k.n > 0);
  const cmp = (s.seats || {}).cmp || {};
  const y = (s.hand || {}).yours || {}; const a = (s.hand || {}).agents || {};
  const mem = memory || {}; const memN = Object.values(mem).reduce((t, n) => t + (Number(n) || 0), 0);
  if (!study) return <div className="ost m-card" data-testid="owner-study"><h4>👤 YOU</h4><small className="ost-dim">The study builds every 10 minutes from your graded moves — nothing yet.</small></div>;
  return <div className="ost m-card" data-testid="owner-study">
    <header><h4>👤 YOU <small>your own moves, graded 30 min later · the agents study this</small></h4>
      <span className="ost-ring" style={{ '--p': (s.score || 0) / 100 }} data-tip="share of your graded moves that turned out good"><b>{s.score == null ? '—' : `${s.score}%`}</b><small>{s.graded || 0} graded</small></span></header>
    <ul className="ost-kinds">{kinds.map((k, i) => <li key={k.kind} style={{ '--i': i }} data-tip={`the coin typically ${pc(k.medPct)} 30 min after your ${k.label}`}>
      <span>{k.label}</span><span className="ost-bar"><i style={{ transform: `scaleX(${(k.goodPct || 0) / 100})` }} /></span><em>{k.goodPct == null ? '—' : `${k.goodPct}%`}</em><small>n {k.n}</small></li>)}
      {!kinds.length && <li className="ost-dim">no graded moves yet</li>}</ul>
    <div className="ost-vs">
      <span data-tip="your closed seats vs where the agents' first exit call would have sold"><small>YOUR SEATS</small><b className={Number(cmp.you) >= Number(cmp.agents) ? 'is-up' : 'is-dn'}>{pc(cmp.you)}</b><em>agents {pc(cmp.agents)} · n {cmp.n || 0}</em></span>
      <span data-tip="closed real trades where you dragged the SL / TP vs the agents' own lines"><small>YOUR LINES</small><b className={Number(y.med) >= Number(a.med) ? 'is-up' : 'is-dn'}>{pc(y.med)}</b><em>agents {pc(a.med)} · n {y.n || 0}</em></span>
      <span data-tip="notes filed for the AI (capped drawers: you · lessons · rules · coins · site)"><small>AI MEMORY</small><b>{memN}</b><em>{['owner', 'lessons', 'rules', 'coins'].map(k => `${k} ${mem[k] || 0}`).join(' · ')}</em></span></div>
    {(s.findings || []).length ? <ul className="ost-find">{s.findings.map((f, i) => <li key={i} style={{ '--i': i }}>{f}</li>)}</ul> : null}
    {(s.suggestions || []).length ? <div className="ost-sugg"><small>THE STUDY SUGGESTS · waiting for your ✅ in 🧠 Brain › Fix</small>{s.suggestions.map((x, i) => <p key={i}><b>{x.agent}</b> {x.value}</p>)}</div> : null}
  </div>;
}
