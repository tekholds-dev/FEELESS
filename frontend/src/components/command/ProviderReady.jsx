import React, { useEffect, useState } from 'react';
import '../../styles/feeCats.css';

// 🔑 HQ › Core: what still needs a human. Names only, and "set" never means funded: the row says so.
export function ProviderReady({ call }) {
  const [d, setD] = useState(null); const [open, setOpen] = useState(false);
  useEffect(() => { let on = true; call('/admin/providers').then(x => on && setD(x)).catch(() => on && setD({ rows: [], ready: 0, total: 0, failed: true })); return () => { on = false; }; }, [call]);
  if (!d) return <p className="cc-empty">Reading provider keys…</p>;
  if (d.failed || !d.total) return <p className="cc-empty" role="alert">Could not read provider keys.</p>;
  const rows = d.rows || []; const left = (d.total || 0) - (d.ready || 0);
  return <section className="m-card pr" data-testid="provider-ready">
    <button type="button" className="pr-head" aria-expanded={open} onClick={() => setOpen(x => !x)} data-tip="Which provider keys are set, by name only. Set does not mean funded or within quota" data-testid="pr-toggle">
      <span><b>🔑 NEEDS A HUMAN</b><small>{left ? `${left} provider${left === 1 ? '' : 's'} waiting on a key` : 'Every key is set'} · set does not mean funded</small></span>
      <span className="pr-meter" aria-hidden="true"><i><u style={{ transform: `scaleX(${d.total ? d.ready / d.total : 0})` }} /></i></span><b className="m-num pr-n">{d.ready || 0}/{d.total || 0}</b><em aria-hidden="true">{open ? '▴' : '▾'}</em></button>
    {open ? <ul className="pr-list">{rows.map((r, i) => <li key={r.name} className={r.ready ? 'is-ok' : 'is-need'} style={{ '--i': i }}><i aria-hidden="true" /><span><b>{r.name}</b><small>{r.unlocks}</small></span>
      {r.ready ? <em>KEY SET</em> : <code data-tip={`Get it from ${r.where}, then add it to backend/.env`}>{r.missing.join(' · ')}</code>}</li>)}</ul> : null}
  </section>;
}
