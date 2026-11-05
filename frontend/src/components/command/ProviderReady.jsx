import React, { useEffect, useState } from 'react';
import '../../styles/feeCats.css';
import { Ic3 } from '../../lib/icon3d';

// 🔑 HQ › Core: what still needs a human. Names only, and "set" never means funded: the row says so.
function KeyRow({ r, call, onSaved, i }) {
  const [open, setOpen] = useState(false); const [vals, setVals] = useState({}); const [busy, setBusy] = useState(false); const [msg, setMsg] = useState(''); const keys = r.keys || r.missing || [];
  const save = async e => { e.preventDefault(); setBusy(true); setMsg(''); try { let last = null; for (const k of keys) { if (vals[k]?.trim()) last = await call('/admin/provider-key', { method: 'POST', body: JSON.stringify({ name: k, value: vals[k].trim() }) }); } if (last) { setVals({}); setMsg('Saved. The agent service picks it up on its next restart.'); onSaved(last); } } catch (er) { setMsg(er.message); } finally { setBusy(false); } };
  const site = /\./.test(r.where) ? `https://${r.where}` : null;
  return <li className={`${r.ready ? 'is-ok' : 'is-need'}${open ? ' is-open' : ''}`} style={{ '--i': i }}><button type="button" className="pvr-row" aria-expanded={open} onClick={() => setOpen(x => !x)} data-tip={open ? 'Close' : r.ready ? 'Replace this key' : 'Enter this key'} data-testid={`pvr-${r.name}`}><i aria-hidden="true" /><span><b>{r.name}</b><small>{r.unlocks}</small></span><em>{r.ready ? 'SET' : `NEEDS ${r.missing.length}`}</em><u aria-hidden="true">{open ? '▴' : '▾'}</u></button>
    {open ? <form className="pvr-form" onSubmit={save} data-testid={`pvr-form-${r.name}`}>{keys.map(k => <label key={k}><small>{k}{(r.missing || []).includes(k) ? '' : ' · set, type to replace'}</small><input className="m-input" type="password" autoComplete="off" spellCheck="false" value={vals[k] || ''} onChange={e => setVals(v => ({ ...v, [k]: e.target.value }))} aria-label={k} data-testid={`pvr-input-${k}`} /></label>)}
      <div className="pvr-acts">{site ? <a className="m-btn" href={site} target="_blank" rel="noopener noreferrer" data-tip={`Get it from ${r.where}`}>Get a key ↗</a> : <small>From {r.where}</small>}<button type="submit" className="m-btn m-go" disabled={busy || !keys.some(k => vals[k]?.trim())} data-tip="Saved in backend/.env on your server. Never shown again, never logged" data-testid={`pvr-save-${r.name}`}>{busy ? 'Saving…' : 'Save'}</button></div>{msg ? <small className="pvr-msg" role="status">{msg}</small> : null}</form> : null}</li>;
}
export function ProviderReady({ call }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; call('/admin/providers').then(x => on && setD(x)).catch(() => on && setD({ rows: [], ready: 0, total: 0, failed: true })); return () => { on = false; }; }, [call]);
  if (!d) return <p className="cc-empty">Reading provider keys…</p>;
  if (d.failed || !d.total) return <p className="cc-empty" role="alert">Could not read provider keys.</p>;
  const rows = d.rows || []; const left = (d.total || 0) - (d.ready || 0);
  return <section className="m-card pvr" data-testid="provider-ready">
    <header className="pvr-head" data-tip="Set does not mean funded or within quota" data-testid="pr-head"><span><b><Ic3 e="🔑" /> PROVIDER KEYS</b><small>{left ? `${left} waiting on a key` : 'Every key is set'} · click one to enter it · set does not mean funded</small></span>
      <span className="pvr-meter" aria-hidden="true"><i><u style={{ transform: `scaleX(${d.total ? d.ready / d.total : 0})` }} /></i></span><b className="m-num pvr-n">{d.ready || 0}/{d.total || 0}</b></header>
    <ul className="pvr-list">{rows.map((r, i) => <KeyRow key={r.name} r={r} i={i} call={call} onSaved={setD} />)}</ul>
  </section>;
}
