import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuthQuery } from '../../lib/chatSession';

// 🧩 COL-26 (owner + GPT 2026-11-09): the Collective's proven parts. Blocks of PROVED pages, each with its licenses and its family tree (which
// proofs reused it). The next build is offered the ones that fit; a part nobody reuses in 30 days goes stale and stops being offered.
export function PartsShelf({ cat }) {
  const [d, setD] = useState(null); const [open, setOpen] = useState(false); const [err, setErr] = useState('');
  useEffect(() => { let on = true; fetch(apiUrl(`/api/cats/${cat.id}/parts?${agentAuthQuery()}`)).then(r => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`)))).then(x => on && setD(x)).catch(e => on && setErr(e.message)); return () => { on = false; }; }, [cat.id]);
  const parts = d?.parts || []; const live = parts.filter(p => !p.stale); const reused = parts.filter(p => p.uses > 0).length; const top = Math.max(1, ...parts.map(p => p.uses));
  if (!d && !err) return null;
  return <details className="pts" open={open} onToggle={e => setOpen(e.currentTarget.open)} data-testid="parts-shelf">
    <summary data-tip="Blocks of PROVED pages. Your next build is offered the ones that fit; reuse is logged, never paid"><b>🧩 PROVEN PARTS</b>
      <span className="pts-pips" aria-hidden="true">{parts.slice(0, 24).map(p => <i key={p.id} className={p.stale ? 'is-stale' : p.uses ? 'is-used' : ''} />)}</span>
      <small>{err ? `⚠ ${err}` : `${live.length} offered · ${reused} reused · ${parts.length - live.length} stale`}</small></summary>
    {parts.length ? <ul className="pts-list">{parts.slice(0, 40).map((p, i) => <li key={p.id} style={{ '--i': i }} className={p.stale ? 'is-stale' : ''} data-testid={`part-${p.id}`}>
      <span className="pts-t"><b>{p.title}</b><small>&lt;{p.tag}&gt; · from a PROVED {p.kind === 'pos' ? 'PoStatic' : p.kind}{p.mine ? ' of this agent' : ''} · {p.licenses.join(', ')}</small></span>
      <span className="pts-n" data-tip={p.reusedBy.length ? `Reused in ${p.reusedBy.map(r => r.ref).join(', ')}` : 'Not reused yet'}><em>REUSED</em><b className="m-num">{p.uses}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${p.uses / top})` }} /></i></span>
      <span className={`pts-s${p.stale ? ' is-stale' : ''}`}>{p.stale ? `stale · not offered` : 'offered'}</span></li>)}</ul>
      : <p className="m-note">No parts yet. When a PoStatic is marked right and its 24-hour stamp says PROVED, its blocks land here.</p>}
  </details>;
}
