import React, { useEffect, useState } from 'react';
import '../../styles/psInspect.css';

// 🔍 Slice 9 · PoStatic: inspect, not mark (owner 2026-11-19). Hover the built page and any element lights up the way a browser's inspect
// does; click it and a card here aims "Fix this" or "Comment" at that exact element. The request carries its selector, its words and its
// code; the next version shows it before and after. Old box marks still open in the page (BuildSpace keeps them).
export const INSPECT_MAX = 6;

// what the page's sandbox draws: picked elements numbered green, saved comments amber
export const pinRows = (picks, comments) => [...(picks || []).map((p, i) => ({ sel: p.sel, n: i + 1, kind: 'fix' })), ...(comments || []).map((c, i) => ({ sel: c.sel, n: `C${i + 1}`, kind: 'comment' }))];

// 🧊 Slice 27: what a click picked — the element, a text node in it, a region of a canvas, or a 3D object in a three.js scene
const NODES = ['text', 'canvas', 'three'];
const PART_WORD = p => `${['top', 'middle', 'bottom'][Math.round((p?.y || 0) * 3)] || 'middle'} ${['left', 'centre', 'right'][Math.round((p?.x || 0) * 3)] || 'centre'}`;
export const pickKey = p => [p.sel, p.node || 'el', p.three?.name || p.three?.path || '', p.part ? `${p.part.x},${p.part.y}` : '', p.node === 'text' ? p.text : ''].join('|');
/** What a pick is, in two words: "<h2>", "TEXT", "CANVAS · top left", "3D · Hero cube". Pure. */
export const pickWord = p => (p.node === 'three' ? `3D · ${p.three?.name || p.three?.type || 'object'}` : p.node === 'canvas' ? `CANVAS · ${PART_WORD(p.part)}` : p.node === 'text' ? 'TEXT' : `<${p.tag || 'el'}>`);
/** Its words can be changed in place, $0, by the page tools: a text node, or an element with only words in it. Pure. */
export const canEdit = p => !!p.text && (p.node === 'text' || (!NODES.includes(p.node) && p.leaf === true));

// a click inside the page → one pick (newest wins on the same pick, at most INSPECT_MAX)
export const addPick = (picks, d) => { if (!d?.sel) return picks;
  const node = NODES.includes(d.node) ? d.node : undefined;
  const p = { kind: 'el', sel: String(d.sel).slice(0, 300), tag: String(d.tag || '').slice(0, 20), text: String(d.text || '').slice(0, 300), html: String(d.html || '').slice(0, 1200), rect: d.rect, sy: d.sy, css: d.css, note: '',
    ...(node ? { node } : {}), ...(d.leaf != null ? { leaf: !!d.leaf } : {}), ...(node === 'canvas' && d.part ? { part: d.part } : {}), ...(node === 'three' && d.three ? { three: d.three } : {}) };
  return [...picks.filter(x => pickKey(x) !== pickKey(p)), p].slice(-INSPECT_MAX); };

const Sel = ({ tag, sel }) => <code className="psi-sel" data-tip={sel}><b>&lt;{tag || 'el'}&gt;</b> {String(sel || '').replace(/^body > /, '')}</code>;

