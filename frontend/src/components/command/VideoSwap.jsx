import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { motion } from 'motion/react';
import { apiUrl } from '../../lib/api';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';
import '../../styles/videoSwap.css';

// 🎭 Slice 4 (owner 2026-11-18): drop in a video → the same video (motion, timing, camera, sound) with a realistic AI-made person in place,
// no watermark, filed into this PoC folder with the before | after side by side and its cost. Runs on FEELESS's own HQ › Core keys
// (MiniMax H3 Max Recast on fal.ai, runner-up Runway Aleph 2 on OpenRouter); only the owner and staff agents can press it, at the price shown.
const STEPS = [['person', 'Person'], ['sending', 'Send'], ['queued', 'Queue'], ['running', 'Make'], ['sound', 'Sound'], ['side', 'Side by side'], ['filed', 'Filed']];
const STEP_I = Object.fromEntries(STEPS.map(([k], i) => [k, i])); STEP_I.submitted = 1;
const money = v => `$${Number(v || 0).toFixed(2)}`;
async function call(path, opts) {
  const r = await fetch(apiUrl(path), { headers: { 'Content-Type': 'application/json' }, ...opts });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || `Request failed (${r.status})`);
  return j;
}
const readFile = f => new Promise((ok, no) => { const r = new FileReader(); r.onload = () => ok(r.result); r.onerror = () => no(new Error('That file could not be read.')); r.readAsDataURL(f); });

// ▶ before | after, played together: one button runs both clips from the same moment
export function SwapPair({ before, after, side }) {
  const a = useRef(null); const b = useRef(null); const [on, setOn] = useState(false); const [view, setView] = useState('pair');
  const both = fn => [a.current, b.current].forEach(v => v && fn(v));
  const play = () => { if (on) { both(v => v.pause()); setOn(false); return; } both(v => { v.currentTime = 0; }); both(v => { const p = v.play(); if (p?.catch) p.catch(() => {}); }); setOn(true); };
  if (view === 'side' && side) return <div className="vsw-pair is-side"><video src={apiUrl(side)} controls playsInline preload="metadata" data-testid="vsw-side" /><button type="button" className="m-btn" onClick={() => setView('pair')} data-tip="Back to the two players">Two players</button></div>;
  return <div className="vsw-pair" data-testid="vsw-pair">
    <figure><small className="m-label">BEFORE</small><video ref={a} src={apiUrl(before?.url)} muted playsInline preload="metadata" onEnded={() => setOn(false)} data-testid="vsw-before" /></figure>
    <figure className="is-after"><small className="m-label">AFTER</small>{after?.url ? <video ref={b} src={apiUrl(after.url)} playsInline preload="metadata" onEnded={() => setOn(false)} data-testid="vsw-after" /> : <span className="vsw-wait"><i /></span>}</figure>
    <span className="vsw-pair-acts"><button type="button" className="m-btn m-go" onClick={play} disabled={!after?.url} data-tip="Plays the before and after from the same moment, with the clip's own sound" data-testid="vsw-play">{on ? '❚❚ Pause both' : '▶ Play both'}</button>
      {side ? <button type="button" className="m-btn" onClick={() => setView('side')} data-tip="One file, before on the left, after on the right" data-testid="vsw-side-open">Side-by-side file</button> : null}
      {side ? <a className="m-btn" href={apiUrl(side)} download data-tip="Download the before | after video">Download</a> : null}</span>
  </div>;
}

// 🧾 a filed swap in the folder's list: what made it, what it cost, the before | after
export function SwapFiled({ f }) {
  const s = f?.swap; if (!s) return null;
  return <section className="vsw-filed m-card" data-testid={`vsw-filed-${f.id}`}>
    <header><span><small className="m-label">VIDEO SWAP · PoC #{f.n}</small><b>{s.engine}{s.res ? ` · ${s.res}` : ''}</b><small>{s.person?.source === 'made' ? 'New AI-made person' : 'The folder\'s AI-made character'} · sound {s.sound} · no watermark</small></span>
      <span className="vsw-cost" data-tip={(s.lines || []).map(l => `${l.what}: ${money(l.usd)}`).join(' · ')}><small>COST</small><b className="m-num">{money(f.cost)}</b><small>{s.paid}</small></span></header>
    <SwapPair before={s.before} after={s.after} side={s.side} />
    <small className="vsw-runner">Runner-up engine: {s.runnerUp}{s.tookS ? ` · took ${Math.round(s.tookS / 60) || 1} min` : ''}</small>
  </section>;
}

