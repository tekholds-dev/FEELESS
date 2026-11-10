import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import '../../styles/mediaStudio.css';

// 🎬 PoC images and video (owner 2026-11-10): they run on the owner's OWN fal.ai or Replicate account, so users can make real
// characters, clips and posts as cheap as the newest models allow. Not linked yet → a 3-step link. Linked → pick, prompt, make.
// Every job's real state comes from the server (queued → in progress → done / failed), never a timer.
const STEP_WORD = { queued: 'waiting for its turn', in_queue: 'in line at the provider', in_progress: 'making it', starting: 'starting up', processing: 'making it' };
const usd = v => (v == null ? null : `$${Number(v).toFixed(v < 0.1 ? 3 : 2)}`);

export function MediaCard({ m }) {
  const md = m.media || {}; const live = md.status === 'queued' || md.status === 'running'; const [, tick] = useState(0);
  useEffect(() => { if (!live) return undefined; const t = setInterval(() => { if (!document.hidden) tick(n => n + 1); }, 1000); return () => clearInterval(t); }, [live]);
  const secs = Math.max(0, Math.round(Date.now() / 1000 - Number(md.at || 0)));
  return <figure className={`mst-card is-${md.status}`} data-testid={`media-${md.id}`}>
    <figcaption><b>{md.kind === 'video' ? '🎬' : '🖼'} {md.label}</b><small>{md.provider === 'fal' ? 'fal.ai' : 'Replicate'}{usd(md.usd) ? ` · about ${usd(md.usd)}` : ''} · your account</small></figcaption>
    {md.status === 'done' && md.url ? (md.kind === 'video'
      ? <video src={apiUrl(md.url)} controls playsInline preload="metadata" data-testid="media-video" />
      : <img src={apiUrl(md.url)} alt={md.prompt} loading="lazy" data-testid="media-image" />) : null}
    {live ? <div className="mst-wait" role="status"><span>{STEP_WORD[md.step] || STEP_WORD[md.status] || md.step || 'working'} · {secs >= 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${secs}s`}</span><i aria-hidden="true"><u /></i></div> : null}
    {md.status === 'failed' ? <p className="kd-err" role="alert">⚠ {md.why || 'It did not finish.'} Nothing more is charged.</p> : null}
    <p className="mst-prompt">{md.prompt}</p>
    {md.status === 'done' && md.url ? <a className="m-btn" href={apiUrl(md.url)} download target="_blank" rel="noopener noreferrer" data-tip="Save the file" data-testid="media-save">Save</a> : null}
    {md.status === 'done' && md.kept === false ? <small className="mst-note">{md.why}</small> : null}
  </figure>;
}

async function act(cat, body) {
  const r = await fetch(apiUrl(`/api/cats/${cat.id}/action`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), ...body }) });
  const j = await r.json().catch(() => ({})); if (!r.ok) throw new Error(j.detail || `HTTP ${r.status}`); return j;
}

function LinkSteps({ cat, d, onLinked }) {
  const [p, setP] = useState('fal'); const [key, setKey] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const pv = d.providers[p];
  const seal = async () => { setBusy(true); setErr(''); try { await act(cat, { action: 'api_key', provider: p, secret: key.trim() }); setKey(''); onLinked(); } catch (e) { setErr(e.message); } setBusy(false); };
  return <div className="mst-link" data-testid="media-link">
    <p className="mst-lead">Images and video run on <b>your own</b> account, so you pay the provider directly at its price and nothing goes through FEELESS credit. Three steps, once:</p>
    <div className="m-seg" role="radiogroup" aria-label="Which provider">{['fal', 'replicate'].map(k => <button key={k} type="button" role="radio" aria-checked={p === k} className={p === k ? 'is-on' : ''} onClick={() => setP(k)} data-testid={`media-prov-${k}`}>{d.providers[k].name}</button>)}</div>
    <ol className="mst-steps">
      <li style={{ '--i': 0 }}><b>Make an account</b><a className="m-btn" href={pv.signup} target="_blank" rel="noopener noreferrer">Open {pv.name} ↗</a><small>Add a few dollars of credit there; a short Wan clip is about $0.15.</small></li>
      <li style={{ '--i': 1 }}><b>Create a key</b><a className="m-btn" href={pv.keys} target="_blank" rel="noopener noreferrer">Keys page ↗</a><small>{p === 'fal' ? 'Name it FEELESS. It looks like id:secret.' : 'It starts with r8_.'}</small></li>
      <li style={{ '--i': 2 }}><b>Paste it here</b><span className="mst-key"><input className="m-input" type="password" autoComplete="off" spellCheck={false} value={key} onChange={e => setKey(e.target.value)} placeholder={p === 'fal' ? 'key-id:secret' : 'r8_…'} aria-label={`${pv.name} key`} data-testid="media-key" />
        <button type="button" className="m-btn m-go" disabled={busy || key.trim().length < 20} onClick={seal} data-testid="media-key-save" data-tip="Sealed on the server; only the last 4 ever come back">Link</button></span><small>Sealed on the server. Remove it any time in API keys.</small></li>
    </ol>{err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </div>;
}

export function MediaButton({ cat, row, work, doc, setDoc, seed = '' }) {
  const [open, setOpen] = useState(false); const [d, setD] = useState(null); const [kind, setKind] = useState('video'); const [model, setModel] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const load = () => work(cat.id, { op: 'media_models' }).then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message));
  useEffect(() => { if (open) { load(); if (!text && seed) setText(seed.slice(0, 600)); } }, [open]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  const rows = (d?.models || []).filter(m => m.kind === kind); const pick = model && rows.some(m => m.id === model && m.ready) ? model : d?.pick?.[kind];
  const make = async () => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'media_make', job: row.id, text, tools: { kind, model: pick } }); setDoc(j.doc); setOpen(false); } catch (e) { setErr(e.message); } setBusy(false); };
  const making = (doc?.messages || []).filter(m => ['queued', 'running'].includes(m.media?.status)).length;
  return <>
    <button type="button" className="m-btn mst-open" onClick={() => setOpen(true)} data-testid="media-open" data-tip="Make an AI image or video on your own fal.ai or Replicate account">🎬 Image / video{making ? <em>{making} making</em> : null}</button>
    {open ? createPortal(<div className="lct-pop" role="dialog" aria-modal="true" aria-label="Image or video" onClick={e => e.target === e.currentTarget && setOpen(false)} data-testid="media-pop">
      <section className="mst-pop m-pop">
        <header><b>🎬 Image / video</b><small>{d?.linked?.length && d.providers ? `on your ${d.linked.map(k => d.providers[k].name).join(' + ')}` : 'link your own account first'}</small><button type="button" className="m-btn" onClick={() => setOpen(false)} aria-label="Close" data-testid="media-close">✕</button></header>
        {!d?.providers ? <p className="mst-lead">{err ? `⚠ ${err}` : 'Reading your providers…'}</p> : !(d.linked || []).length ? <LinkSteps cat={cat} d={d} onLinked={load} /> : <>
          <div className="m-seg" role="radiogroup" aria-label="Image or video">{[['video', '🎬 Video'], ['image', '🖼 Image']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={kind === k} className={kind === k ? 'is-on' : ''} onClick={() => { setKind(k); setModel(''); }} data-testid={`media-kind-${k}`}>{l}</button>)}</div>
          <ul className="mst-models">{rows.map((m, i) => <li key={m.id} style={{ '--i': i }}><button type="button" disabled={!m.ready} aria-pressed={pick === m.id} className={pick === m.id ? 'is-on' : ''} onClick={() => setModel(m.id)} data-testid={`media-model-${m.id}`}
            data-tip={m.ready ? m.why : `Link ${m.providerName} to use this`}><b>{m.label}</b><small>{m.providerName}{m.id === d.pick?.[kind] ? ' · cheap pick' : ''}</small><em>{usd(m.usd) || `price on ${m.providerName}`}</em></button></li>)}</ul>
          <textarea className="m-input" rows={4} value={text} onChange={e => setText(e.target.value)} placeholder={kind === 'video' ? 'A chrome rat dances on a tombstone at night, slow camera push, neon green rim light' : 'A chrome tombstone that reads GONE, studio light, black background'} aria-label="What to make" data-testid="media-prompt" />
          <div className="mst-go"><small>{(d.linked || []).length < 2 ? <>Also have the other one? <button type="button" className="fea-back-btn" onClick={() => setD({ ...d, linked: [] })}>Link it</button></> : 'Both linked'}</small>
            <button type="button" className="m-btn m-go" disabled={busy || !pick || text.trim().length < 3} onClick={make} data-testid="media-make">{busy ? 'Starting…' : `Make the ${kind}`}</button></div>
          {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}</>}
      </section></div>, document.body) : null}
  </>;
}
