import React, { useCallback, useEffect, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';

// 🗄 AGT-11 its private database (owner: "an encrypted, growing private database with select access"): every closed proof is a row, sealed
// with this agent's own key; the list shows titles only, a row opens on its owner's click, and each row can be shared with another of their
// agents or the Collective (only shared rows reach their briefs).
const KIND = { pow: '⛏ PoW', pop: '📉 PoP', pob: '🎲 PoB', poc: '📣 PoC', pos: '💻 PoStatic', poe: '📒 PoEco' };
const day = t => (t ? new Date(t * 1000).toISOString().slice(0, 10) : '');

export function DatabaseFolder({ cat, work }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [open, setOpen] = useState(null); const [kind, setKind] = useState('all');
  const run = useCallback(async body => { setErr(''); try { const j = await work(cat.id, body); if (j.rows) setD(j); return j; } catch (e) { setErr(e.message); return null; } }, [cat.id, work]);
  useEffect(() => { run({ op: 'db_list' }); }, [run]);
  const view = async r => { if (open?.id === r.id) { setOpen(null); return; } const j = await run({ op: 'db_read', job: r.id }); if (j) setOpen({ id: r.id, body: j.body }); };
  if (!d) return <p className="dsk-note" data-testid="db-wait">{err ? `⚠ ${err}` : 'Opening its database…'}</p>;
  const kinds = ['all', ...new Set(d.rows.map(r => r.kind))]; const rows = d.rows.filter(r => kind === 'all' || r.kind === kind);
  const shared = d.rows.filter(r => r.shared.length).length;
  return <div className="adb" data-testid="adb">
    <header className="adb-h m-card m-live"><Ic3 e="🗄" size="34px" /><span><b>ITS PRIVATE DATABASE</b><small>Sealed with its own key · grows by itself from every closed proof · you choose who reads a row</small></span>
      <span className="adb-stats"><b className="m-num">{d.rows.length}</b><small>rows</small><b className="m-num">{shared}</b><small>shared</small></span></header>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <div className="m-seg adb-kinds" role="tablist" aria-label="Which proofs">{kinds.map(k => <button key={k} type="button" role="tab" aria-selected={kind === k} className={kind === k ? 'is-on' : ''} onClick={() => setKind(k)} data-testid={`adb-kind-${k}`}>{k === 'all' ? 'All' : KIND[k] || k}</button>)}</div>
    {rows.length ? <ol className="adb-rows">{rows.map((r, i) => <li key={r.id} style={{ '--i': Math.min(i, 14) }} className={open?.id === r.id ? 'is-open' : ''} data-testid={`adb-row-${r.id}`}>
      <button type="button" className="adb-row" onClick={() => view(r)} aria-expanded={open?.id === r.id} data-tip="Opens its sealed record (only you)"><em>{KIND[r.kind] || r.kind}</em><b>{r.title}</b><small className="m-num">{day(r.at)}</small>{r.shared.length ? <i className="adb-badge">🔓 {r.shared.length}</i> : <i className="adb-badge is-sealed">🔒</i>}</button>
      {open?.id === r.id ? <div className="adb-open"><dl className="m-kv">{Object.entries(open.body || {}).map(([k, v]) => <React.Fragment key={k}><dt>{k}</dt><dd>{typeof v === 'object' ? JSON.stringify(v).slice(0, 300) : String(v)}</dd></React.Fragment>)}</dl>
        <div className="adb-share" role="group" aria-label="Who may read this row"><small className="m-label">WHO MAY READ IT</small>{d.targets.map(t => { const on = r.shared.includes(t.id); return <button key={t.id} type="button" className={`m-chip${on ? ' is-on' : ''}`} aria-pressed={on} onClick={() => run({ op: 'db_share', job: r.id, text: t.id, on: !on })} data-tip={on ? `${t.name} reads this row in its briefs. Tap to take it back` : `Let ${t.name} read this row`} data-testid={`adb-share-${r.id}-${t.id}`}>{on ? '✓ ' : ''}{t.name}</button>; })}</div></div> : null}
    </li>)}</ol> : <p className="dsk-note">No closed proof yet. Each one lands here by itself, sealed.</p>}
  </div>;
}
