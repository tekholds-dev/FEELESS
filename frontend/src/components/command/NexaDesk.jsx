import React, { useCallback, useEffect, useState } from 'react';
import { ModelRig } from './ModelRig';
import { AiChat } from './AiChat';
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
      <article className="nxd-card nxd-kb" data-testid="nexa-kb"><h4>🧠 DISCOVERY BASE<small>{d?.kb ? `${d.kb.total} facts · ${d.kb.kb} KB` : 'empty'} · she searches only for what it lacks</small></h4>
        {d?.kb ? <div className="nxd-kbbars">{Object.entries(d.kb.n || {}).map(([c, n], i) => <span key={c} style={{ '--i': i }}><em>{c}</em>
          <i><u style={{ transform: `scaleX(${Math.min(1, n / ((d.kb.caps || {})[c] || 1))})` }} /></i><b>{n}</b></span>)}</div> : null}
        {(d?.kb?.latest || []).length ? <ol>{d.kb.latest.slice(0, 10).map(f => <li key={`${f.cat}-${f.key}`}><i>{f.src === 'nexa' ? '🪟' : '⚙'}</i><span><b>{f.cat}</b> {f.fact}</span><small>{ago(f.at)}</small></li>)}</ol>
          : <p className="nxd-dim">Fills as she reads: every coin FEELESS shows her, every fact she chooses to keep.</p>}
      </article>
    </div>
    <p className="nxd-real" data-testid="nexa-real">💵 Real money: {d?.real?.why || 'FeeCat trades paper.'}</p>
    <details className="nxd-chat" data-testid="nexa-chat" open><summary>💬 Talk to Nexa <small>she answers from her own FeeCat desk — record, last read, tunes, notebook</small></summary>
      <div className="nxd-chatrow"><NexaVitals call={call} desk={d} /><div className="nxd-chatbox"><AiChat call={call} variant="mini" lockProvider="win" title="🪟 NEXA" /></div></div></details>
  </section>;
}

// 🪟 NEXA LIVE (owner, 2026-10-21: "see Nexa's realtime vitals and loading beside the chat"): her call in flight on a line against its real
// deadline, what her llamafile is actually running (from the Model Rig's /props + /slots read), her last calls and how many she answered.
export function nexaStats(calls) {
  const mine = (calls?.log || []).filter(r => r.prov === 'win');
  const ok = mine.filter(r => r.ok);
  const ms = ok.map(r => r.ms).filter(Boolean).sort((a, b) => a - b);
  return { n: mine.length, ok: ok.length, rate: mine.length ? Math.round((100 * ok.length) / mine.length) : null, med: ms.length ? ms[Math.floor(ms.length / 2)] : null,
    flight: (calls?.inflight || []).filter(x => x.prov === 'win'), recent: mine.slice(0, 5) };
}
// pure: her background reads as bars — height = seconds against the 240 s line (sqrt so a 2 s read still shows), fast vs full, failed
export function readBars(reads, lim = 240) {
  return (reads || []).slice(-16).map(r => ({ h: Math.max(0.06, Math.min(1, Math.sqrt((Number(r.ms) || 0) / 1000 / lim))), mode: r.mode === 'full' ? 'full' : 'fast', ok: r.ok !== false, sec: Math.round((Number(r.ms) || 0) / 1000), at: r.at }));
}
export function NexaVitals({ call, desk }) {
  const [c, setC] = React.useState(null); const [rig, setRig] = React.useState(null);
  React.useEffect(() => {
    let on = true; let t = null; let n = 0;
    const tick = async () => {
      try { const r = await call('/admin/ai/calls'); if (on) setC(r); } catch { /* keep the last */ }
      if (n++ % 8 === 0) { try { const r = await call('/admin/ai/rig'); if (on) setRig(r); } catch { /* keep */ } }
      if (on) t = setTimeout(tick, document.hidden ? 8000 : 2000);
    };
    tick(); return () => { on = false; clearTimeout(t); };
  }, [call]);
  const st = nexaStats(c); const nx = rig?.nexa; const live = rig?.live?.win || {};
  const lim = (c?.limits || {}).win || 240;
  return <aside className="nxd-vit" data-testid="nexa-vitals">
    <header><i className="nxd-orb" aria-hidden /><b>NEXA</b><span className={`nxd-st s-${String(live.state || 'untested').toLowerCase().replace(/\s+/g, '-')}`}>{live.state || 'UNTESTED'}</span></header>
    {st.flight.length ? st.flight.map(x => { const fill = Math.min(1, (x.sec || 0) / lim); const tick = x.typical ? Math.min(1, x.typical / lim) : null;
      return <div key={x.at} className="nxd-line" data-testid="nexa-line"><span><i style={{ transform: `scaleX(${Math.max(0.02, fill)})` }} />{tick != null ? <b style={{ left: `${tick * 100}%` }} aria-hidden /> : null}</span>
        <small>{x.role || 'call'} · {Math.round(x.sec || 0)}s of {lim}s{x.typical ? ` · typical ${Math.round(x.typical)}s` : ''}</small></div>; })
      : <p className="nxd-idle">idle{st.med ? ` · answers in ~${(st.med / 1000).toFixed(0)}s` : ''}</p>}
    <div className="nxd-vg">
      <span><em>RUNNING</em><b>{nx?.actual ? `${(nx.actual.ctx / 1024).toFixed(0)}K × ${nx.actual.slots}` : '—'}</b></span>
      <span><em>WANTED</em><b>{nx?.desired ? `${(nx.desired.ctx / 1024).toFixed(0)}K × ${nx.desired.slots}` : 'auto'}</b></span>
      <span><em>ANSWERED</em><b>{st.rate == null ? '—' : `${st.rate}%`}</b><small>{st.ok}/{st.n}</small></span>
      <span><em>TYPICAL</em><b>{st.med ? `${(st.med / 1000).toFixed(0)}s` : '—'}</b></span>
    </div>
    {nx ? <p className={`nxd-rt is-${nx.state}`}>{nx.state === 'active' ? '✅ runtime matches the rig' : nx.state === 'applying' ? '⏳ restarting her llamafile…' : nx.state === 'unreachable' ? '✕ her llamafile is not answering' : '⚠ runtime differs from the rig'}</p> : null}
    {desk?.reads?.length ? <div className="nxd-reads" data-tip="Her background reads: ⚡ fast = numbers only (most), ◆ full = tune + lesson, once an hour. Taller = slower.">
      <em>HER READS<b>{desk.mode === 'full' ? '◆ full' : '⚡ fast'} · {desk.ms ? `${Math.round(desk.ms / 1000)}s` : '—'}</b></em>
      <span>{readBars(desk.reads).map((r, i) => <i key={`${r.at}-${i}`} className={`is-${r.mode} ${r.ok ? '' : 'is-err'}`} style={{ transform: `scaleY(${r.h})`, '--i': i }} title={`${r.mode} · ${r.sec}s${r.ok ? '' : ' · no answer'}`} />)}</span></div> : null}
    <ol className="nxd-calls">{st.recent.map((r, i) => <li key={`${r.at}-${i}`} className={r.ok ? '' : 'is-err'}><b>{r.role || 'call'}</b><span>{(r.ms / 1000).toFixed(0)}s</span><small>{r.ok ? '✓' : '✕'}</small></li>)}</ol>
    <details className="nxd-rig" data-testid="nexa-rig"><summary data-tip="NEXA's model settings right here: what FEELESS sends her, her llamafile runtime, presets">⚙ HER MODEL · settings + presets</summary>
      <ModelRig call={call} only="win" /></details>
  </aside>;
}
