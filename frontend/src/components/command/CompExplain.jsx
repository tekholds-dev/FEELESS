import React, { useMemo, useState } from 'react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import '../../styles/compExplain.css';

// 🔍 AGX-5 · COMP EXPLAINED (owner 2026-11-14: "amaze me" — read at a glance). Pure helpers + three views:
//   · AttnExplained: WHERE IT LOOKS as the input words lit by how much it leaned on them, plus one plain sentence; the heads blend into one
//     view (split them on demand). Replaces the grey H1–H8 grid.
//   · DatasetPulse: THE DATASET as one sentence and a chart of right / wrong rows per proof type racing to the fine-tune goal.
//   · examVerdict: COMP v2's exam in one plain line (where it stands against the best flagship and the always-majority baseline).
const clean = t => String(t ?? '').replace(/\s+/g, ' ').trim();
const shown = t => String(t ?? '').replace(/\n/g, '⏎').replace(/ /g, '·') || '∅';
const blank = t => !clean(t) || t === '∅' || /^[\W_]+$/.test(clean(t));

/** Pure: the attention of the last block → what the LAST token (the one guessing what comes next) leaned on, all heads blended and per head.
 *  → null, or { tokens, w (0..1 per token, blended, max = 1), heads: [{ top, w }], top, low, ratio, last } */
export function attnRead(attn) {
  const toks = attn?.tokens || []; const H = (attn?.heads || []).filter(h => Array.isArray(h) && h.length === toks.length); const T = toks.length;
  if (T < 2 || !H.length) return null;
  const rowOf = h => toks.map((_, j) => Math.max(0, Number(h[T - 1]?.[j]) || 0));
  const per = H.map(rowOf); const blend = toks.map((_, j) => per.reduce((s, r) => s + r[j], 0) / per.length);
  const norm = r => { const m = Math.max(...r, 1e-9); return r.map(v => v / m); };
  const idx = toks.map((t, j) => j).filter(j => j < T - 1 && !blank(toks[j]));
  const pool = idx.length >= 2 ? idx : toks.map((_, j) => j).filter(j => j < T - 1);
  const top = pool.reduce((a, j) => (blend[j] > blend[a] ? j : a), pool[0]);
  const rest = pool.filter(j => j !== top && blend[j] > 0); const low = rest.length ? rest.reduce((a, j) => (blend[j] < blend[a] ? j : a), rest[0]) : null;
  const ratio = low != null && blend[low] > 0 ? blend[top] / blend[low] : null;
  return { tokens: toks, w: norm(blend), heads: per.map(r => { const n = norm(r); const t = pool.reduce((a, j) => (r[j] > r[a] ? j : a), pool[0]); return { top: t, w: n }; }), top, low, ratio, last: T - 1 };
}

/** Pure: the plain sentence. */
export function attnSay(r) {
  if (!r) return '';
  const q = j => `“${clean(r.tokens[j]) || shown(r.tokens[j])}”`;
  const lead = `Guessing what comes after ${q(r.last)}, it leaned on ${q(r.top)} most`;
  if (r.ratio == null || r.low == null) return `${lead}.`;
  const x = r.ratio >= 10 ? Math.round(r.ratio) : Math.round(r.ratio * 10) / 10;
  return `${lead}: ${x}× more than ${q(r.low)}.`;
}

function Strip({ tokens, w, last, testid }) {
  return <span className="cex-strip" data-testid={testid}>{tokens.map((t, j) => <span key={j} className={j === last ? 'is-now' : ''} style={{ '--w': j === last ? 0 : w[j].toFixed(3) }}
    data-tip={j === last ? 'The word it is reading from' : `${Math.round(w[j] * 100)}% of its strongest pull`}>{shown(t)}</span>)}</span>;
}

/** WHERE IT LOOKS, explained: the input lit by attention + one plain line; heads blended (split on demand). */
export function AttnExplained({ peek }) {
  const r = useMemo(() => attnRead(peek?.attn), [peek]); const [split, setSplit] = useState(false);
  if (!r) return null;
  return <div className="cex-attn mlf-attn" data-testid="mlf-attn">
    <div className="mlf-attn-head"><small className="m-label">WHERE IT LOOKS · STEP {peek.step}</small>
      {r.heads.length > 1 ? <button type="button" className="m-btn cex-split" aria-pressed={split} onClick={() => setSplit(!split)} data-tip="Each head learns its own way to look back. Blended = what they do together" data-testid="cex-split">{split ? 'Blend the heads' : `Split ${r.heads.length} heads`}</button> : null}</div>
    <p className="cex-say" data-testid="cex-say">{attnSay(r)}</p>
    <Strip tokens={r.tokens} w={r.w} last={r.last} testid="cex-blend" />
    {split ? <ol className="cex-heads" data-testid="cex-heads">{r.heads.map((h, i) => <li key={i} style={{ '--i': i }}><b>H{i + 1}</b><Strip tokens={r.tokens} w={h.w} last={r.last} /><small>→ “{clean(r.tokens[h.top]) || shown(r.tokens[h.top])}”</small></li>)}</ol> : null}
    <small className="cex-key"><i aria-hidden="true" /><span>Brighter = it leaned on that word more. Underlined = the word it reads from.</span></small></div>;
}

