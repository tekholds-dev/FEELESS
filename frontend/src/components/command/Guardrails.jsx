import React, { useCallback, useEffect, useState } from 'react';
import '../../styles/guardrails.css';

// 🛡 AGX-7 · YOUR GUARDRAILS (owner only, 2026-11-14): every limit COMP and the agents run under, one switch each (+ its number). The
// server enforces them; no agent reads or writes them. Restrict-only: a number can go DOWN from today's, never up — so this panel can
// tighten, never loosen. CLAUDE.md's hard limits sit below it, locked.
export function Guardrails({ call }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(''); const [busy, setBusy] = useState(''); const [draft, setDraft] = useState({});
  const load = useCallback(() => (call ? call('/admin/guardrails').then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message)) : Promise.resolve()), [call]);
  useEffect(() => { load(); }, [load]);
  const put = async (key, row) => { setBusy(key); try { setD(await call('/admin/guardrails', { method: 'POST', body: JSON.stringify({ [key]: row }) })); setErr(''); setDraft(x => ({ ...x, [key]: undefined })); } catch (e) { setErr(e.message); } finally { setBusy(''); } };
  if (!d) return <div className="grl" data-testid="grl">{err ? <p className="kd-err" role="alert">⚠ {err}</p> : <p className="mlb-none">Reading your guardrails…</p>}</div>;
  const tight = d.switches.filter(s => !s.on || (s.max != null && s.value < s.max)).length;
  return <div className="grl" data-testid="grl">
    <header className="grl-head"><span><small className="m-label">YOUR GUARDRAILS · OWNER ONLY</small><b>{tight ? `${tight} tightened` : 'All at today\'s settings'}</b></span>
      <small>The server enforces these. No agent can read or change them, and a number here only goes down from today's.</small></header>
    {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
    <ul className="grl-list">{d.switches.map((s, i) => { const v = draft[s.key] ?? s.value; const changed = s.max != null && Number(v) !== Number(s.value);
      return <li key={s.key} className={s.on ? 'is-on' : 'is-off'} style={{ '--i': i }} data-testid={`grl-${s.key}`}>
        <span className="grl-say"><b>{s.label}</b><small>{s.say}</small></span>
        {s.max != null ? <label className="grl-val" data-tip={`Today's number is ${s.max}${s.unit === '$' ? ' $' : ''}. It can go down to ${s.min}, never above ${s.max}`}>
          {s.unit === '$' ? <em>$</em> : null}<input type="number" className="m-input" min={s.min} max={s.max} step={s.unit === '$' ? 0.005 : 1} value={v ?? ''} disabled={!s.on || !!busy}
            onChange={e => setDraft(x => ({ ...x, [s.key]: e.target.value }))} aria-label={`${s.label} (most ${s.max})`} data-testid={`grl-val-${s.key}`} />
          {s.unit && s.unit !== '$' ? <em>{s.unit}</em> : null}
          {changed ? <button type="button" className="m-btn m-go" disabled={!!busy} onClick={() => put(s.key, { value: Number(v) })} data-testid={`grl-save-${s.key}`}>Save</button> : <small>of {s.max}</small>}</label> : <span />}
        <button type="button" className={`m-toggle grl-sw${s.on ? ' is-on' : ''}`} role="switch" aria-checked={s.on} disabled={!!busy} onClick={() => put(s.key, { on: !s.on })}
          data-tip={s.on ? 'On: today\'s behaviour. Tap to switch it off' : 'Off: tap to allow it again'} data-testid={`grl-on-${s.key}`}><i aria-hidden="true" />{s.on ? 'ON' : 'OFF'}</button>
      </li>; })}</ul>
    <section className="grl-hard" data-testid="grl-hard"><h4>🔒 HARD LIMITS · LOCKED<small>CLAUDE.md §1: changed only by editing that file, never here</small></h4>
      <ul>{d.hard.map((h, i) => <li key={h.t} style={{ '--i': i }}><b>{h.t}</b><small>{h.say}</small><em aria-label="locked">🔒</em></li>)}</ul></section>
  </div>;
}
