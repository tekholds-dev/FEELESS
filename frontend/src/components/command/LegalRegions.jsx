import React, { useEffect, useMemo, useRef, useState } from 'react';
import { COUNTRIES, countryName } from '../LegalConsent';
import '../../styles/legal.css';

// ⚖ HQ › Money › Legal & regions (LEGAL-1): the owner's switches for backend/legal.py — which countries are closed everywhere and per
// feature, the 18+ gate per feature, the minimum age — plus who accepted this terms version (by stated country) and the export / delete log
// (counts only, never the data). The server re-checks every edit (the sanctioned four can't be removed; unknown codes are dropped).
const short = a => (a ? `${a.slice(0, 4)}…${a.slice(-4)}` : '');
const ago = t => { const s = Math.max(0, Date.now() / 1000 - t); return s < 3600 ? `${Math.round(s / 60)}m ago` : s < 86400 ? `${Math.round(s / 3600)}h ago` : `${Math.round(s / 86400)}d ago`; };

function Codes({ codes, locked = [], onChange, testid, label }) {
  const [add, setAdd] = useState('');
  const opts = useMemo(() => COUNTRIES.filter(c => !codes.includes(c)).map(c => [c, countryName(c)]).sort((a, b) => a[1].localeCompare(b[1])), [codes]);
  return <div className="lgr-codes" data-testid={testid}>
    {codes.length ? codes.map(c => <span key={c} className={`lgr-code${locked.includes(c) ? ' is-locked' : ''}`} data-tip={locked.includes(c) ? `${countryName(c)} — sanctioned; the law keeps it closed` : countryName(c)}>
      <b className="m-num">{c}</b>{locked.includes(c) ? <i aria-hidden="true">🔒</i> : <button type="button" onClick={() => onChange(codes.filter(x => x !== c))} aria-label={`Open ${countryName(c)} again`} data-testid={`${testid}-x-${c}`}>✕</button>}</span>) : <small className="lgr-open">Open everywhere</small>}
    <select className="m-input lgr-add" value={add} aria-label={`Close ${label} in a country`} data-tip={`Close ${label} in one more country`} onChange={e => { const v = e.target.value; setAdd(''); if (v) onChange([...codes, v]); }} data-testid={`${testid}-add`}>
      <option value="">+ country</option>{opts.map(([c, n]) => <option key={c} value={c}>{n} ({c})</option>)}
    </select>
  </div>;
}

