import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import '../../styles/mediaStudio.css';

// 🎬 PoC images and video (owner 2026-11-10): they run on the owner's OWN OpenRouter, fal.ai or Replicate account (staff agents: FEELESS's
// OpenRouter key, $2 a day). It opens IN the conversation, not over it: first the formats going viral right now, each with a real clip we
// made on that model, its price and how long it took; one tap makes that format from the folder's own words. Below: any model, your prompt.
// Every job's real state comes from the server (queued → in progress → done / failed), never a timer.
const STEP_WORD = { queued: 'waiting for its turn', in_queue: 'in line at the provider', in_progress: 'making it', starting: 'starting up', processing: 'making it' };
const PROV = { fal: 'fal.ai', replicate: 'Replicate', openrouter: 'OpenRouter' };
const usd = v => (v == null ? null : `$${Number(v).toFixed(v < 0.1 ? 3 : 2)}`);

export function MediaCard({ m }) {
  const md = m.media || {}; const live = md.status === 'queued' || md.status === 'running'; const [, tick] = useState(0);
  useEffect(() => { if (!live) return undefined; const t = setInterval(() => { if (!document.hidden) tick(n => n + 1); }, 1000); return () => clearInterval(t); }, [live]);
  const secs = Math.max(0, Math.round(Date.now() / 1000 - Number(md.at || 0)));
  return <figure className={`mst-card is-${md.status}`} data-testid={`media-${md.id}`}>
    <figcaption><b>{md.kind === 'video' ? '🎬' : '🖼'} {md.label}</b><small>{PROV[md.provider] || md.provider}{usd(md.paidUsd ?? md.usd) ? ` · ${md.paidUsd != null ? '' : 'about '}${usd(md.paidUsd ?? md.usd)}` : ''} · {md.house ? 'FEELESS key (staff)' : 'your account'}</small></figcaption>
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
  const provs = ['openrouter', 'fal', 'replicate'].filter(k => d.providers[k]); const [p, setP] = useState(provs[0]); const [key, setKey] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const pv = d.providers[p];
  const seal = async () => { setBusy(true); setErr(''); try { await act(cat, { action: 'api_key', provider: p, secret: key.trim() }); setKey(''); onLinked(); } catch (e) { setErr(e.message); } setBusy(false); };
  return <div className="mst-link" data-testid="media-link">
    <p className="mst-lead">Images and video run on <b>your own</b> account, so you pay the provider directly at its price and nothing goes through FEELESS credit. Three steps, once:</p>
    <div className="m-seg" role="radiogroup" aria-label="Which provider">{provs.map(k => <button key={k} type="button" role="radio" aria-checked={p === k} className={p === k ? 'is-on' : ''} onClick={() => setP(k)} data-testid={`media-prov-${k}`}>{d.providers[k].name}</button>)}</div>
    <ol className="mst-steps">
      <li style={{ '--i': 0 }}><b>Make an account</b><a className="m-btn" href={pv.signup} target="_blank" rel="noopener noreferrer">Open {pv.name} ↗</a><small>Add a few dollars of credit there; a 5 s viral clip is about $0.15, a picture about $0.04.</small></li>
      <li style={{ '--i': 1 }}><b>Create a key</b><a className="m-btn" href={pv.keys} target="_blank" rel="noopener noreferrer">Keys page ↗</a><small>{p === 'fal' ? 'Name it FEELESS. It looks like id:secret.' : p === 'openrouter' ? 'It starts with sk-or-.' : 'It starts with r8_.'}</small></li>
      <li style={{ '--i': 2 }}><b>Paste it here</b><span className="mst-key"><input className="m-input" type="password" autoComplete="off" spellCheck={false} value={key} onChange={e => setKey(e.target.value)} placeholder={p === 'fal' ? 'key-id:secret' : p === 'openrouter' ? 'sk-or-…' : 'r8_…'} aria-label={`${pv.name} key`} data-testid="media-key" />
        <button type="button" className="m-btn m-go" disabled={busy || key.trim().length < 20} onClick={seal} data-testid="media-key-save" data-tip="Sealed on the server; only the last 4 ever come back">Link</button></span><small>Sealed on the server. Remove it any time in API keys.</small></li>
    </ol>{err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}
  </div>;
}

// 🔥 one viral format: its real sample plays muted on loop (only while on screen), then label, trend, model, price, seconds
function Preset({ x, i, onMake, busy }) {
  const v = React.useRef(null);
  useEffect(() => { const el = v.current; if (!el || typeof IntersectionObserver === 'undefined') return undefined;
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) el.play?.()?.catch?.(() => {}); else el.pause?.(); }); io.observe(el); return () => io.disconnect(); }, []);
  return <li className="mst-preset" style={{ '--i': i }} data-testid={`media-preset-${x.id}`}>
    <span className="mst-thumb">{x.sample ? (x.kind === 'video' ? <video ref={v} src={x.sample} muted loop playsInline preload="metadata" aria-label={`${x.label}: a real ${x.modelLabel} result`} />
      : <img src={x.sample} alt={`${x.label}: a real ${x.modelLabel} result`} loading="lazy" decoding="async" />) : null}<em>{x.kind === 'video' ? '🎬' : '🖼'}</em></span>
    <b>{x.label}</b><small>{x.trend}</small>
    <span className="mst-meta"><i>{x.modelLabel}</i><i>{usd(x.usd)}</i>{x.secs ? <i>~{x.secs}s</i> : null}</span>
    <button type="button" className="m-btn m-go" disabled={busy || !x.ready} onClick={() => onMake(x)} data-testid={`media-make-${x.id}`} data-tip={x.ready ? `Makes a ${x.label} from this folder's words on ${x.modelLabel} (${usd(x.usd)})` : 'Link OpenRouter first'}>Make this</button>
  </li>;
}