function JobRow({ j, i }) {
  const at = j.step === 'failed' ? -1 : (STEP_I[j.step] ?? 0); const pct = j.step === 'filed' ? 1 : Math.max(0.06, (at + 0.5) / STEPS.length);
  return <li className={`vsw-job is-${j.step}`} style={{ '--i': i }} data-testid={`vsw-job-${j.id}`}>
    <header><b>{j.label}{j.res ? ` · ${String(j.res).toLowerCase()}` : ''}</b><small className="m-num">{money(j.quote?.usd)}</small><em>{j.step === 'failed' ? 'STOPPED' : j.step === 'filed' ? 'FILED' : 'MAKING'}</em></header>
    {j.step !== 'failed' ? <><span className="vsw-track" aria-hidden="true"><motion.i initial={{ scaleX: 0 }} animate={{ scaleX: pct }} transition={{ duration: 0.6 }} /></span>
      <ol className="vsw-steps">{STEPS.map(([k, l], n) => <li key={k} className={n < at || j.step === 'filed' ? 'is-done' : n === at ? 'is-now' : ''}>{l}</li>)}</ol></> : <p className="vsw-why" role="alert">{j.why}</p>}
    {j.step === 'filed' ? <SwapPair before={j.before} after={j.after} side={j.side} /> : null}
  </li>;
}

function Meter({ label, used, add, cap, tip, testid }) {
  const u = Math.min(1, (Number(used) || 0) / (cap || 1)); const a = Math.min(1 - u, (Number(add) || 0) / (cap || 1)); const over = (Number(used) || 0) + (Number(add) || 0) > cap + 1e-9;
  return <span className={`vsw-meter${over ? ' is-over' : ''}`} data-tip={tip} data-testid={testid}><small>{label}</small><i><u style={{ transform: `scaleX(${u})` }} /><s style={{ transform: `translateX(${u * 100}%) scaleX(${a})` }} /></i><b className="m-num">{money((Number(used) || 0) + (Number(add) || 0))} / {money(cap)}</b></span>;
}

