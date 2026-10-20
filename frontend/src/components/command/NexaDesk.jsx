import React, { useCallback, useEffect, useState } from 'react';
import { toast } from 'sonner';
import '../../styles/nexaDesk.css';

// 🪟 NEXA SICARIO's desk (HQ › Fee, owner only; backend/nexa.py): FeeCat's own model on the Windows PC. She reads FeeCat's book, the next coins,
// the web and the whole FEELESS brief every 5 min → avoid / exit (FeeCat acts, paper) · favor (graded) · tune FeeCat's rules (bounded, ≤ 1 an hour,
// only while YOUR switch is on, every change revertible). Her memory is a capped notebook she writes herself.
const ago = t => { if (!t) return '—'; const s = Date.now() / 1000 - t; return s < 60 ? `${Math.round(s)}s` : s < 3600 ? `${Math.round(s / 60)}m` : `${Math.round(s / 3600)}h`; };
export const nexaState = d => (!d ? 'loading' : !d.provider?.on ? 'offline' : d.busy ? 'thinking' : d.ok === false ? 'confused' : d.at ? 'live' : 'waking');
const WORD = { loading: 'reading…', offline: 'NOT CONNECTED', thinking: 'THINKING', confused: 'NO CLEAN ANSWER', live: 'ON THE DESK', waking: 'WAKING UP' };
const MEM_ICON = { lesson: '🧠', discovery: '🌐', grade: '📏' };
export function NexaDesk({ call }) {
  const [d, setD] = useState(null); const [busy, setBusy] = useState(false);
  const load = useCallback(() => call('/admin/nexa').then(setD).catch(() => {}), [call]);
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, 10000); return () => clearInterval(t); }, [load]);
  const act = body => { setBusy(true); return call('/admin/nexa', { method: 'POST', body: JSON.stringify(body) }).then(x => { setD(x); toast.success('🪟 Nexa updated'); }).catch(e => toast.error(e.message)).finally(() => setBusy(false)); };
  const st = nexaState(d); const L = d?.last || {}; const rec = d?.record || {}; const tuneOn = !!d?.cfg?.tune;
  return <section className={`nxd m-card is-${st}`} data-testid="nexa-desk">
    <header className="nxd-hero">
      <span className="nxd-orb" aria-hidden="true"><i /><i /><b>N</b></span>
      <span className="nxd-who"><b>NEXA SICARIO</b><small data-testid="nexa-state">{WORD[st]}{d?.at ? ` · last read ${ago(d.at)} ago${d.ms ? ` · ${(d.ms / 1000).toFixed(0)}s to think` : ''}` : ''}</small>
        <em>the Godfather's oldest · FeeCat's analyst + the family's discovery model · {d?.provider?.model || 'llamafile'} on the Windows PC · paper only</em></span>
      <span className="nxd-acts">
        <button type="button" className={`m-btn ${tuneOn ? 'is-on' : ''}`} disabled={busy || !d} aria-pressed={tuneOn} onClick={() => act({ tune: !tuneOn })} data-testid="nexa-tune"
          data-tip="On: Nexa may move FeeCat's own rules inside their bounds, one step, at most once an hour. Off: she only advises.">{tuneOn ? '🎛 Tuning FeeCat: ON' : '🎛 Let her tune FeeCat'}</button>
        <button type="button" className="m-btn" disabled={busy || !d?.provider?.on} onClick={() => act({ now: true })} data-testid="nexa-now">⚡ Read now</button>
      </span>
    </header>
    {st === 'offline' ? <p className="nxd-off" data-testid="nexa-off">🪟 {d?.provider?.why || 'Not reachable.'} — on the Windows PC run llamafile with <code>--server --host 0.0.0.0 --port 8080</code>, then set <code>WIN_LLM_BASE_URL=http://&lt;its-ip&gt;:8080/v1</code> in backend/.env and restart.</p> : null}
    {d?.err ? <p className="nxd-err">⚠ last read: {d.err}</p> : null}
    <div className="nxd-grid">
      <article className="nxd-card"><h4>🎯 HER CALL NOW</h4>
        {L.at ? <><p className="nxd-why">{L.why || '—'}</p>
          <p className="nxd-chips">{(L.avoid || []).map(p => <span key={`a${p}`} className="is-bad" data-tip="FeeCat won't buy it while this read is fresh">✋ skip {p.slice(0, 6)}…</span>)}
            {(L.exit || []).map(p => <span key={`e${p}`} className="is-gold" data-tip="FeeCat banks it if it's in profit">💰 bank {p.slice(0, 6)}…</span>)}
            {(L.favor || []).map(p => <span key={`f${p}`} className="is-good" data-tip="Graded an hour later — it earns her trust">⭐ likes {p.slice(0, 6)}…</span>)}
            {!(L.avoid || []).length && !(L.exit || []).length && !(L.favor || []).length ? <span>nothing to flag</span> : null}</p></>
          : <p className="nxd-dim">No read yet.</p>}
      </article>
      <article className="nxd-card"><h4>📏 HER RECORD</h4>
        {['favor', 'avoid'].map(k => { const r = rec[k] || {}; return <p key={k} className="nxd-rec"><b>{k === 'favor' ? '⭐ likes' : '✋ skips'}</b>
          <i className="nxd-bar"><u style={{ transform: `scaleX(${(r.rightPct || 0) / 100})` }} /></i><span>{r.n ? `${r.rightPct}% right · ${r.n} graded · typical ${r.typical > 0 ? '+' : ''}${r.typical}%` : 'not graded yet'}</span></p>; })}
      </article>
      <article className="nxd-card"><h4>🎛 WHAT SHE TUNED<small>{tuneOn ? 'switch on' : 'switch off — advice only'}</small></h4>
        {(d?.tunes || []).length ? <ul className="nxd-tunes">{d.tunes.slice().reverse().map((t, i) => <li key={t.at}><span>{Object.entries(t.set).map(([k, v]) => `${k} ${t.was?.[k]} → ${v}`).join(' · ')}</span><small>{ago(t.at)} ago</small>
          {i === 0 ? <button type="button" className="m-btn" disabled={busy} onClick={() => act({ revert: true })} data-testid="nexa-revert">↩ Revert</button> : null}</li>)}</ul>
          : <p className="nxd-dim">Nothing tuned yet.</p>}
      </article>
      <article className="nxd-card nxd-mem"><h4>📓 HER NOTEBOOK<small>{d?.memN || 0} notes · capped, she writes it herself</small>
        {d?.memN ? <button type="button" className="nxd-x" disabled={busy} onClick={() => window.confirm('Wipe Nexa\'s notebook?') && act({ forget: true })}>wipe</button> : null}</h4>
        {(d?.memory || []).length ? <ol>{d.memory.slice().reverse().slice(0, 14).map(m => <li key={`${m.at}-${m.text}`} className={`k-${m.kind}`}><i>{MEM_ICON[m.kind] || '•'}</i><span>{m.text}</span><small>{ago(m.at)}</small></li>)}</ol>
          : <p className="nxd-dim">Empty — her lessons and discoveries land here after each read.</p>}
      </article>
    </div>
    <p className="nxd-real" data-testid="nexa-real">💵 Real money: {d?.real?.why || 'FeeCat trades paper.'}</p>
  </section>;
}
