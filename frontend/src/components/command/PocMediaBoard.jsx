import React, { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import { MediaCard, STEP_WORD, splitWhy } from './MediaStudio';
import '../../styles/pocBoard.css';

// 🖼 owner 2026-11-17 ("idk what img/vid cause i cant see … the shit on the left was to help view and understanding of current
// processing"): the left of a PoC folder shows what is making right now (each job, its real step from the server, how long) and every
// finished picture and video as big tiles; one tap opens it full size with all its buttons. A job that failed is one quiet line, not a wall
// of red. Everything here is the folder's real state (the folder re-reads itself every 3 s while anything makes): no timers pretend.
const say = w => (w ? w[0].toUpperCase() + w.slice(1) : 'Working');
const ago = s => (s >= 60 ? `${Math.floor(s / 60)}m ${s % 60}s` : `${s}s`);
const money = v => (v == null ? '' : `$${Number(v).toFixed(Number(v) < 0.1 ? 3 : 2)}`);

export default function PocMediaBoard({ cat, doc, work, setDoc }) {
  const all = (doc?.messages || []).filter(m => m.media && !m.media.ref);
  const live = all.filter(m => ['queued', 'running'].includes(m.media.status));
  const done = all.filter(m => m.media.status === 'done' && m.media.url && !m.media.clip).reverse();
  const clips = all.filter(m => m.media.status === 'done' && m.media.clip).reverse();
  const failed = all.filter(m => m.media.status === 'failed').reverse();
  const [open, setOpen] = useState(null); const [showFailed, setShowFailed] = useState(false); const [, tick] = useState(0);
  useEffect(() => { if (!live.length) return undefined; const t = setInterval(() => { if (!document.hidden) tick(n => n + 1); }, 1000); return () => clearInterval(t); }, [live.length]);
  useEffect(() => { if (!open) return undefined; const k = e => { if (e.key === 'Escape') setOpen(null); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [open]);
  const now = Date.now() / 1000; const openMsg = open ? all.find(m => m.media.id === open) : null;
  return <section className="pmb" aria-label="This folder's pictures and videos" data-testid="poc-board">
    <header className="pmb-h"><b>🎬 Media</b><small>{done.length ? `${done.length} made` : 'nothing made yet'}{clips.length ? ` · ${clips.length} clip${clips.length > 1 ? 's' : ''}` : ''}{live.length ? ` · ${live.length} making` : ''}</small></header>
    {live.length ? <ul className="pmb-live" data-testid="poc-board-live">{live.map(m => { const md = m.media; const s = Math.max(0, Math.round(now - Number(md.at || now)));
      return <li key={md.id}><span className="pmb-live-ic" aria-hidden="true">{md.swap ? '🎭' : md.kind === 'video' ? '🎬' : '🖼'}</span>
        <span className="pmb-live-t"><b>{md.label}</b><small>{say(STEP_WORD[md.step] || STEP_WORD[md.status] || (md.status === 'running' ? 'making it' : md.step))} · {ago(s)}{md.usd ? ` · about ${money(md.usd)}` : ''}</small></span>
        <i className="pmb-bar" aria-hidden="true"><u /></i></li>; })}</ul> : null}
    {done.length ? <ul className="pmb-grid" data-testid="poc-board-grid">{done.map((m, i) => { const md = m.media;
      return <li key={md.id} style={{ '--i': i }}><button type="button" onClick={() => setOpen(md.id)} data-testid={`poc-board-${md.id}`} aria-label={`Open ${md.label || md.kind}`}>
        {md.kind === 'video' ? <video src={apiUrl(md.url)} muted playsInline preload="metadata" /> : <img src={apiUrl(md.url)} alt="" loading="lazy" />}
        <span className="pmb-tag">{md.kind === 'video' ? (md.swap ? '🎭 Swap' : '🎬 Video') : '🖼 Image'}{doc?.character?.mid === md.id ? ' · 👤' : ''}</span>
        <span className="pmb-cap"><b>{md.label}</b><i>{money(md.paidUsd ?? md.usd)}</i></span></button></li>; })}</ul>
      : !live.length ? <p className="pmb-none">Make a picture or video below, or swap your character into a clip. It shows up here, big, the moment it is ready.</p> : null}
    {clips.length ? <p className="pmb-clips" data-testid="poc-board-clips"><small>Your clips</small>{clips.slice(0, 6).map(m => <button key={m.media.id} type="button" onClick={() => setOpen(m.media.id)} data-tip={m.media.label}><video src={apiUrl(m.media.url)} muted playsInline preload="metadata" /></button>)}</p> : null}
    {failed.length ? <div className="pmb-fail"><button type="button" className="pmb-fail-btn" aria-expanded={showFailed} onClick={() => setShowFailed(v => !v)} data-testid="poc-board-failed">
      {failed.length} didn't finish <em>{showFailed ? 'Hide' : 'Why'}</em></button>
      {showFailed ? <ul>{failed.map(m => <li key={m.media.id}><span><b>{m.media.label}</b><small>{splitWhy(m.media.why)[0]}</small></span><button type="button" className="m-btn" onClick={() => setOpen(m.media.id)}>Open</button></li>)}</ul> : null}</div> : null}
    {openMsg ? createPortal(<div className="pmb-view" role="dialog" aria-modal="true" aria-label={openMsg.media.label || 'Media'} data-testid="poc-board-view">
      <button type="button" className="pmb-scrim" aria-label="Close" tabIndex={-1} onClick={() => setOpen(null)} />
      <div className="pmb-view-in"><button type="button" className="m-btn pmb-x" onClick={() => setOpen(null)} aria-label="Close" data-testid="poc-board-close">✕</button>
        <MediaCard m={openMsg} cat={cat} doc={doc} work={work} setDoc={setDoc} /></div></div>, document.body) : null}
  </section>;
}
