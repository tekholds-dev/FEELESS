import React, { useEffect, useState } from 'react';
import '../../styles/brainLearned.css';

// 🎓 LEARNED (owner, 2026-10-16: "tell me agents / AI are learning and I can go in the chat log to see learnings, proposals"): one read of
// GET /admin/ai/learned — your standing words filed from the chat log, hold lessons, live rules, the germ entry's real record (agents vs
// yours) and the fixes waiting for your ✅. Read only; re-read every 30s while open.
const ago = at => { const s = Math.max(0, Date.now() / 1000 - Number(at || 0)); return s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);

export function germBars(rec) {
  return Object.entries(rec || {}).map(([k, v]) => ({ k, n: v.n || 0, med: v.med, won: v.won || 0 })).sort((a, b) => (b.med ?? -999) - (a.med ?? -999));
}

function Notes({ title, items, empty }) {
  return <section className="bln-sec"><h5>{title} <small>{(items || []).length}</small></h5>
    {(items || []).length ? <ul>{items.map((x, i) => <li key={i} style={{ '--i': i }}><span>{x.t}</span><em>{ago(x.at)}</em></li>)}</ul> : <p className="bln-dim">{empty}</p>}</section>;
}

export function BrainLearned({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState('');
  useEffect(() => {
    let alive = true;
    const load = () => Promise.resolve(call('/api/reputation/admin/ai/learned')).then(x => { if (alive && x) { setD(x); setErr(''); } }).catch(e => alive && setErr(String(e?.message || e)));
    load(); const t = setInterval(() => !document.hidden && load(), 30000);
    return () => { alive = false; clearInterval(t); };
  }, [call]);
  if (!d) return <div className="bln" data-testid="brain-learned"><p className="bln-dim">{err || 'reading what the desk learned…'}</p></div>;
  const yours = germBars(d.germYours);
  return <div className="bln" data-testid="brain-learned">
    <header className="bln-head"><b>🎓 WHAT THE DESK LEARNED</b><small>filed from your chat, your trades and the real record · the AI + agents read these on every case</small></header>
    <section className="bln-sec bln-germ"><h5>🦠 GERM METHOD · REAL RECORD</h5>
      <p className="bln-line" data-testid="bln-germ-agents"><small>AGENTS</small>{d.germAgents}</p>
      {yours.length ? <ul className="bln-bars" data-testid="bln-germ-yours">{yours.map((b, i) => <li key={b.k} style={{ '--i': i }}>
        <span>{b.k}</span><span className="bln-bar"><i className={Number(b.med) >= 0 ? 'up' : 'dn'} style={{ transform: `scaleX(${Math.min(1, b.won / 100)})` }} /></span>
        <em className={Number(b.med) >= 0 ? 'up' : 'dn'}>{pc(b.med)}</em><small>{b.won}% won · n {b.n}</small></li>)}</ul>
        : <p className="bln-dim">your picks: no closed trade with an entry snapshot yet</p>}</section>
    <section className="bln-sec"><h5>🛠 WAITING FOR YOUR ✅ <small>{(d.pending || []).length}</small></h5>
      {(d.pending || []).length ? <ul>{d.pending.map(p => <li key={p.id}><span><b>{p.agent}</b> {p.key} → {String(p.new)} · {p.reason}</span><em>{p.kind}</em></li>)}</ul>
        : <p className="bln-dim">no proposal waiting — 🛠 Fix agents asks the model for some</p>}</section>
    <Notes title="💬 YOU SAID (from the chat log)" items={d.owner} empty="say how you trade in the chat (always / never / I hold …) and it is filed here" />
    <Notes title="🎓 LESSONS" items={d.lessons} empty="no lessons yet" />
    <Notes title="🧷 LIVE RULES" items={d.rules} empty="no live rules right now" />
  </div>;
}