export function MediaButton({ cat, row, work, doc, setDoc, seed = '' }) {
  const [open, setOpen] = useState(false); const [d, setD] = useState(null); const [kind, setKind] = useState('video'); const [model, setModel] = useState(''); const [text, setText] = useState(''); const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  const load = () => work(cat.id, { op: 'media_models' }).then(x => { setD(x); setErr(''); }).catch(e => setErr(e.message));
  useEffect(() => { if (open) { load(); if (!text && seed) setText(seed.slice(0, 600)); } }, [open]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  const rows = (d?.models || []).filter(m => m.kind === kind).sort((a, b) => Number(b.ready) - Number(a.ready)); /* what runs now first */ const pick = model && rows.some(m => m.id === model && m.ready) ? model : d?.pick?.[kind];
  const make = async () => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'media_make', job: row.id, text, tools: { kind, model: pick } }); setDoc(j.doc); setOpen(false); } catch (e) { setErr(e.message); } setBusy(false); };
  const makePreset = async x => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'media_make', job: row.id, text: text || seed || '', tools: { preset: x.id } }); setDoc(j.doc); setOpen(false); } catch (e) { setErr(e.message); } setBusy(false); };
  const making = (doc?.messages || []).filter(m => ['queued', 'running'].includes(m.media?.status)).length;
  return <>
    <button type="button" className={`m-btn mst-open${open ? ' is-on' : ''}`} aria-expanded={open} onClick={() => setOpen(o => !o)} data-testid="media-open" data-tip="Turn this folder into a viral-format image or video, right here in the chat">🎬 Image / video{making ? <em>{making} making</em> : null}</button>
    {open ? <div className="mst-inline" role="region" aria-label="Image or video" data-testid="media-pop">
      <section className="mst-pop m-pop">
        <header><b>🎬 Image / video</b><small>{d?.linked?.length && d.providers ? `on your ${d.linked.map(k => d.providers[k].name).join(' + ')}` : d?.house ? `FEELESS key · $${d.houseLeftUsd ?? 0} left today` : 'link your own account first'}</small><button type="button" className="m-btn" onClick={() => setOpen(false)} aria-label="Close" data-testid="media-close">✕</button></header>
        {!d?.providers ? <p className="mst-lead">{err ? `⚠ ${err}` : 'Reading your providers…'}</p> : !(d.linked || []).length && !d.house ? <LinkSteps cat={cat} d={d} onLinked={load} /> : <>
          {(d.presets || []).length ? <><p className="mst-h">🔥 Viral right now <small>real results we made on each model · one tap makes it from this folder</small></p>
            <ul className="mst-presets">{d.presets.map((x, i) => <Preset key={x.id} x={x} i={i} busy={busy} onMake={makePreset} />)}</ul>
            <p className="mst-h">Or your own <small>any model, your words</small></p></> : null}
          <div className="m-seg" role="radiogroup" aria-label="Image or video">{[['video', '🎬 Video'], ['image', '🖼 Image']].map(([k, l]) => <button key={k} type="button" role="radio" aria-checked={kind === k} className={kind === k ? 'is-on' : ''} onClick={() => { setKind(k); setModel(''); }} data-testid={`media-kind-${k}`}>{l}</button>)}</div>
          <ul className="mst-models">{rows.map((m, i) => <li key={m.id} style={{ '--i': i }}><button type="button" disabled={!m.ready} aria-pressed={pick === m.id} className={pick === m.id ? 'is-on' : ''} onClick={() => setModel(m.id)} data-testid={`media-model-${m.id}`}
            data-tip={m.ready ? m.why : `Link ${m.providerName} to use this`}><b>{m.label}</b><small>{m.providerName}{m.id === d.pick?.[kind] ? ' · cheap pick' : ''}</small><em>{usd(m.usd) || `price on ${m.providerName}`}</em></button></li>)}</ul>
          <textarea className="m-input" rows={4} value={text} onChange={e => setText(e.target.value)} placeholder={kind === 'video' ? 'A chrome rat dances on a tombstone at night, slow camera push, neon green rim light' : 'A chrome tombstone that reads GONE, studio light, black background'} aria-label="What to make" data-testid="media-prompt" />
          <div className="mst-go"><small>{(d.linked || []).length < 2 ? <>Also have the other one? <button type="button" className="fea-back-btn" onClick={() => setD({ ...d, linked: [] })}>Link it</button></> : 'Both linked'}</small>
            <button type="button" className="m-btn m-go" disabled={busy || !pick || text.trim().length < 3} onClick={make} data-testid="media-make">{busy ? 'Starting…' : `Make the ${kind}`}</button></div>
          {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}</>}
      </section></div> : null}
  </>;
}
