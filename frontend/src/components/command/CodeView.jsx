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
export const CodeLines = forwardRef(function CodeLines({ rows, path = 'index.html', caret = false }, ref) {
  const lang = langOf(path);
  const body = useMemo(() => rows.map((r, i) => <span key={i} className={`fcv-l${r.kind ? ` is-${r.kind}` : ''}`}><i className="fcv-n" aria-hidden="true">{r.n ?? ''}</i><i className="fcv-m" aria-hidden="true">{r.kind === 'add' ? '+' : r.kind === 'rem' ? '−' : ''}</i>
    <code>{i < TINT_MAX ? tint(r.text, lang).map(([t, k], j) => (k ? <b key={j} className={`t-${k}`}>{t}</b> : t)) : r.text}{caret && i === rows.length - 1 ? <i className="fea-caret" aria-hidden="true" /> : null}</code>{'\n'}</span>), [rows, lang, caret]);
  return <pre ref={ref} className="fea-src fcv">{body}</pre>;
});
export function StatusBar({ path = 'index.html', rows, extra }) {
  const lines = rows.filter(r => r.kind !== 'rem').length; const chars = rows.reduce((a, r) => a + (r.kind === 'rem' ? 0 : r.text.length + 1), 0);
  return <footer className="fcv-bar m-num"><b>{{ html: 'HTML', css: 'CSS', js: 'JavaScript' }[langOf(path)]}</b><span>{lines.toLocaleString()} lines</span><span>{chars.toLocaleString()} chars</span><span>UTF-8</span><span>LF</span>{extra ? <em>{extra}</em> : null}</footer>;
}
export function Tabs({ files, at, onPick }) {
  return <nav className="fcv-tabs" aria-label="Open files">{files.map(f => <button key={f} type="button" className={f === at ? 'is-on' : ''} aria-current={f === at} onClick={() => onPick?.(f)} data-tip={f}><i className={`fcv-dot is-${langOf(f)}`} aria-hidden="true" />{f.split('/').pop()}</button>)}</nav>;
}