/** Pure: the dataset in one sentence + chart rows. */
export function datasetRead(d) {
  const kinds = d?.kinds || []; const goal = d?.goals?.rows || 1000; const pg = d?.goals?.pairs || 200;
  const near = kinds.reduce((a, k) => (!a || k.rows > a.rows ? k : a), null);
  const rows = kinds.map(k => ({ kind: k.kind, right: k.won, wrong: k.lost, flat: k.flat || 0, open: k.open }));
  if (d?.duels) rows.push({ kind: '⚔ Duels', right: d.duels, wrong: d.duels, flat: 0, open: 0 });
  const say = !d ? '' : !d.rows ? 'No settled proofs yet: every proof your agents file and settle becomes a row here.'
    : `${d.rows.toLocaleString()} rows to learn from. Closest to a fine-tune: ${near.kind} at ${Math.round((near.rows / goal) * 100)}% of ${goal.toLocaleString()}. ${d.pairs} right-vs-wrong pairs, ${Math.round((d.pairs / pg) * 100)}% of the ${pg} that make preference training worth it.`;
  return { rows, say, goal };
}

const tipStyle = { background: 'var(--m-surface)', border: '1px solid var(--m-line-hi)', borderRadius: 8, fontSize: 11, color: 'var(--m-text)' };
export function DatasetPulse({ d }) {
  const r = useMemo(() => datasetRead(d), [d]);
  if (!d) return null;
  return <div className="cex-data" data-testid="cex-data"><p className="cex-say" data-testid="cex-data-say">{r.say}</p>
    {r.rows.some(x => x.right + x.wrong + x.flat) ? <div className="cex-chart" data-tip="Each proof type's settled rows: right (green), wrong (red), flat (grey)"><ResponsiveContainer width="100%" height={Math.max(120, r.rows.length * 30)}>
      <BarChart data={r.rows} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 4 }} barCategoryGap={6}>
        <XAxis type="number" hide /><YAxis type="category" dataKey="kind" width={78} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: 'var(--m-dim)' }} />
        <Tooltip contentStyle={tipStyle} cursor={{ fill: 'transparent' }} />
        <Bar dataKey="right" stackId="a" fill="var(--m-accent)" radius={[4, 0, 0, 4]} isAnimationActive={false} />
        <Bar dataKey="wrong" stackId="a" fill="var(--m-danger)" isAnimationActive={false} />
        <Bar dataKey="flat" stackId="a" fill="var(--m-mute)" radius={[0, 4, 4, 0]} isAnimationActive={false} /></BarChart></ResponsiveContainer></div> : null}</div>;
}

/** Pure: COMP v2's exam in one line. */
export function examVerdict(exam) {
  const ex = (exam?.examinees || []).filter(e => e.score); const comp = ex.find(e => e.id === 'comp'); if (!comp) return '';
  const base = ex.find(e => e.id === 'baseline'); const flag = ex.filter(e => e.kind === 'flagship').sort((a, b) => b.score.acc - a.score.acc)[0];
  const p = v => `${Math.round(v * 100)}%`; const pts = (a, b) => Math.round(Math.abs(a - b) * 100);
  const vsBase = base ? (comp.score.acc > base.score.acc ? `${pts(comp.score.acc, base.score.acc)} points above always-guess-the-majority (${p(base.score.acc)})` : `not yet above always-guess-the-majority (${p(base.score.acc)})`) : '';
  const vsFlag = flag ? (comp.score.acc >= flag.score.acc ? `level with or ahead of ${flag.name} (${p(flag.score.acc)})` : `${pts(comp.score.acc, flag.score.acc)} points behind ${flag.name} (${p(flag.score.acc)})`) : 'no flagship sat it (no key saved)';
  return `COMP v2 got ${p(comp.score.acc)} right: ${[vsBase, vsFlag].filter(Boolean).join(', ')}.`;
}
