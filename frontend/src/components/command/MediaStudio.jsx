import React, { Suspense, lazy, useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { agentAuth } from '../../lib/chatSession';
import '../../styles/mediaStudio.css';

const PocPlay = lazy(() => import('./PocPlay'));   // 🎨 its own chunk: Konva loads only when a playground opens

// 🎬 PoC images and video (owner 2026-11-10): they run on the owner's OWN OpenRouter, fal.ai or Replicate account (staff agents: FEELESS's
// OpenRouter key, $2 a day). It opens IN the conversation, not over it: first the formats going viral right now, each with a real clip we
// made on that model, its price and how long it took; one tap makes that format from the folder's own words. Below: any model, your prompt.
// Every job's real state comes from the server (queued → in progress → done / failed), never a timer.
const STEP_WORD = { queued: 'waiting for its turn', in_queue: 'in line at the provider', in_progress: 'making it', starting: 'starting up', processing: 'making it' };
const PROV = { fal: 'fal.ai', replicate: 'Replicate', openrouter: 'OpenRouter' };
const usd = v => (v == null ? null : `$${Number(v).toFixed(v < 0.1 ? 3 : 2)}`);

export function MediaCard({ m, cat, doc, work, setDoc }) {
  const md = m.media || {}; const live = md.status === 'queued' || md.status === 'running'; const [, tick] = useState(0);
  const [busy, setBusy] = useState(false); const [err, setErr] = useState('');
  useEffect(() => { if (!live) return undefined; const t = setInterval(() => { if (!document.hidden) tick(n => n + 1); }, 1000); return () => clearInterval(t); }, [live]);
  const secs = Math.max(0, Math.round(Date.now() / 1000 - Number(md.at || 0)));
  // 👤 a finished image becomes a person: one tap animates him (Seedance-grade i2v), one keeps him as the folder's character for every video after
  const canLife = !!(cat && doc && work && setDoc) && md.status === 'done' && md.kind === 'image' && md.kept !== false && md.url;
  const isChar = canLife && doc?.character?.mid === md.id;
  const run = async body => { setBusy(true); setErr(''); try { const j = await work(cat.id, body); setDoc(j.doc); } catch (e) { setErr(e.message); } setBusy(false); };
  // 🎨 POC-PLAY: any finished picture or video opens in the playground; Save files the edit back into this proof as a new version
  const canPlay = !!(cat && doc && work && setDoc) && md.status === 'done' && !!md.url; const [play, setPlay] = useState(false);
  const pics = canPlay && play ? (doc.messages || []).map(x => x.media).filter(x => x && x.status === 'done' && x.url && x.kind !== 'video' && x.id !== md.id).map(x => ({ ...x, url: apiUrl(x.url) })) : [];
  const savePlay = async (dataUrl, template) => { const j = await work(cat.id, { op: 'media_play', job: doc.id, text: dataUrl, tools: { from: md.id, template } }); setDoc(j.doc); };
  return <figure className={`mst-card is-${md.status}${md.fromImg ? ' is-fromimg' : ''}`} data-testid={`media-${md.id}`}>
    <figcaption><b>{md.kind === 'video' ? '🎬' : '🖼'} {md.label}</b><small>{PROV[md.provider] || md.provider}{usd(md.paidUsd ?? md.usd) ? ` · ${md.paidUsd != null ? '' : 'about '}${usd(md.paidUsd ?? md.usd)}` : ''} · {md.house ? 'FEELESS key (staff)' : 'your account'}{md.fromImg ? ' · from your image' : ''}</small>{isChar ? <em className="mst-char-on" data-testid="media-ischar">👤 THE CHARACTER</em> : null}</figcaption>
    {md.status === 'done' && md.url ? (md.kind === 'video'
      ? <video src={apiUrl(md.url)} controls playsInline preload="metadata" data-testid="media-video" />
      : <img src={apiUrl(md.url)} alt={md.prompt} loading="lazy" data-testid="media-image" />) : null}
    {live ? <div className="mst-wait" role="status"><span>{STEP_WORD[md.step] || STEP_WORD[md.status] || md.step || 'working'} · {secs >= 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${secs}s`}</span><i aria-hidden="true"><u /></i></div> : null}
    {md.status === 'failed' ? <p className="kd-err" role="alert">⚠ {md.why || 'It did not finish.'} Nothing more is charged.</p> : null}
    <p className="mst-prompt">{md.prompt}</p>
    {md.status === 'done' && md.url ? <span className="mst-acts">
      <a className="m-btn" href={apiUrl(md.url)} download target="_blank" rel="noopener noreferrer" data-tip="Save the file" data-testid="media-save">Save</a>
      {canLife ? <button type="button" className="m-btn m-go" disabled={busy} data-testid="media-life"
        data-tip="Makes a video that STARTS from this exact image (Seedance): same face, same clothes, now moving. On your account."
        onClick={() => run({ op: 'media_make', job: doc.id, text: `This exact person comes alive and moves naturally — same face, same clothes, same jewelry, photoreal: ${String(md.prompt || '').slice(0, 300)}`, tools: { kind: 'video', img: md.id } })}>{busy ? 'Starting…' : '🎬 Bring to life'}</button> : null}
      {canPlay ? <button type="button" className="m-btn" onClick={() => setPlay(true)} data-testid="media-play"
        data-tip="Open it in the playground: move, crop, add text and badges, put it on a phone or billboard, then save a new version">🎨 Playground</button> : null}
      {canLife ? <button type="button" className="m-btn" disabled={busy} aria-pressed={isChar} data-testid="media-char"
        data-tip={isChar ? 'He stops leading this folder\'s videos' : 'Every video made in this folder starts from him: one consistent guy for all your content'}
        onClick={() => run({ op: 'media_char', job: doc.id, text: isChar ? '' : md.id })}>{isChar ? '👤 Unset character' : '👤 Make him the character'}</button> : null}
    </span> : null}
    {err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}
    {play ? createPortal(<Suspense fallback={<div className="ppl ppl-wait" role="status">Opening the playground…</div>}>
      <PocPlay src={apiUrl(md.url)} kind={md.kind} from={md.id} title={md.label || 'Picture'} media={pics} onSave={savePlay} onClose={() => setPlay(false)} /></Suspense>, document.body) : null}
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
  const [noChar, setNoChar] = useState(false);   // 👤 the folder's character leads its videos unless this make says no
  const charOn = kind === 'video' && doc?.character?.mid && !noChar;
  const make = async () => { setBusy(true); setErr(''); try { const j = await work(cat.id, { op: 'media_make', job: row.id, text, tools: { kind, model: pick, ...(kind === 'video' && noChar ? { noChar: true } : {}) } }); setDoc(j.doc); setOpen(false); } catch (e) { setErr(e.message); } setBusy(false); };
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
          {kind === 'video' && doc?.character?.mid ? <p className={`mst-charline${charOn ? ' is-on' : ''}`} data-testid="media-charline"><img src={apiUrl(doc.character.url)} alt="The folder's character" loading="lazy" /><b>{charOn ? 'Starts from your character' : 'Your character sits this one out'}</b>
            <button type="button" className="m-btn" onClick={() => setNoChar(v => !v)} data-tip={charOn ? 'This video is made from the words alone' : 'This video starts from his image again'} data-testid="media-nochar">{charOn ? 'Not this time' : 'Use him'}</button></p> : null}
          <div className="mst-go"><small>{(d.linked || []).length < 2 ? <>Also have the other one? <button type="button" className="fea-back-btn" onClick={() => setD({ ...d, linked: [] })}>Link it</button></> : 'Both linked'}</small>
            <button type="button" className="m-btn m-go" disabled={busy || !pick || text.trim().length < 3} onClick={make} data-testid="media-make">{busy ? 'Starting…' : `Make the ${kind}`}</button></div>
          {err ? <p className="kd-err" role="alert">⚠ {err}</p> : null}</>}
      </section></div> : null}
  </>;
}

// 💬 owner 2026-11-13: "assure I can choose what video/img model when making requests in chat … still references this PoC file". A chat line that
// asks for a picture or a clip goes to the media models (never to the text minds), on the model picked in the composer, and a short or
// pointing ask ("make a video of him") carries this folder's own words so the model knows what it is about. Pure.
const MEDIA_VERB = /\b(make|create|generate|render|draw|animate|shoot|film|turn|bring|give me|show me|do)\b/i;
const MEDIA_VIDEO = /\b(video|clip|reel|tiktok|short|animation|animate|moving|motion|bring (?:him|her|it|them) to life)\b/i;
const MEDIA_IMAGE = /\b(image|picture|pic|photo|portrait|poster|thumbnail|cover|art|illustration|render)\b/i;
export function mediaAsk(text) {
  const t = String(text || '').trim(); const m = t.match(/^(video|image|img|pic|photo)\s*:/i);
  if (m) return /^video/i.test(m[1]) ? 'video' : 'image';
  if (!MEDIA_VERB.test(t)) return null;
  return MEDIA_VIDEO.test(t) ? 'video' : MEDIA_IMAGE.test(t) ? 'image' : null;
}
export function mediaPrompt(text, carry) {
  const t = String(text || '').replace(/^(video|image|img|pic|photo)\s*:\s*/i, '').trim(); const c = String(carry || '').replace(/\s+/g, ' ').trim();
  const pointing = /\b(this|him|her|it|them|same|that guy|the guy|the person|the character|this poc)\b/i.test(t) || t.split(/\s+/).length < 8;
  return c && pointing ? `${t}\nFrom this PoC: ${c.slice(0, 400)}` : t;
}
// the composer's model chip: Auto (cheap pick) or any ready image / video model; remembered per browser
const MPICK = 'feeless.mediaPick';
export function useMediaPick() {
  const [v, setV] = useState(() => { try { return JSON.parse(localStorage.getItem(MPICK) || '{}'); } catch { return {}; } });
  const set = (kind, id) => setV(o => { const n = { ...o, [kind]: id }; try { localStorage.setItem(MPICK, JSON.stringify(n)); } catch { /* private */ } return n; });
  return [v, set];
}
export function MediaModelChip({ cat, work, pick, setPick }) {
  const [d, setD] = useState(null); const [open, setOpen] = useState(false); const btn = React.useRef(null); const [at, setAt] = useState(null);
  useEffect(() => { if (!open || !btn.current) return; const r = btn.current.getBoundingClientRect(); const w = Math.min(420, window.innerWidth - 24);   // 📐 always inside the screen
    setAt({ left: Math.max(12, Math.min(r.left, window.innerWidth - w - 12)), bottom: window.innerHeight - r.top + 8, width: w }); }, [open]);
  useEffect(() => { if (!open) return undefined; const k = e => e.key === 'Escape' && setOpen(false); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  useEffect(() => { if (open && !d) work(cat.id, { op: 'media_models' }).then(setD).catch(() => setD({ models: [] })); }, [open]);   // eslint-disable-line react-hooks/exhaustive-deps
  const name = k => (pick?.[k] ? ((d?.models || []).find(m => m.id === pick[k])?.label || pick[k].split('/').pop()) : 'Auto');
  return <span className="mst-chip">
    <button ref={btn} type="button" className={`mst-chip-btn${open ? ' is-on' : ''}`} aria-expanded={open} onClick={() => setOpen(o => !o)} data-testid="media-chip"
      aria-label={`Image model ${name('image')}, video model ${name('video')}`} data-tip={`Ask for an image or a video in the chat: image on ${name('image')}, video on ${name('video')}, made from this PoC. Tap to pick.`}>🎬{pick?.image || pick?.video ? <i aria-hidden="true" /> : null}</button>
    {open ? createPortal(<div className="mst-chip-pop m-pop" style={at || undefined} role="dialog" aria-label="Image and video models" data-testid="media-chip-pop">
      {!d ? <p className="mst-lead">Reading your models…</p> : ['image', 'video'].map(k => <div key={k}><p className="mst-h">{k === 'image' ? '🖼 Images' : '🎬 Videos'}</p>
        <div className="mst-chip-row">{[{ id: '', label: 'Auto', providerName: 'cheapest ready', ready: true }, ...(d.models || []).filter(m => m.kind === k)].map(m =>
          <button key={m.id || 'auto'} type="button" disabled={!m.ready} aria-pressed={(pick?.[k] || '') === m.id} className={(pick?.[k] || '') === m.id ? 'is-on' : ''}
            onClick={() => setPick(k, m.id)} data-testid={`media-chip-${k}-${m.id || 'auto'}`} data-tip={m.ready ? (m.why || m.providerName) : `Link ${m.providerName} to use this`}>
            <b>{m.label}</b><small>{m.providerName}{m.usd != null ? ` · ${usd(m.usd)}` : ''}</small></button>)}</div></div>)}
      <small className="mst-note">Then just ask in the chat: "make a video of him walking at dusk" or "image: a chrome tombstone".</small>
    </div>, document.body) : null}
  </span>;
}