export function InspectPicks({ picks, setPicks, busy, onFix, onComment, onGo, onEdit = null }) {
  const [wait, setWait] = useState(''); const [err, setErr] = useState(''); const [ed, setEd] = useState({});   // ed: pick key → the words being typed
  if (!picks.length) return null;
  const note = (i, v) => setPicks(ps => ps.map((p, k) => (k === i ? { ...p, note: v } : p)));
  const act = async (k, i, fn, ...a) => { setWait(`${k}${i}`); setErr(''); try { await fn(picks[i], ...a); setPicks(ps => ps.filter((_, j) => j !== i)); } catch (e) { setErr(e.message || 'Not sent.'); } setWait(''); };
  return <ol className="psi-picks" aria-label="Inspected elements" data-testid="ws-insp-picks">{picks.map((p, i) => { const key = pickKey(p); const words = ed[key]; const three = p.node === 'three' ? p.three || {} : null;
    return <li key={key} className={`psi-card is-${p.node || 'el'}`} style={{ '--i': i }} data-testid={`ws-insp-card-${i}`}>
    <header><button type="button" className="psi-n" onClick={() => onGo(p.sel)} aria-label={`Show pick ${i + 1} in the page`} data-tip="Scroll the page to it" data-testid={`ws-insp-go-${i}`}><em className="m-num">{i + 1}</em></button>
      <span className="psi-what"><b data-testid={`ws-insp-kind-${i}`}>{pickWord(p)}</b><Sel tag={p.tag} sel={p.sel} /></span>
      <button type="button" className="psi-x" onClick={() => setPicks(ps => ps.filter((_, k) => k !== i))} aria-label={`Drop pick ${i + 1}`} data-tip="Drop it" data-testid={`ws-insp-x-${i}`}>✕</button></header>
    {three ? <q className="psi-text" data-testid={`ws-insp-3d-${i}`}>{[three.type, three.geometry, three.material].filter(Boolean).join(' · ')}{three.color ? <i className="psi-dot" style={{ background: three.color }} aria-hidden="true" /> : null}{three.path ? <small> {three.path}</small> : null}</q>
      : p.text ? <q className="psi-text">{p.text.slice(0, 140)}</q> : null}
    {words != null ? <form className="psi-edit" onSubmit={e => { e.preventDefault(); if (words.trim() && words.trim() !== p.text) act('e', i, onEdit, words.trim()); }} data-testid={`ws-insp-editform-${i}`}>
      <input className="m-input" value={words} maxLength={400} autoFocus onChange={e => setEd(x => ({ ...x, [key]: e.target.value }))} aria-label={`New words for pick ${i + 1}`} data-testid={`ws-insp-editin-${i}`} />
      <button type="submit" className="m-btn m-go" disabled={busy || !!wait || !words.trim() || words.trim() === p.text} data-tip="The page tools put your words in, $0: no mind is called. A new version files" data-testid={`ws-insp-apply-${i}`}>{wait === `e${i}` ? 'Saving…' : 'Apply · $0'}</button>
      <button type="button" className="m-btn" onClick={() => setEd(x => { const n = { ...x }; delete n[key]; return n; })} data-testid={`ws-insp-editx-${i}`}>Cancel</button></form>
      : <span className="psi-row"><input className="m-input" value={p.note} maxLength={300} onChange={e => note(i, e.target.value)} placeholder={three ? 'What should this 3D object do?' : 'What should change, or your comment'} aria-label={`What to do with pick ${i + 1}`} data-testid={`ws-insp-note-${i}`} />
        <button type="button" className="m-btn m-go" disabled={busy || !!wait} onClick={() => act('f', i, onFix)} data-tip={three ? 'Its minds change the code that makes this exact 3D object. Uses model credit' : 'A plain look ask (red, bigger, bold, centred) is done by the page tools for $0; anything more goes to its minds and uses model credit'} data-testid={`ws-insp-fix-${i}`}>{wait === `f${i}` ? 'Sending…' : 'Fix'}</button>
        <button type="button" className="m-btn" disabled={!p.note.trim() || !!wait} onClick={() => act('c', i, onComment)} data-tip="Keeps your comment on it, free. Its minds read it on every next build" data-testid={`ws-insp-comment-${i}`}>{wait === `c${i}` ? 'Saving…' : 'Comment'}</button>
        {onEdit && canEdit(p) ? <button type="button" className="m-btn" disabled={busy || !!wait} onClick={() => setEd(x => ({ ...x, [key]: p.text }))} data-tip="Change its words right here, $0" data-testid={`ws-insp-edit-${i}`}>Edit text</button> : null}</span>}
  </li>; })}{err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</ol>;
}

/** 📍 The picked elements' numbers in a gutter BESIDE the page (never on top of its content): rows from the page's own feeless-inspect-pinpos. */
export function PinGutter({ rows, pins, onGo }) {
  if (!rows?.length) return null;
  return <ol className="psi-gutter" aria-label="Picks on the page" data-testid="ws-insp-gutter">{rows.map(r => { const sel = (pins || []).find(p => String(p.n) === String(r.n))?.sel;
    return r.top + r.h < 0 || r.top > 1 ? null : <li key={r.n} style={{ top: `${Math.max(0, r.top) * 100}%`, height: `${Math.max(0.02, Math.min(r.h, 1 - Math.max(0, r.top))) * 100}%` }} className={r.kind === 'comment' ? 'is-c' : ''}>
      <button type="button" onClick={() => sel && onGo(sel)} aria-label={`Pick ${r.n}`} data-tip="Scroll the page to it" data-testid={`ws-gutter-${r.n}`}><em className="m-num">{r.n}</em></button></li>; })}</ol>;
}

export function InspectComments({ rows, onDrop, onGo }) {
  if (!rows?.length) return null;
  return <section className="psi-comments" aria-label="Your comments on elements" data-testid="ws-insp-comments"><small className="m-label">YOUR COMMENTS · ITS MINDS READ THEM</small><ol>{rows.map((c, i) => <li key={c.id}><button type="button" className="psi-n is-c" onClick={() => onGo(c.sel)} aria-label={`Show comment ${i + 1} in the page`} data-tip="Scroll the page to this element" data-testid={`ws-insp-cgo-${i}`}><em className="m-num">C{i + 1}</em></button><span><Sel tag={c.tag} sel={c.sel} /><b>{c.note}</b></span><button type="button" className="psi-x" onClick={() => onDrop(c.id)} aria-label={`Take comment ${i + 1} off`} data-tip="Take this comment off" data-testid={`ws-insp-cx-${i}`}>✕</button></li>)}</ol></section>;
}

function Side({ s, v, label }) {
  if (!s) return <figure className="psi-side is-none"><figcaption className="m-label">{label}</figcaption><p>No new page</p></figure>;
  return <figure className={`psi-side${s.found ? '' : ' is-gone'}`}><figcaption className="m-label">{label}{v ? <em className="m-num"> v{v}</em> : null}</figcaption>{s.shot ? <a href={s.shot} target="_blank" rel="noopener noreferrer" data-tip="Open the picture"><img src={s.shot} alt={`${label}: ${s.text || 'the element'}`} loading="lazy" /></a> : <p className="psi-noshot">{s.found ? 'No picture' : 'Not on this page'}</p>}{s.text ? <q>{s.text.slice(0, 120)}</q> : null}</figure>;
}

// 🔁 The next version shows each inspected element before and after (pictures from a headless browser, its words and its code)
export function InspectDiff({ runs }) {
  const list = (runs || []).filter(r => r?.rows?.length); const [at, setAt] = useState(list.length - 1);
  useEffect(() => { setAt(list.length - 1); }, [list.length]);
  const run = list[Math.max(0, Math.min(at, list.length - 1))];
  if (!run) return null;
  const pct = run.asked ? run.changed / run.asked : 0;
  return <section className="psi-diff m-live" aria-label="Inspected elements, before and after" data-testid="ws-insp-diff">
    <header><span className="psi-ring" style={{ '--p': pct }} role="img" aria-label={`${run.changed} of ${run.asked} changed`}><b className="m-num">{run.changed}/{run.asked}</b></span><span><small className="m-label">INSPECT · BEFORE → AFTER</small><strong>{run.to ? `Page ${run.from} → page ${run.to}` : `Page ${run.from} · no new page`}</strong>{run.ask ? <q>{run.ask.slice(0, 120)}</q> : null}</span></header>
    {list.length > 1 ? <div className="m-seg psi-runs" role="tablist" aria-label="Inspect rounds">{list.map((r, i) => <button key={r.at} type="button" role="tab" aria-selected={i === at} className={i === at ? 'active' : ''} onClick={() => setAt(i)} data-tip={r.ask} data-testid={`ws-insp-run-${i}`}>v{r.to || r.from}</button>)}</div> : null}
    <ol>{run.rows.map((r, i) => <li key={r.sel} style={{ '--i': i }} data-testid={`ws-insp-row-${i}`}><div className="psi-row-top"><Sel tag={r.tag} sel={r.sel} /><span className={`m-chip${r.changed ? ' ok' : ''}`}>{r.changed ? 'CHANGED' : r.gone ? 'GONE' : run.to ? 'SAME' : 'NOT BUILT'}</span></div>{r.note ? <small className="psi-ask">You: {r.note}</small> : null}
      <div className="psi-pair"><Side s={r.before} v={run.from} label="BEFORE" /><i className="psi-arrow" aria-hidden="true" /><Side s={r.after} v={run.to} label="AFTER" /></div>
      {r.before?.code || r.after?.code ? <details className="psi-code"><summary data-tip="The element's own code on both pages">Code</summary><pre className="is-before">{r.before?.code}</pre>{r.after ? <pre className="is-after">{r.after.code}</pre> : null}</details> : null}</li>)}</ol>
  </section>;
}
