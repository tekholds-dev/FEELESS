import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/modelRig.css';

// 🎛 MODEL RIG (Brain › Models): G4 · OSSY · NEXA side by side — context budget, parallel slots, timeout, background calls a minute (Nexa: how
// often she reads). Saved = live at once (no restart, nothing reloaded). The load command under each card is what makes the MODEL match it.
const FIELDS = [['ctx', '🧠 CONTEXT', v => (v ? `${v / 1024}K` : 'auto')], ['parallel', '⚡ SLOTS', v => `×${v}`], ['timeout', '⏱ TIMEOUT', v => `${v}s`],
  ['perMin', '📞 CALLS / MIN', v => `${v}`], ['every', '🔁 READ EVERY', v => `${v / 60}m`]];
const AV = { lan: '/assets/ai-pfp/g4.gif', local: '/assets/ai-pfp/ossy.gif', win: null };

export function ModelRig({ call }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(''); const [err, setErr] = useState('');
  const load = useCallback(() => call('/admin/ai/rig').then(setD).catch(e => setErr(String(e?.message || e))), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 20000); return () => clearInterval(t); }, [load]);
  const save = async (key, f, v) => {
    setBusy(`${key}.${f}`);
    try { setD(await call('/admin/ai/rig', { method: 'POST', body: JSON.stringify({ [key]: { [f]: v } }) })); setErr(''); } catch (e) { setErr(String(e?.message || e)); }
    setBusy('');
  };
  if (!d?.rows) return <p className="mrg-wait">{err || 'reading the rig…'}</p>;
  return <div className="mrg" data-testid="model-rig">
    <p className="mrg-head"><b>🎛 MODEL RIG</b><small>what FEELESS sends each model · live at once · the model's own load settings below each card</small></p>
    <div className="mrg-grid">{d.rows.map((r, i) => { const lv = d.live?.[r.key] || {};
      return <section key={r.key} className={`mrg-card k-${r.key}`} style={{ '--i': i }} data-testid={`rig-${r.key}`}>
        <header>{AV[r.key] ? <img src={AV[r.key]} alt="" /> : <i className="mrg-av">🪟</i>}<b>{r.name}</b>
          <span className={`mrg-st s-${String(lv.state || 'untested').toLowerCase().replace(/\s+/g, '-')}`}>{lv.state || 'UNTESTED'}{lv.lastMs ? ` · ${(lv.lastMs / 1000).toFixed(1)}s` : ''}</span></header>
        {FIELDS.filter(([f]) => r[f] !== undefined).map(([f, label, word]) => <div key={f} className="mrg-row"><em>{label}</em>
          <div className="mrg-seg">{(d.options[f] || []).map(v => <button key={v} type="button" className={r[f] === v ? 'active' : ''} disabled={!!busy}
            aria-busy={busy === `${r.key}.${f}`} onClick={() => save(r.key, f, v)} data-testid={`rig-${r.key}-${f}-${v}`}>{word(v)}</button>)}</div></div>)}
        <code className="mrg-cmd" title="Run where the model lives so its loaded context + slots match">{r.cmd}</code>
      </section>; })}</div>
    {err ? <p className="mrg-err">{err}</p> : null}
  </div>;
}
