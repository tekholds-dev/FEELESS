import React, { forwardRef, useMemo } from 'react';
import { langOf, tint } from '../../lib/codeTint';

// 💻 AGT-7: the code views look like an editor: line numbers, syntax colours, added (+) and removed (−) lines in the gutter, and a status bar.
// Rows: [{ n, text, kind: '' | 'add' | 'rem' }]. Past TINT_MAX lines the rest stays plain so a huge page never stalls a frame.
const TINT_MAX = 4000;
export const plainRows = text => String(text || '').split('\n').map((t, i) => ({ n: i + 1, text: t, kind: '' }));
export function diffRows(previous = '', code = '') {
  const before = previous.split('\n'); const after = code.split('\n'); let start = 0; let end = 0;
  while (start < Math.min(before.length, after.length) && before[start] === after[start]) start++;
  while (end < Math.min(before.length, after.length) - start && before[before.length - 1 - end] === after[after.length - 1 - end]) end++;
  const removed = previous ? before.slice(start, before.length - end) : []; const added = after.slice(start, after.length - end);
  const rows = after.slice(0, start).map((t, i) => ({ n: i + 1, text: t, kind: '' }));
  removed.forEach(t => rows.push({ n: null, text: t, kind: 'rem' }));
  added.forEach((t, i) => rows.push({ n: start + i + 1, text: t, kind: 'add' }));
  after.slice(after.length - end).forEach((t, i) => rows.push({ n: after.length - end + i + 1, text: t, kind: '' }));
  return { rows, added: added.length, removed: removed.length };
}
// 🖍 AGT-7: the parts its owner marked on the page, found in the code: the first line of each marked element's HTML (≥ 12 letters, spaces folded).
const fold = t => String(t || '').replace(/\s+/g, ' ').trim();
export function markLines(rows, marks) {
  const keys = (marks || []).map(m => fold(String(m?.html || '').split('>')[0] + '>')).filter(k => k.length >= 12);
  const hot = new Map(); if (!keys.length) return hot;
  rows.forEach((r, i) => { if (r.kind === 'rem') return; const t = fold(r.text); keys.forEach((k, j) => { if (!hot.has(i) && t.includes(k)) hot.set(i, j + 1); }); });
  return hot;
}
export const CodeLines = forwardRef(function CodeLines({ rows, path = 'index.html', caret = false, hot = null }, ref) {
  const lang = langOf(path);
  const body = useMemo(() => rows.map((r, i) => <span key={i} id={hot?.has(i) ? `fcv-mark-${hot.get(i)}` : undefined} className={`fcv-l${r.kind ? ` is-${r.kind}` : ''}${hot?.has(i) ? ' is-mark' : ''}`}><i className="fcv-n" aria-hidden="true">{r.n ?? ''}</i><i className="fcv-m" aria-hidden="true">{hot?.has(i) ? hot.get(i) : r.kind === 'add' ? '+' : r.kind === 'rem' ? '−' : ''}</i>
    <code>{i < TINT_MAX ? tint(r.text, lang).map(([t, k], j) => (k ? <b key={j} className={`t-${k}`}>{t}</b> : t)) : r.text}{caret && i === rows.length - 1 ? <i className="fea-caret" aria-hidden="true" /> : null}</code>{'\n'}</span>), [rows, lang, caret, hot]);
  return <pre ref={ref} className="fea-src fcv">{body}</pre>;
});
export function MarkJumps({ hot, rows }) {
  if (!hot?.size) return null; const at = [...hot.entries()].sort((a, b) => a[1] - b[1]);
  return <nav className="fcv-marks" aria-label="Marked areas in the code" data-testid="code-marks"><small>🖍 MARKED ON THE PAGE</small>{at.map(([i, n]) => <button key={n} type="button" onClick={() => document.getElementById(`fcv-mark-${n}`)?.scrollIntoView({ block: 'center', behavior: 'smooth' })} data-tip="Jump to it in the code" data-testid={`code-mark-${n}`}>{n} · line {rows[i]?.n}</button>)}</nav>;
}
export function StatusBar({ path = 'index.html', rows, extra }) {
  const lines = rows.filter(r => r.kind !== 'rem').length; const chars = rows.reduce((a, r) => a + (r.kind === 'rem' ? 0 : r.text.length + 1), 0);
  return <footer className="fcv-bar m-num"><b>{{ html: 'HTML', css: 'CSS', js: 'JavaScript' }[langOf(path)]}</b><span>{lines.toLocaleString()} lines</span><span>{chars.toLocaleString()} chars</span><span>UTF-8</span><span>LF</span>{extra ? <em>{extra}</em> : null}</footer>;
}
export function Tabs({ files, at, onPick }) {
  return <nav className="fcv-tabs" aria-label="Open files">{files.map(f => <button key={f} type="button" className={f === at ? 'is-on' : ''} aria-current={f === at} onClick={() => onPick?.(f)} data-tip={f}><i className={`fcv-dot is-${langOf(f)}`} aria-hidden="true" />{f.split('/').pop()}</button>)}</nav>;
}
