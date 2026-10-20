import React, { useEffect, useState } from 'react';
import '../../styles/modelLive.css';
import { ModelRig } from './ModelRig';

// 🧠 THE MODELS, LIVE (owner, 2026-10-19: "real time loading % and vital prompt log from G4 and OSSY in brain"): every call in flight with
// its % = elapsed ÷ that model's OWN average answer time (it waits at 99% until the answer lands — never a fake finish), then the last 30
// calls: who, the job, how long, tokens, and the head of what it was sent + answered (keys / addresses masked server-side).
export const NAME = { lan: 'G4', local: 'OSSY' };
export const who = (prov, names) => (names || {})[prov] || NAME[prov] || String(prov || '?').toUpperCase();
export const ago = (at, now = Date.now() / 1000) => { const s = Math.max(0, Math.round(now - at)); return s < 60 ? `${s}s` : s < 3600 ? `${Math.floor(s / 60)}m` : `${Math.floor(s / 3600)}h`; };

export function ModelLive({ call }) {
  const [d, setD] = useState(null); const [open, setOpen] = useState(null);
  useEffect(() => {
    let on = true; let t = null;
    const load = async () => { try { const r = await call('/admin/ai/calls'); if (on) setD(r); } catch { /* keep the last */ } if (on) t = setTimeout(load, document.hidden ? 8000 : 1500); };
    load();
    return () => { on = false; clearTimeout(t); };
  }, [call]);
  if (!d) return <p className="mlv-wait" data-testid="mlv-wait">reading the models…</p>;
  const fl = d.inflight || []; const log = d.log || [];
  return <div className="mlv" data-testid="model-live"><ModelRig call={call} />
    <section className="mlv-now">
      <h5>⚡ THINKING NOW <small>{fl.length ? `${fl.length} call${fl.length > 1 ? 's' : ''} in flight` : 'nobody is thinking this second'}</small></h5>
      {['lan', 'local'].map(k => { const f = fl.filter(x => x.prov === k); const a = (d.avgMs || {})[k];
        return <div key={k} className={`mlv-row ${f.length ? 'is-on' : ''} p-${k}`} data-testid={`mlv-${k}`}>
          <b>{who(k, d.names)}</b>
          {f.length ? f.map(x => <span key={x.at} className="mlv-bar" title={`${x.role || 'call'} · ${x.sec}s of a typical ${x.typical}s`}>
            <i style={{ transform: `scaleX(${Math.max(0.02, x.pct / 100)})` }} /><em>{x.pct}% · {x.role || 'call'} · {x.sec}s</em></span>)
            : <span className="mlv-idle">idle{a ? ` · answers in ~${(a / 1000).toFixed(1)}s` : ''}</span>}
        </div>; })}
      {fl.filter(x => x.prov !== 'lan' && x.prov !== 'local').map(x => <div key={x.at} className="mlv-row is-on"><b>{who(x.prov, d.names)}</b><span className="mlv-bar"><i style={{ transform: `scaleX(${Math.max(0.02, x.pct / 100)})` }} /><em>{x.pct}% · {x.role || 'call'}</em></span></div>)}
    </section>
    <section className="mlv-log">
      <h5>📜 PROMPT LOG <small>last {log.length} · tap one to read what it was sent</small></h5>
      <ol>{log.map((r, i) => { const k = `${r.at}-${r.prov}-${i}`; const o = open === k;
        return <li key={k} className={`${r.ok ? '' : 'is-err'} p-${r.prov} ${o ? 'is-open' : ''}`} data-testid="mlv-call">
          <button type="button" onClick={() => setOpen(o ? null : k)} aria-expanded={o}>
            <b>{who(r.prov, d.names)}</b><span>{r.role || 'call'}</span><span>{(r.ms / 1000).toFixed(1)}s</span><span>~{r.tok} tok</span><span className="mlv-ago">{ago(r.at)}</span>
            <em>{r.ok ? (r.answer || '—').slice(0, 90) : `✕ ${r.err}`}</em>
          </button>
          {o ? <div className="mlv-body"><p><small>SENT</small>{r.prompt || '—'}</p><p><small>ANSWER</small>{r.ok ? r.answer : r.err}</p><p className="mlv-sys"><small>SYSTEM</small>{r.system}</p></div> : null}
        </li>; })}</ol>
    </section>
  </div>;
}
