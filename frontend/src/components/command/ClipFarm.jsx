import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Check, Copy, ExternalLink, Film, Link2, Loader2, Scissors, Trash2, Upload, X } from 'lucide-react';
import { apiUrl, errorText } from '../../lib/api';
import { agentAuth, agentAuthQuery } from '../../lib/chatSession';
import { boxRef } from '../../lib/boxRef';
import '../../styles/clipFarm.css';

// ✂ Slice 15 (owner 2026-11-19: "clipfarming! yt, twitch, ig -> … users should be able to upload vids etc up to 5 mins and we provide best
// brains to clip farm epically and quickly"). Drop a video (≤ 5 min). This machine transcribes it with word times, finds the loud, funny and
// cut-heavy moments, both of the agent's PoC minds score every moment blind, and each pick comes back tracked on the speaker, captioned word by
// word, in 9:16, 1:1 and 16:9, each filed as its own PoC. YouTube / Twitch / Instagram links are never downloaded: save it from the app, then
// upload. The board lays each clip out as story / feed / wide with a day of the week; it posts only from Its PoCs › Approve and post.
export const MAX_S = 300; export const MAX_MB = 600;
export const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const SHAPES = [['story', '9:16', 'Shorts · Reels · TikTok'], ['feed', '1:1', 'Feed square'], ['wide', '16:9', 'YouTube · X']];
const STATE_IC = { done: <Check size={13} />, running: <Loader2 size={13} className="clf-spin" />, failed: <X size={13} />, todo: null };
const box = boxRef([640]);