export function VideoSwapPanel({ cat, row, work, setDoc, onClose }) {
  const [p, setP] = useState(null); const [err, setErr] = useState(''); const [clip, setClip] = useState(''); const [eng, setEng] = useState(''); const [res, setRes] = useState('768P');
  const [who, setWho] = useState('character'); const [words, setWords] = useState(''); const [note, setNote] = useState(''); const [sure, setSure] = useState(false); const [busy, setBusy] = useState(false);
  const [rights, setRights] = useState(false); const [up, setUp] = useState(false);
  const load = useCallback(() => call(`/api/cats/${cat.id}/vswap?ws=${encodeURIComponent(row.id)}&${agentAuthQuery()}`).then(j => { setP(j); setErr(''); return j; }).catch(e => { setErr(e.message); setP(x => x || { engines: [], clips: [], jobs: [], failed: true }); }), [cat.id, row.id]);
  useEffect(() => { load(); }, [load]);
  const live = (p?.jobs || []).some(j => !['filed', 'failed'].includes(j.step));
  useEffect(() => { if (!live) return undefined; const t = setInterval(() => { if (!document.hidden) load(); }, 4000); return () => clearInterval(t); }, [live, load]);
  useEffect(() => { if (!p) return; if (!clip && p.clips?.[0]) setClip(p.clips[0].mid); if (!eng) setEng(p.auto || 'fal-h3-recast'); if (p.res && !res) setRes(p.res); if (!p.person) setWho('make'); }, [p, clip, eng, res]);
  useEffect(() => { setSure(false); }, [clip, eng, res, who, words]);
  if (!p) return <p className="vsw-none">Reading the swap desk…</p>;
  const E = (p.engines || []).find(e => e.id === eng) || (p.engines || [])[0] || {}; const C = (p.clips || []).find(c => c.mid === clip);
  const rk = E.res?.length ? res : 'std'; const q = C?.quote?.[E.id]?.[rk]?.[who === 'character' && p.person ? 'char' : 'make']; const fit = C?.fit?.[E.id];
  const blocked = !p.allowed ? 'Only the owner and staff agents can spend FEELESS\'s keys.' : !E.ready ? `Add ${E.env} under HQ › Core › Provider keys first.` : !C ? 'Add your clip first.' : fit || (who === 'make' && words.trim().length < 3 ? 'Say who the new person is.' : '') || (q && q.usd > p.cap + 1e-9 ? `Over your ${money(p.cap)} cap per swap.` : '') || (q && p.daySpent + q.usd > p.dayCap + 1e-9 ? 'Over today\'s cap on FEELESS keys.' : '');
  const add = async e => { const f = e.target.files?.[0]; e.target.value = ''; if (!f) return; if (!rights) { setErr('Tick that the clip is yours, or that you have the rights to use it.'); return; } setUp(true); setErr('');
    try { const j = await work(cat.id, { op: 'media_clip', job: row.id, text: await readFile(f), tools: { rights: true, name: f.name.replace(/\.[^.]+$/, '').slice(0, 60) } }); if (j?.doc) setDoc?.(j.doc); const n = await load(); if (n?.clips?.[0]) setClip(n.clips[0].mid); } catch (er) { setErr(er.message); } finally { setUp(false); } };
  const go = async () => { if (!sure) { setSure(true); return; } setBusy(true); setErr('');
    try { const j = await call(`/api/cats/${cat.id}/vswap`, { method: 'POST', body: JSON.stringify({ ...agentAuth(), ws: row.id, clip, engine: E.id, res: E.res?.length ? res : '', person: who, words, note, usd: q?.usd }) }); setP(j); setSure(false); } catch (er) { setErr(er.message); setSure(false); load(); } finally { setBusy(false); } };
  return <section className="vsw m-card m-live" aria-label="Video swap" data-testid="vsw">
    <header className="vsw-head"><span><small className="m-label">🎭 VIDEO SWAP · SAME CLIP, NEW AI PERSON</small><b>Same motion, timing, camera and sound. No watermark.</b></span>{onClose ? <button type="button" className="m-btn" onClick={onClose} aria-label="Close video swap" data-tip="Close" data-testid="vsw-close">✕</button> : null}</header>
    <div className="m-seg vsw-engines" role="radiogroup" aria-label="Engine">{(p.engines || []).map(e => <button key={e.id} type="button" role="radio" aria-checked={eng === e.id} className={eng === e.id ? 'active' : ''} onClick={() => setEng(e.id)} data-tip={e.why} data-testid={`vsw-eng-${e.id}`}>
      <b>{e.label}</b><small>{e.pick ? 'PICK' : 'RUNNER-UP'} · {e.who} · <em className={e.ready ? 'is-ok' : 'is-need'} data-tip={e.keyFrom || `Add ${e.env} under HQ › Core › Provider keys`}>{e.ready ? (e.keyFrom && !/^FEELESS/.test(e.keyFrom) ? 'YOUR KEY' : 'KEY SET') : `NEEDS ${e.env}`}</em></small></button>)}</div>
    <div className="vsw-grid">
      <section className="vsw-step"><small className="m-label">1 · YOUR CLIP</small>
        {(p.clips || []).length ? <ul className="vsw-clips">{p.clips.map((c, i) => <li key={c.mid} style={{ '--i': i }}><button type="button" className={clip === c.mid ? 'is-on' : ''} aria-pressed={clip === c.mid} onClick={() => setClip(c.mid)} data-tip={c.fit?.[E.id] || `${Number(c.secs || 0).toFixed(1)} s`} data-testid={`vsw-clip-${c.mid}`}><video src={apiUrl(c.url)} muted playsInline preload="metadata" /><small>{c.label}</small><b className="m-num">{Number(c.secs || 0).toFixed(1)} s</b></button></li>)}</ul> : <p className="vsw-none">No clip in this folder yet.</p>}
        <span className="vsw-add"><label className="vsw-rights"><input type="checkbox" checked={rights} onChange={e => setRights(e.target.checked)} data-testid="vsw-rights" /><small>It's my clip, or I have the rights to use it</small></label>
          <label className={`m-btn${up ? ' is-busy' : ''}`} data-tip="MP4, MOV or WebM, up to 48 MB. Longer than 30 s is cut to its first 30 s"><input type="file" accept="video/mp4,video/quicktime,video/webm" onChange={add} disabled={up} hidden data-testid="vsw-file" />{up ? 'Adding…' : '+ Add your clip'}</label></span></section>
      <section className="vsw-step"><small className="m-label">2 · THE NEW PERSON (AI-MADE)</small>
        <div className="m-seg" role="radiogroup" aria-label="New person">{[['character', 'Folder character', 'The AI-made character this folder keeps'], ['make', 'Describe one', 'A realistic person who does not exist is made first, then swapped in']].map(([k, l, t]) => <button key={k} type="button" role="radio" aria-checked={who === k} className={who === k ? 'active' : ''} disabled={k === 'character' && !p.person} onClick={() => setWho(k)} data-tip={k === 'character' && !p.person ? 'This folder has no AI-made character yet' : t} data-testid={`vsw-who-${k}`}>{l}</button>)}</div>
        {who === 'character' && p.person ? <figure className="vsw-person"><img src={apiUrl(p.person.url)} alt="The folder's character" /><small>{p.person.prompt || 'The folder\'s character'}</small></figure>
          : <textarea className="m-input" rows={2} maxLength={400} value={words} onChange={e => setWords(e.target.value)} placeholder="A woman in her 30s, short red hair, denim jacket" aria-label="Describe the new person" data-testid="vsw-words" />}
        <input className="m-input" value={note} maxLength={400} onChange={e => setNote(e.target.value)} placeholder="Anything else to keep or change (optional)" aria-label="Note for the swap" data-testid="vsw-note" /></section>
      <section className="vsw-step vsw-pay"><small className="m-label">3 · QUALITY + PRICE</small>
        {E.res?.length ? <div className="m-seg" role="radiogroup" aria-label="Quality">{E.res.map(r => <button key={r} type="button" role="radio" aria-checked={res === r} className={res === r ? 'active' : ''} onClick={() => setRes(r)} data-tip={r === '768P' ? 'The default: sharp on a phone' : 'The most detail, about 2× the output price'} data-testid={`vsw-res-${r}`}>{r.toLowerCase()}</button>)}</div> : <small className="vsw-none">{E.sound ? `Sound: ${E.sound}` : ''}</small>}
        {q ? <ul className="vsw-lines" data-testid="vsw-lines">{q.lines.map(l => <li key={l.what}><small>{l.what}</small><b className="m-num">{money(l.usd)}</b></li>)}<li className="is-total"><small>ONE PRESS</small><b className="m-num" data-testid="vsw-total">{money(q.usd)}</b></li></ul> : null}
        {C?.note?.[E.id] ? <p className="vsw-note" data-testid="vsw-note">{C.note[E.id]}</p> : null}
        <Meter label="PER SWAP" used={0} add={q?.usd} cap={p.cap} tip="Your own cap per swap (set under the swap button)" testid="vsw-cap" />
        <Meter label="TODAY ON FEELESS KEYS" used={p.daySpent} add={q?.usd} cap={p.dayCap} tip="Every swap on FEELESS's HQ › Core keys today, this one included" testid="vsw-day" />
        <button type="button" className={`m-btn m-go vsw-go${sure ? ' is-sure' : ''}`} disabled={!!blocked || busy || !q} onClick={go} data-tip={blocked || (sure ? `Spends about ${money(q?.usd)} on ${E.who} (FEELESS's key)` : 'Press, then press again to confirm')} data-testid="vsw-go">{busy ? 'Sending…' : sure ? `Confirm: spend ${money(q?.usd)} on ${E.who}` : `Swap for ${money(q?.usd)}`}</button>
        {blocked ? <small className="vsw-block" role="status" data-testid="vsw-block">{blocked}</small> : null}</section>
    </div>
    {err ? <small className="kd-err" role="alert" data-testid="vsw-err">⚠ {err}</small> : null}
    {(p.jobs || []).length ? <ol className="vsw-jobs" aria-label="This folder's swaps">{p.jobs.map((j, i) => <JobRow key={j.id} j={j} i={i} />)}</ol> : null}
  </section>;
}

export function VideoSwapTile({ cat, row, work, setDoc }) {
  const [open, setOpen] = useState(false);
  useEffect(() => { if (!open) return undefined; const k = e => { if (e.key === 'Escape') setOpen(false); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  return <><button type="button" className="poc-tile vsw-tile" onClick={() => setOpen(true)} data-tip="Your clip back with a realistic AI-made person in it: same motion, timing, camera and sound, no watermark" data-testid="vsw-open"><b>🎭 Video swap</b><small>Same clip, new AI person</small></button>
    {open ? createPortal(<div className="vsw-sheet" role="dialog" aria-modal="true" aria-label="Video swap" onMouseDown={e => { if (e.target === e.currentTarget) setOpen(false); }}><VideoSwapPanel cat={cat} row={row} work={work} setDoc={setDoc} onClose={() => setOpen(false)} /></div>, document.body) : null}</>;
}

export default VideoSwapTile;
