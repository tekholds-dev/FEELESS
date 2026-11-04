import React, { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { apiUrl } from '../../lib/api';
import '../../styles/agentStudio.css';

// 🖥 What a general agent makes (owner 2026-11-04): code it wrote previews on its monitor, and its images, pages and answers live in one folder.
// The page runs in a sandbox with no same-origin and no network, so it can't touch this site or send anything out.
const FENCE = /```(?:html)?\s*\n([\s\S]*?)```/gi;
const LOCK = '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; font-src data:">';

export function codeIn(text) {
  const t = String(text || '');
  for (const m of t.matchAll(FENCE)) if (/<(?:!doctype|html|body|div|section|main|canvas|svg|h1)\b/i.test(m[1])) return m[1].trim();
  const bare = t.match(/<!doctype html[\s\S]*<\/html>|<html[\s\S]*<\/html>/i);
  return bare ? bare[0].trim() : null;
}
export function lockedPage(code) { return `${LOCK}${code}`; }

export function CodeMonitor({ code, title = 'Its monitor', onClose }) {
  const [phone, setPhone] = useState(false);
  useEffect(() => { const k = e => { if (e.key === 'Escape') onClose(); }; window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  return createPortal(<div className="ast-shade" role="dialog" aria-modal="true" aria-label={title} data-testid="ast-monitor" onClick={e => { if (e.target === e.currentTarget) onClose(); }}>
    <div className="ast-screen m-glass"><header><b>🖥 {title}</b>
      <span className="m-seg">{[[false, 'Desktop'], [true, 'Phone']].map(([v, l]) => <button key={l} type="button" className={phone === v ? 'on' : ''} aria-pressed={phone === v} onClick={() => setPhone(v)} data-tip={`See it at ${v ? '360 px' : 'full width'}`}>{l}</button>)}</span>
      <button type="button" className="m-btn" onClick={onClose} aria-label="Close the preview" data-tip="Close (Esc)" data-testid="ast-close">✕</button></header>
      <div className={`ast-view${phone ? ' is-phone' : ''}`}><iframe title={title} sandbox="allow-scripts" srcDoc={lockedPage(code)} data-testid="ast-frame" /></div>
      <small>Sandboxed: this page can't reach the site or the network. Images and scripts from other sites won't load here.</small></div></div>, document.body);
}

const readPage = url => fetch(apiUrl(url)).then(r => (r.ok ? r.text() : Promise.reject(new Error('gone'))));
export function PreviewButton({ text, url }) {
  const found = useMemo(() => codeIn(text), [text]); const [loaded, setLoaded] = useState(null); const [open, setOpen] = useState(false); const [gone, setGone] = useState(false); const code = loaded || found;
  if (!code && !url) return null;
  const go = () => { if (code) { setOpen(true); return; } readPage(url).then(p => { setLoaded(p); setOpen(true); }).catch(() => setGone(true)); };
  if (gone) return <small className="m-dim">This page expired. Files stay 24 hours after their last use.</small>;
  return <><button type="button" className="m-btn cwb-open-pow" onClick={go} data-tip="Runs the page it wrote on its monitor, sandboxed" data-testid="ast-preview">▶ Preview on its monitor</button>{open ? <CodeMonitor code={code} onClose={() => setOpen(false)} /> : null}</>;
}

const TABS = [['images', '🖼 Images'], ['pages', '🌐 Pages'], ['posts', '📝 Posts']];
export function Creations({ files = [], chat = [] }) {
  const [tab, setTab] = useState('images'); const [big, setBig] = useState(null); const [page, setPage] = useState(null);
  const images = files.filter(f => /^image\//.test(f.mime || '') || /^(png|jpe?g|webp|gif)$/i.test(f.ext || ''));
  const made = chat.filter(m => m.by !== 'you' && m.tid);
  const pages = made.map(m => ({ m, code: codeIn(m.text) })).filter(x => x.code);
  const built = files.filter(f => f.ext === 'html');
  const openBuilt = f => readPage(f.url).then(setPage).catch(() => {});
  const posts = made.filter(m => !codeIn(m.text));
  const counts = { images: images.length, pages: pages.length + built.length, posts: posts.length };
  return <div className="ast" data-testid="ast-creations">
    <div className="m-seg" role="tablist">{TABS.map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)} data-testid={`ast-tab-${k}`}>{l} <b className="m-num">{counts[k]}</b></button>)}</div>
    {tab === 'images' ? (images.length ? <ul className="ast-grid">{images.map((f, i) => <li key={f.id} style={{ '--i': Math.min(i, 10) }}><button type="button" onClick={() => setBig(f)} data-tip={f.name || 'Open it'} aria-label={`Open ${f.name || 'image'}`}><img src={f.url} alt={f.name || ''} loading="lazy" /></button></li>)}</ul> : <p className="m-dim">Nothing yet. Images you or it save to its storage show here.</p>) : null}
    {tab === 'pages' ? (pages.length + built.length ? <ul className="ast-rows">{built.map(f => <li key={f.id}><span>{String(f.name).replace(/\.html$/, '')}</span><button type="button" className="m-btn" onClick={() => openBuilt(f)} data-tip="Runs it on its monitor, sandboxed" data-testid={`ast-built-${f.id}`}>▶ Preview</button></li>)}{pages.map(({ m, code }, i) => <li key={m.tid || i}><span>{String(m.text).split('\n')[0].replace(/[`#]/g, '').slice(0, 70) || 'A page it wrote'}</span><button type="button" className="m-btn" onClick={() => setPage(code)} data-tip="Run it on its monitor" data-testid={`ast-page-${i}`}>▶ Preview</button></li>)}</ul> : <p className="m-dim">Nothing yet. Ask it to build a web page and it lands here.</p>) : null}
    {tab === 'posts' ? (posts.length ? <ul className="ast-rows">{posts.slice(-30).reverse().map((m, i) => <li key={m.tid || i}><span>{String(m.text).slice(0, 180)}</span></li>)}</ul> : <p className="m-dim">Nothing yet. What it writes for you shows here.</p>) : null}
    {big ? createPortal(<div className="ast-shade" role="dialog" aria-modal="true" aria-label={big.name || 'Image'} onClick={() => setBig(null)} data-testid="ast-big"><img src={big.url} alt={big.name || ''} /></div>, document.body) : null}
    {page ? <CodeMonitor code={page} onClose={() => setPage(null)} /> : null}
  </div>;
}