export function LegalRegions({ call }) {
  const [v, setV] = useState(null); const [cfg, setCfg] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(false); const [saved, setSaved] = useState('');
  const callRef = useRef(call); callRef.current = call;   // `call` changes identity with every wallet re-render: load ONCE, so a re-render never wipes unsaved edits
  useEffect(() => { let live = true; callRef.current('/admin/legal').then(j => { if (live) { setV(j); setCfg(j.cfg); } }).catch(e => live && setErr(e.message)); return () => { live = false; }; }, []);
  const dirty = v && cfg && JSON.stringify(cfg) !== JSON.stringify(v.cfg);
  const save = async () => { setBusy(true); setErr(''); setSaved(''); try { const j = await call('/admin/legal', { method: 'POST', body: JSON.stringify({ cfg: { ...cfg, minAge: Math.max(18, Math.min(25, Math.round(Number(cfg.minAge)) || 18)) } }) }); setV(j); setCfg(j.cfg); setSaved('Saved — every gate uses it now.'); } catch (e) { setErr(e.message); } finally { setBusy(false); } };
  if (err && !v) return <p className="m-note" data-testid="lgr-err">{err}</p>;
  if (!v || !cfg) return <p className="m-note">Loading the legal switches…</p>;
  const setFeat = (k, patch) => setCfg(c => ({ ...c, features: { ...c.features, [k]: { ...c.features[k], ...patch } } }));
  const total = v.accepted + v.stale; const top = Math.max(1, ...v.byCountry.map(x => x[1]));
  const closedN = Object.values(cfg.features).reduce((a, f) => a + f.blocked.length, 0);
  return <section className="lgr" data-testid="hq-legal">
    <div className="lgr-top">
      <div className="m-card lgr-stat"><span className="m-label">ACCEPTED · TERMS {v.version}</span><b className="m-num" data-testid="lgr-accepted">{v.accepted}</b>
        <u className="lgr-meter" aria-hidden="true"><s style={{ transform: `scaleX(${total ? v.accepted / total : 0})` }} /></u><small>{v.stale ? `${v.stale} accepted an older version — asked again on their next trade` : 'every wallet that accepted is on this version'}</small></div>
      <div className="m-card lgr-stat"><span className="m-label">CLOSED EVERYWHERE</span><b className="m-num">{cfg.everywhere.length}</b><small>{cfg.everywhere.join(' · ')}</small></div>
      <div className="m-card lgr-stat"><span className="m-label">FEATURE CLOSURES</span><b className="m-num">{closedN}</b><small>{closedN ? 'country × feature pairs closed' : 'every feature open outside the sanctioned list'}</small></div>
    </div>
    <div className="lgr-two">
      <div className="m-card lgr-switches">
        <header><span className="m-label">SWITCHES</span><span className="lgr-save">{saved ? <small className="lgr-ok" role="status">{saved}</small> : null}{err ? <small className="lgr-bad" role="alert">{err}</small> : null}
          <button type="button" className="m-btn" disabled={!dirty || busy} onClick={() => setCfg(v.cfg)} data-tip="Throw away the edits">Undo</button>
          <button type="button" className="m-btn m-go" disabled={!dirty || busy} onClick={save} data-testid="lgr-save" data-tip="Every gate on the site uses the new switches within a minute">{busy ? 'Saving…' : 'Save'}</button></span></header>
        <div className="lgr-row is-every"><span><b>Everywhere</b><small>Closed for the whole site. The sanctioned four stay.</small></span>
          <Codes codes={cfg.everywhere} locked={v.sanctioned} label="the whole site" testid="lgr-every" onChange={x => setCfg(c => ({ ...c, everywhere: x }))} /></div>
        {Object.entries(v.features).map(([k, name], i) => <div key={k} className="lgr-row" style={{ '--i': i }}>
          <span><b>{name}</b><label className="lgr-age" data-tip="Ask the wallet for its 18+ / terms statement before this feature signs"><input type="checkbox" checked={!!cfg.features[k]?.ageGate} onChange={e => setFeat(k, { ageGate: e.target.checked })} data-testid={`lgr-age-${k}`} /> {cfg.minAge}+ and terms</label></span>
          <Codes codes={cfg.features[k]?.blocked || []} label={name} testid={`lgr-${k}`} onChange={x => setFeat(k, { blocked: x })} /></div>)}
        <div className="lgr-row"><span><b>Minimum age</b><small>18 to 25. Applies to every gated feature.</small></span>
          <input className="m-input lgr-num m-num" type="number" min="18" max="25" value={cfg.minAge} onChange={e => setCfg(c => ({ ...c, minAge: e.target.value }))} onBlur={() => setCfg(c => ({ ...c, minAge: Math.max(18, Math.min(25, Math.round(Number(c.minAge)) || 18)) }))} aria-label="Minimum age" data-testid="lgr-minage" /></div>
        <div className="lgr-row"><span><b>Ask every wallet to accept</b><small>Off = only the country checks run (not recommended).</small></span>
          <label className="lgr-age"><input type="checkbox" checked={!!cfg.requireAccept} onChange={e => setCfg(c => ({ ...c, requireAccept: e.target.checked }))} data-testid="lgr-require" /> on</label></div>
      </div>
      <div className="lgr-side">
        <div className="m-card"><span className="m-label">ACCEPTED BY STATED COUNTRY</span>
          {v.byCountry.length ? <ol className="lgr-bars" data-testid="lgr-by-country">{v.byCountry.map(([c, n], i) => <li key={c} style={{ '--i': i }} data-tip={countryName(c)}><b className="m-num">{c}</b><u><s style={{ transform: `scaleX(${n / top})` }} /></u><i className="m-num">{n}</i></li>)}</ol> : <p className="m-note">No wallet has accepted the {v.version} terms yet.</p>}</div>
        <div className="m-card"><span className="m-label">EXPORT / DELETE LOG</span>
          {v.requests.length ? <ol className="lgr-log" data-testid="lgr-log">{v.requests.map((r, i) => <li key={`${r.at}-${i}`} className={`is-${r.kind}`}><em>{r.kind === 'delete' ? 'DELETE' : 'EXPORT'}</em><b className="m-num">{short(r.wallet)}</b><small className="m-num" data-tip={Object.entries(r.counts || {}).map(([k, n]) => `${k} ${n}`).join(' · ')}>{Object.values(r.counts || {}).reduce((a, n) => a + n, 0)} rows</small><time className="m-num">{ago(r.at)}</time></li>)}</ol> : <p className="m-note">No export or delete yet.</p>}</div>
      </div>
    </div>
  </section>;
}
