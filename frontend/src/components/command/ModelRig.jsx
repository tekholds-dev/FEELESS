import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/modelRig.css';

// 🎛 MODEL RIG (Brain › Models): G4 · OSSY · NEXA side by side — context budget, parallel slots, timeout, background calls a minute (Nexa: how
// often she reads). Saved = live at once (no restart, nothing reloaded). The load command under each card is what makes the MODEL match it.
const FIELDS = [['ctx', '🧠 CONTEXT', v => (v ? `${v / 1024}K` : 'auto')], ['parallel', '⚡ SLOTS', v => `×${v}`], ['timeout', '⏱ TIMEOUT', v => `${v}s`],
  ['perMin', '📞 CALLS / MIN', v => `${v}`], ['every', '🔁 READ EVERY', v => `${v / 60}m`]];
const AV = { lan: '/assets/ai-pfp/g4.gif', local: '/assets/ai-pfp/ossy.gif', win: null };
// 🪟 NEXA's runtime: what you saved vs what llamafile itself reports (/props + /slots). ACTIVE only when the runtime says so.
export const NX_STATE = { active: ['✅ ACTIVE', 'ok'], applying: ['⏳ APPLYING', 'busy'], differs: ['⚠ NOT APPLIED', 'warn'], unreachable: ['✕ NEXA OFFLINE', 'bad'] };
const ctxWord = v => (v ? `${(v / 1024).toFixed(v % 1024 ? 1 : 0)}K` : '—');
export function NexaRuntime({ n, busy, onAct }) {
  if (!n) return null;
  const [word, tone] = NX_STATE[n.state] || ['—', ''];
  const want = n.desired; const got = n.actual;
  const same = k => want && got && want[k] === got[k];
  return <div className={`mrg-nx t-${tone}`} data-testid="nexa-runtime">
    <div className="mrg-nxh"><b>{word}</b><small>{n.controller?.reachable ? '🟢 controller online' : '🔴 controller offline — settings are saved, NEXA is not changed'}</small></div>
    <div className="mrg-nxg">
      <span><em>WANTED</em><b>{want ? `${ctxWord(want.ctx)} × ${want.slots}` : 'auto'}</b></span>
      <i aria-hidden>{n.state === 'applying' ? '⟳' : '→'}</i>
      <span className={got ? (same('ctx') && same('slots') ? 'is-ok' : 'is-off') : ''}><em>RUNNING</em><b>{got ? `${ctxWord(got.ctx)} × ${got.slots}` : 'not answering'}</b>{got?.model ? <small>{got.model}</small> : null}</span>
    </div>
    {n.state === 'applying' ? <span className="mrg-nxbar" aria-hidden><i /></span> : null}
    {n.job?.msg ? <p className="mrg-nxmsg">{n.job.msg}</p> : null}
    {n.auto ? <p className="mrg-nxmsg">Pick a context (not auto) to control NEXA's runtime.</p> : null}
    <div className="mrg-nxacts">
      <button type="button" className="m-btn primary" disabled={!!busy || n.auto || n.state === 'applying'} onClick={() => onAct('apply')} data-testid="nexa-apply">Apply to NEXA</button>
      <button type="button" className="m-btn" disabled={!!busy || n.state === 'applying'} onClick={() => onAct('restart')} data-testid="nexa-restart">⟳ Restart NEXA</button>
    </div>
  </div>;
}

export function ModelRig({ call }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const load = useCallback(() => call('/admin/ai/rig').then(setD).catch(e => setErr(String(e?.message || e))), [call]);
  const applying = d?.nexa?.state === 'applying';
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, applying ? 3000 : 20000); return () => clearInterval(t); }, [load, applying]);
  const save = async (key, f, v) => {
    setBusy(`${key}.${f}`);
    try { setD(await call('/admin/ai/rig', { method: 'POST', body: JSON.stringify({ [key]: { [f]: v } }) })); setErr(''); } catch (e) { setErr(String(e?.message || e)); }
    setBusy('');
  };
  const nexa = async act => {
    setBusy(`nexa.${act}`);
    try { setD(await call('/admin/ai/rig', { method: 'POST', body: JSON.stringify({ nexa: act }) })); setErr(''); } catch (e) { setErr(String(e?.message || e)); }
    setBusy('');
  };
  if (!d?.rows) return <p className="mrg-wait">{err || 'reading the rig…'}</p>;
  return <div className="mrg" data-testid="model-rig">
    <p className="mrg-head"><b>🎛 MODEL RIG</b><small>what FEELESS sends each model · live at once · NEXA's context + slots also restart her llamafile and are checked on it</small></p>
    <div className="mrg-grid">{d.rows.map((r, i) => { const lv = d.live?.[r.key] || {};
      return <section key={r.key} className={`mrg-card k-${r.key}`} style={{ '--i': i }} data-testid={`rig-${r.key}`}>
        <header>{AV[r.key] ? <img src={AV[r.key]} alt="" /> : <i className="mrg-av">🪟</i>}<b>{r.name}</b>
          <span className={`mrg-st s-${String(lv.state || 'untested').toLowerCase().replace(/\s+/g, '-')}`}>{lv.state || 'UNTESTED'}{lv.lastMs ? ` · ${(lv.lastMs / 1000).toFixed(1)}s` : ''}</span></header>
        {FIELDS.filter(([f]) => r[f] !== undefined).map(([f, label, word]) => <div key={f} className="mrg-row"><em>{label}</em>
          <div className="mrg-seg">{(d.options[f] || []).map(v => <button key={v} type="button" className={r[f] === v ? 'active' : ''} disabled={!!busy}
            aria-busy={busy === `${r.key}.${f}`} onClick={() => save(r.key, f, v)} data-testid={`rig-${r.key}-${f}-${v}`}>{word(v)}</button>)}</div></div>)}
        {r.key === 'win' ? <NexaRuntime n={d.nexa} busy={busy} onAct={nexa} /> : <code className="mrg-cmd" title="Run where the model lives so its loaded context + slots match">{r.cmd}</code>}
      </section>; })}</div>
    {err ? <p className="mrg-err">{err}</p> : null}
  </div>;
}