/** Pure: what is wrong with a picked file before it goes up (the server checks again with ffprobe), or ''. */
export function fileProblem(f, secs) {
  if (!f) return 'Pick a video.';
  if (!/\.(mp4|mov|webm|m4v|mkv|avi)$/i.test(f.name || '') && !/^video\//.test(f.type || '')) return 'Upload a video file: MP4, MOV, WebM, MKV, AVI or M4V.';
  if (f.size > MAX_MB * 1e6) return `That file is ${Math.round(f.size / 1e6)} MB. Up to ${MAX_MB} MB: export it smaller.`;
  if (secs != null && secs > MAX_S + 0.5) return `That video is ${Math.floor(secs / 60)}:${String(Math.floor(secs % 60)).padStart(2, '0')} long. Up to 5:00: trim it first.`;
  return '';
}
/** Pure: the platform of a link FEELESS never downloads from (their terms), else ''. */
export function platformOf(u) {
  const m = String(u || '').trim().match(/^https?:\/\/(?:[a-z0-9-]+\.)*(youtube\.com|youtu\.be|twitch\.tv|instagram\.com|tiktok\.com|x\.com|twitter\.com|facebook\.com|fb\.watch)\b/i);
  return m ? { 'youtube.com': 'YouTube', 'youtu.be': 'YouTube', 'twitch.tv': 'Twitch', 'instagram.com': 'Instagram', 'tiktok.com': 'TikTok', 'x.com': 'X', 'twitter.com': 'X', 'facebook.com': 'Facebook', 'fb.watch': 'Facebook' }[m[1].toLowerCase()] : '';
}
/** Pure: a link that is never downloaded → what to do instead, else ''. */
export function linkProblem(u) {
  const s = String(u || '').trim(); if (!s) return '';
  const name = platformOf(s);
  if (!name) return /^https:\/\//.test(s) ? '' : 'Paste a link that starts with https://';
  return `${name} doesn't allow downloading its videos. Save it from the ${name} app (yours, or you have the rights), then upload the file.`;
}
/** The steps to save your own video from each app: a redirect, never a downloader. */
export const SAVE_STEPS = {
  YouTube: ['Your own video: YouTube Studio › Content › the video’s ⋮ menu › Download.', 'Not yours? Ask the creator for the file, or for the rights to use it.'],
  Twitch: ['Your own past stream: Creator Dashboard › Content › Video Producer › ⋮ › Download.', 'Your own clip: Creator Dashboard › Content › Clips › Download.'],
  Instagram: ['Your own reel: open it › ⋯ › Save / Download (or Your activity › Download your information).', 'Someone else’s reel: ask them for the file or the rights.'],
  TikTok: ['Your own video: open it › Share › Save video.', 'Someone else’s: only if they allow saving and you have the rights.'],
  X: ['Your own video: Settings › Your account › Download an archive of your data.', 'Someone else’s: ask them for the file or the rights.'],
  Facebook: ['Your own video: open it › ⋯ › Download video.', 'Someone else’s: ask them for the file or the rights.'],
};
export const abs = u => { try { return new URL(apiUrl(u), window.location.href).href; } catch { return u; } };
function LinkChip({ url, label, onDelete, testid }) {
  const [done, setDone] = useState(false);
  if (!url) return null;
  return <span className="clf-link" data-testid={testid}><Link2 size={12} aria-hidden="true" /><small>{label}</small>
    <a href={apiUrl(url)} target="_blank" rel="noreferrer noopener" data-tip="Open the in-house FEELESS link (plays in any browser, 7 days)"><ExternalLink size={12} /></a>
    <button type="button" onClick={async () => { try { await navigator.clipboard.writeText(abs(url)); setDone(true); setTimeout(() => setDone(false), 1500); } catch { /* no clipboard here */ } }} data-tip="Copy the link: paste it to your phone or into a post">{done ? <Check size={12} /> : <Copy size={12} />}</button>
    {onDelete ? <button type="button" onClick={onDelete} data-tip="End this link now" data-testid={`${testid}-del`}><Trash2 size={12} /></button> : null}</span>;
}
/** Pure: the clip PoCs on the board, newest run first, best clip first. */
export function boardRows(pocs) {
  return (pocs || []).filter(f => f?.studio?.clip).sort((a, b) => (b.at || 0) - (a.at || 0) || (a.studio.clip.rank || 0) - (b.studio.clip.rank || 0));
}
const file = (f, piece, fmt) => (f?.studio?.files || []).find(x => x.piece === piece && x.format === fmt && x.url && !x.error);
const clock = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

function Steps({ run }) {
  return <ol className="clf-steps" aria-label="Progress">{(run.steps || []).map((s, i) => <li key={s.key} className={`is-${s.state}`} style={{ '--i': i }} data-testid={`cfm-step-${s.key}`}>
    <span className="clf-dot" aria-hidden="true">{STATE_IC[s.state]}</span><b>{s.label}</b><small>{s.note || (s.state === 'todo' ? 'waiting' : '')}{s.secs != null ? ` · ${s.secs} s` : ''}</small></li>)}</ol>;
}

function Moments({ run }) {
  const minds = run.minds || [];
  if (!(run.cands || []).length) return null;
  return <div className="clf-moments" data-testid="cfm-moments"><table><thead><tr><th>#</th><th>Where</th><th>First 2 s</th><th data-tip="Code's own score: hook, payoff, loudness, laughs, cuts">Code</th>
    {minds.length ? minds.map(m => <th key={m.mind} data-tip={m.model}>Mind {'AB'[m.mind % 2]}<small>{m.name}</small></th>) : <><th>Mind A</th><th>Mind B</th></>}<th>Made</th></tr></thead>
    <tbody>{run.cands.map(c => { const made = (run.picks || []).some(p => p.n === c.n); return <tr key={c.n} className={made ? 'is-made' : ''}>
      <td className="m-num">{c.n}</td><td className="m-num">{clock(c.s)}–{clock(c.e)}<small> {Math.round(c.e - c.s)} s</small></td><td className="clf-first">“{c.first2}”</td><td className="m-num">{c.local}</td>
      {(c.minds || [{}, {}]).map((m, i) => <td key={i} className="m-num" data-tip={m.why || 'no score'}>{m.score == null ? '—' : m.score}{m.picked ? <span className="clf-pick" aria-label="picked">★</span> : null}</td>)}
      <td>{made ? <Scissors size={14} aria-label="made" /> : null}</td></tr>; })}</tbody></table></div>;
}

function Board({ rows, onSlot, onOpen, busy }) {
  if (!rows.length) return <p className="clf-none">The clips land here as phone story, feed and wide tiles, each with a day of the week.</p>;
  return <div className="clf-board" data-testid="cfm-board">{rows.map((f, i) => { const c = f.studio.clip; const slot = f.studio.slot || ''; return <article key={f.id} className="clf-clip" style={{ '--i': i }} data-testid={`cfm-clip-${f.id}`}>
    <header><span className="m-label">PoC #{f.n}{f.test ? ' · TEST' : ''}</span><b>{f.studio.hook}</b><small>{clock(c.s)}–{clock(c.e)} of {c.from} · both minds {c.both ?? '—'}/10 · goal {Number(f.studio.goal?.target || 0).toLocaleString()} views · ${(Number(f.cost || 0)).toFixed(4)}</small></header>
    <div className="clf-tiles">{SHAPES.map(([k, r, tip]) => { const v = file(f, 'video', k); const im = file(f, 'image', k); return <figure key={k} className={`clf-tile is-${k}`} data-tip={tip}>
      <span className="m-label">{r}</span>{v ? <video src={apiUrl(v.url)} poster={im ? apiUrl(im.url) : undefined} controls muted playsInline preload="none" data-testid={`cfm-vid-${k}`} /> : <small>not made</small>}</figure>; })}</div>
    <footer><div className="m-seg clf-days" role="group" aria-label="Day to post">{DAYS.map(d => <button key={d} type="button" aria-pressed={slot === d} className={slot === d ? 'active' : ''} disabled={busy || !!f.posted} onClick={() => onSlot(f.id, slot === d ? '' : d)} data-testid={`cfm-day-${f.id}-${d}`}>{d}</button>)}</div>
      <span className="clf-links">{SHAPES.map(([k, r]) => <LinkChip key={k} url={f.studio.links?.[k]} label={r} testid={`cfm-link-${f.id}-${k}`} />)}</span>
      <button type="button" className="m-btn" onClick={() => onOpen?.(f)} data-tip="Its PoCs: the goal, the platforms and the approve" data-testid={`cfm-open-${f.id}`}>{f.posted ? 'Posted · reach' : 'Approve and post…'}</button></footer>
  </article>; })}</div>;
}

export default function ClipFarm({ cat, wsId, pocs, onPocs, onOpen }) {
  const [runs, setRuns] = useState([]); const [busy, setBusy] = useState(false); const [pct, setPct] = useState(null); const [err, setErr] = useState('');
  const [rights, setRights] = useState(false); const [note, setNote] = useState(''); const [link, setLink] = useState(''); const [drag, setDrag] = useState(false); const [slotBusy, setSlotBusy] = useState(false); const [card, setCard] = useState('');
  const input = useRef(null); const base = `/api/cats/${cat.id}/clipfarm`;
  const load = useCallback(() => fetch(apiUrl(`${base}?${agentAuthQuery()}`)).then(r => r.ok ? r.json() : null).then(j => { if (j) { setRuns(j.runs || []); setBusy(!!j.busy); } return j; }).catch(() => null), [base]);
  const running = runs.some(r => r.status === 'running') || busy;
  useEffect(() => { load(); const t = setInterval(() => { if (!document.hidden) load(); }, running ? 2500 : 15000); return () => clearInterval(t); }, [load, running]);
  const lastClips = (runs.find(r => r.status === 'running') || runs[0])?.clips?.length || 0;
  useEffect(() => { if (lastClips) onPocs?.(); }, [lastClips]);   // eslint-disable-line react-hooks/exhaustive-deps

  const send = async f => {
    setErr(''); if (!rights) { setErr('Tick that the video is yours, or that you have the rights to use it.'); return; }
    const secs = await new Promise(ok => { try { const v = document.createElement('video'); v.preload = 'metadata'; v.onloadedmetadata = () => { ok(v.duration); URL.revokeObjectURL(v.src); }; v.onerror = () => ok(null); v.src = URL.createObjectURL(f); setTimeout(() => ok(null), 4000); } catch { ok(null); } });
    const bad = fileProblem(f, secs); if (bad) { setErr(bad); return; }
    setPct(0);
    const q = `${agentAuthQuery()}&rights=1&name=${encodeURIComponent(f.name)}&note=${encodeURIComponent(note)}${wsId ? `&ws=${encodeURIComponent(wsId)}` : ''}`;
    await new Promise(done => { const x = new XMLHttpRequest(); x.open('POST', apiUrl(`${base}/upload?${q}`)); x.setRequestHeader('Content-Type', f.type || 'video/mp4');
      x.upload.onprogress = e => e.lengthComputable && setPct(Math.round(e.loaded / e.total * 100));
      x.onload = () => { if (x.status >= 300) { let b = {}; try { b = JSON.parse(x.responseText); } catch { /* not JSON */ } setErr(errorText(b, x.status)); } done(); };
      x.onerror = () => { setErr('The upload did not go through. Try again.'); done(); }; x.send(f); });
    setPct(null); load();
  };
  const fromLink = async () => {
    setErr(''); setCard(''); const plat = platformOf(link); if (plat) { setCard(plat); return; } const bad = linkProblem(link); if (bad) { setErr(bad); return; } if (!rights) { setErr('Tick that the video is yours, or that you have the rights to use it.'); return; }
    setPct(0); try { const r = await fetch(apiUrl(`${base}/link`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), url: link.trim(), rights: true, note, ws: wsId }) });
      const j = await r.json().catch(() => ({})); if (!r.ok) setErr(errorText(j, r.status)); else setLink(''); } finally { setPct(null); load(); }
  };
  const unlink = async url => { setErr(''); const r = await fetch(apiUrl(`${base}/unlink`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), id: String(url).split('/').pop() }) }).catch(() => null);
    if (!r?.ok) setErr('That link could not be ended. Try again.'); load(); };
  const slot = async (job, day) => { setSlotBusy(true); setErr(''); try { const r = await fetch(apiUrl(`${base}/slot`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ...agentAuth(), job, day }) });
    const j = await r.json().catch(() => ({})); if (!r.ok) setErr(errorText(j, r.status)); else onPocs?.(j.pocFolders); } finally { setSlotBusy(false); } };

  const run = runs[0]; const rows = boardRows(pocs);
  return <section ref={box} className="clf m-live" aria-label="Clip farm" data-testid="clip-farm">
    <header className="clf-head"><span><small className="m-label">CLIP FARM · FREE ON THIS MACHINE</small><strong>Drop a video, get the moments back as clips</strong></span>
      <small>Up to 5:00 · any MP4, MOV, WebM, MKV or AVI (converted free on this machine) · captioned, reframed on the speaker, 9:16 · 1:1 · 16:9 · nothing posts without your approve</small></header>
    <div className={`clf-drop${drag ? ' is-drag' : ''}${pct != null ? ' is-busy' : ''}`} onDragOver={e => { e.preventDefault(); setDrag(true); }} onDragLeave={() => setDrag(false)}
      onDrop={e => { e.preventDefault(); setDrag(false); const f = e.dataTransfer.files?.[0]; if (f && !running && pct == null) send(f); }} data-testid="cfm-drop">
      <Film size={26} aria-hidden="true" /><b>{pct != null ? `Uploading ${pct}%` : running ? 'Clipping your video…' : 'Drop your video here'}</b>
      <small>YouTube, Twitch or Instagram? Save it from the app, then drop the file. A Bluesky post or a direct .mp4 link works below.</small>
      <span className="clf-row"><label className="clf-rights"><input type="checkbox" checked={rights} onChange={e => setRights(e.target.checked)} data-testid="cfm-rights" /> It's mine, or I have the rights</label>
        <button type="button" className="m-btn m-go" disabled={running || pct != null} onClick={() => input.current?.click()} data-testid="cfm-pick"><Upload size={14} /> Upload a video</button>
        <input ref={input} type="file" accept="video/*,.mp4,.mov,.webm,.m4v,.mkv,.avi" hidden onChange={e => { const f = e.target.files?.[0]; e.target.value = ''; if (f) send(f); }} data-testid="cfm-file" /></span>
      <span className="clf-row"><input className="m-input" value={note} onChange={e => setNote(e.target.value)} placeholder="Note for the minds (optional): what to look for" aria-label="Note for the minds" data-testid="cfm-note" />
        <input className="m-input" value={link} onChange={e => setLink(e.target.value)} placeholder="https://bsky.app/… or https://…/video.mp4" aria-label="Video link" data-testid="cfm-link" />
        <button type="button" className="m-btn" disabled={!link.trim() || running || pct != null} onClick={fromLink} data-testid="cfm-link-go"><Link2 size={14} /> Use link</button></span>
    </div>
    {card ? <div className="clf-card" role="note" data-testid="cfm-redirect"><b>{card} doesn't allow downloading its videos, so FEELESS never fetches them.</b>
      <span>Save it from the {card} app (it has to be yours, or you need the rights), then upload the file here:</span>
      <ol>{(SAVE_STEPS[card] || []).map(t => <li key={t}>{t}</li>)}</ol>
      <span className="clf-row"><button type="button" className="m-btn m-go" onClick={() => { setCard(''); input.current?.click(); }} data-testid="cfm-redirect-upload"><Upload size={14} /> Upload the saved file</button>
        <button type="button" className="m-btn" onClick={() => setCard('')}>Close</button></span></div> : null}
    {err ? <small className="clf-err" role="alert" data-testid="cfm-err">{err}</small> : null}
    {run ? <div className="clf-run" data-testid="cfm-run"><header><span className="m-label">{run.status === 'running' ? 'RUNNING' : run.status === 'done' ? 'DONE' : 'STOPPED'}{run.test ? ' · TEST' : ''}</span>
      <b>{run.name}</b><small className="m-num">{clock(run.secs || 0)} · {run.w}×{run.h}{run.firstClipS ? ` · first clip ${Math.round(run.firstClipS)} s` : ''}{run.doneS ? ` · all ${Math.round(run.doneS)} s` : ''} · minds ${Number(run.cost || 0).toFixed(4)}</small></header>
      {run.converted?.url ? <span className="clf-links"><LinkChip url={(run.links || []).some(k => k.kind === 'upload' && !k.gone && !k.swept && k.exp * 1000 > Date.now()) ? run.converted.url : ''} label="Your upload, converted" onDelete={() => unlink(run.converted.url)} testid="cfm-uplink" /></span> : null}
      <Steps run={run} />{run.err ? <small className="clf-err">{run.err}</small> : null}<Moments run={run} /></div> : null}
    <h4 className="clf-h">Clip board · story / feed / wide, a day each</h4>
    <Board rows={rows} busy={slotBusy} onSlot={slot} onOpen={onOpen} />
  </section>;
}
