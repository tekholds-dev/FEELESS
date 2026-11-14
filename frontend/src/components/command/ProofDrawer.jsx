import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { isCalm } from '../../lib/fxPause';
import { ProofSubmit } from './ProofKit';
import '../../styles/proofDrawer.css';

// 🗂 AGX-2 · EVERY PROOF STEP IN THE DESK (owner 2026-11-14): a drawer under the code / preview panes of a PoStatic build. File (what is filed,
// version by version) · Grade (👍 / 👎 + why, kept with the grade) · Re-run (one tap asks both minds again, the why pre-filled) · Send (the
// same signed send to the Collective pot the folder already has — no new money path) · Compare (any two saved versions side by side, with how
// many lines moved). All real: psFolders, ws_version, ps_mark, ws_build.
const STEPS = [['file', '🗂', 'File'], ['grade', '⚖', 'Grade'], ['rerun', '↻', 'Re-run'], ['send', '🪙', 'Send'], ['compare', '⇆', 'Compare']];

/** Pure: lines added / removed going from a to b (blank lines and indentation ignored; a moved line counts as kept). */
export function lineDiff(a, b) {
  const bag = s => { const m = new Map(); String(s || '').split('\n').map(x => x.trim()).filter(Boolean).forEach(x => m.set(x, (m.get(x) || 0) + 1)); return m; };
  const A = bag(a); const B = bag(b); let added = 0; let removed = 0;
  B.forEach((n, k) => { added += Math.max(0, n - (A.get(k) || 0)); }); A.forEach((n, k) => { removed += Math.max(0, n - (B.get(k) || 0)); });
  return { added, removed };
}

function Version({ v, side }) {
  if (!v) return <div className="pwr-v is-wait">Reading…</div>;
  if (v.err) return <div className="pwr-v is-wait" role="alert">⚠ {v.err}</div>;
  return <figure className="pwr-v" data-testid={`pdr-v-${side}`}><figcaption><b className="m-num">v{v.i}</b><span>{v.by || 'its minds'}</span><small className="m-num">{v.lines} lines</small></figcaption>
    <iframe title={`Version ${v.i}`} sandbox="allow-scripts" srcDoc={v.preview} /></figure>;
}

export default function ProofDrawer({ cat, row, work, doc, send, onFiled }) {
  const [open, setOpen] = useState(false); const [step, setStep] = useState('file'); const [rows, setRows] = useState([]); const [why, setWhy] = useState(''); const [ask, setAsk] = useState('');
  const [busy, setBusy] = useState(''); const [say, setSay] = useState(''); const n = Number(doc?.versions || 0); const [pick, setPick] = useState([0, 0]); const [vers, setVers] = useState({}); const calm = isCalm();
  const load = useCallback(() => work(cat.id, { op: 'state' }).then(j => setRows((j.psFolders || []).filter(f => f.ws === row.id))).catch(() => {}), [cat.id, row.id, work]);
  useEffect(() => { load(); }, [load, n, open]);   // the header says what is filed even while folded
  const f = rows[0] || null;
  useEffect(() => { setWhy(f?.gradeWhy || ''); }, [f?.id, f?.gradeWhy]);
  useEffect(() => { setPick([Math.max(1, n - 1), n]); }, [n]);
  useEffect(() => { if (step === 'rerun' && !ask && f?.graded === 'wrong' && f.gradeWhy) setAsk(f.gradeWhy); }, [step, f?.id]);   // eslint-disable-line react-hooks/exhaustive-deps
  const getV = useCallback(i => { if (!i || vers[i]) return; setVers(x => ({ ...x, [i]: null })); work(cat.id, { op: 'ws_version', text: row.id, i }).then(j => setVers(x => ({ ...x, [i]: j.version }))).catch(e => setVers(x => ({ ...x, [i]: { err: e.message } }))); }, [cat.id, row.id, work, vers]);
  useEffect(() => { if (open && step === 'compare') { getV(pick[0]); getV(pick[1]); } }, [open, step, pick]);   // eslint-disable-line react-hooks/exhaustive-deps
  const diff = useMemo(() => (vers[pick[0]]?.html != null && vers[pick[1]]?.html != null ? lineDiff(vers[pick[0]].html, vers[pick[1]].html) : null), [vers, pick]);
  const grade = async g => { if (!f) return; setBusy('grade'); setSay(''); try { const j = await work(cat.id, { op: 'ps_mark', job: f.id, text: g, tools: { why: why.trim() } }); const mine = (j.psFolders || []).filter(x => x.ws === row.id); setRows(mine); onFiled?.('psFolders', j.psFolders); setSay(g === 'right' ? 'Marked working.' : 'Marked not working. Re-run it with that why?'); if (g === 'wrong') { setAsk(why.trim()); } } catch (e) { setSay(e.message); } finally { setBusy(''); } };
  const rerun = async () => { const t = ask.trim(); if (!t || !send) return; setBusy('rerun'); setSay(''); try { await send(`Run it again and fix this: ${t}. Keep everything else that works.`, 'both'); setSay('Both minds are on it. The new version lands in the preview above.'); setAsk(''); } finally { setBusy(''); } };
  const graded = f?.graded === 'right' ? 'is-good' : f?.graded === 'wrong' ? 'is-bad' : '';
  return <section className={`pwr${open ? ' is-open' : ''}`} aria-label="Proof steps" data-testid="proof-drawer">
    <header className="pwr-h">
      <button type="button" className="pwr-tog" aria-expanded={open} onClick={() => setOpen(o => !o)} data-tip={open ? 'Fold the drawer away' : 'Every step of this proof, here: file, grade, re-run, send, compare'} data-testid="pdr-toggle">
        <i aria-hidden="true">{open ? '▾' : '▴'}</i><b>PROOF STEPS</b><small>{f ? `PoStatic #${f.n} · v${f.version || n}` : n ? `v${n} · not filed yet` : 'nothing built yet'}</small>
        {f ? <em className={`pwr-chip ${graded}`}>{f.graded === 'right' ? '👍 works' : f.graded === 'wrong' ? '👎 not yet' : 'ungraded'}</em> : null}</button>
      <div className="m-seg pwr-steps" role="tablist" aria-label="Steps">{STEPS.map(([k, ic, l], i) => <button key={k} type="button" role="tab" aria-selected={open && step === k} className={open && step === k ? 'active' : ''} onClick={() => { setStep(k); setOpen(true); }} data-testid={`pdr-step-${k}`} style={{ '--i': i }}><span aria-hidden="true">{ic}</span> {l}</button>)}</div>
    </header>
    {open ? <motion.div key={step} className="pwr-body" initial={calm ? false : { opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.16 }} role="tabpanel" data-testid={`pdr-panel-${step}`}>
      {step === 'file' ? (rows.length ? <ol className="pwr-files">{rows.map((x, i) => <li key={x.id} style={{ '--i': i }} className={x.graded === 'right' ? 'is-good' : x.graded === 'wrong' ? 'is-bad' : ''}>
        <b className="m-num">#{x.n}</b><span>{x.topic}<small>v{x.version} · {x.by || 'its minds'}{x.gradeWhy ? ` · “${x.gradeWhy}”` : ''}</small></span><em>{x.graded === 'right' ? '👍' : x.graded === 'wrong' ? '👎' : '—'}</em>
        {x.version && x.version !== n ? <button type="button" className="m-btn" onClick={() => { setPick([x.version, n]); setStep('compare'); }} data-tip="Set this version beside the newest" data-testid={`pdr-cmp-${x.id}`}>⇆ vs v{n}</button> : <small className="pwr-now">newest</small>}</li>)}</ol>
        : <p className="pwr-none">Nothing filed from this folder yet. Every finished version files itself as a PoStatic here.</p>) : null}
      {step === 'grade' ? (f ? <div className="pwr-grade">
        <p>Only you know if it works. Your why stays with the grade and is offered to the next re-run.</p>
        <textarea className="m-input" rows={2} maxLength={280} value={why} onChange={e => setWhy(e.target.value)} placeholder="Why? e.g. the buy button does nothing on a phone" aria-label="Why this grade" data-testid="pdr-why" />
        <span className="pwr-row"><button type="button" className={`m-btn${f.graded === 'right' ? ' m-go' : ''}`} disabled={!!busy} onClick={() => grade('right')} data-tip="It works" data-testid="pdr-good">👍 It works</button>
          <button type="button" className={`m-btn pwr-bad${f.graded === 'wrong' ? ' is-on' : ''}`} disabled={!!busy} onClick={() => grade('wrong')} data-tip="It does not work yet" data-testid="pdr-bad">👎 Not yet</button><small className="m-num">{why.length}/280</small></span>
      </div> : <p className="pwr-none">Nothing to grade yet: no version is filed.</p>) : null}
      {step === 'rerun' ? <div className="pwr-grade">
        <p>Both minds build it again from the current page. <b>This is a paid model call</b> on its own credit, started by your tap.</p>
        <textarea className="m-input" rows={2} maxLength={400} value={ask} onChange={e => setAsk(e.target.value)} placeholder="What should change?" aria-label="What to change" data-testid="pdr-ask" />
        <span className="pwr-row"><button type="button" className="m-btn m-go" disabled={!!busy || !!doc?.busy || !ask.trim()} onClick={rerun} data-testid="pdr-rerun">{doc?.busy ? 'Building…' : '↻ Re-run with both minds'}</button></span>
      </div> : null}
      {step === 'send' ? (f ? <div className="pwr-send"><p>Send this PoStatic to the Collective pot. Your wallet signs the one transfer, and it shows the amount first.</p><ProofSubmit cat={cat} work={work} f={f} kind="PoStatic" /></div>
        : <p className="pwr-none">File a version first, then it can go to the pot.</p>) : null}
      {step === 'compare' ? (n < 2 ? <p className="pwr-none">One version so far. Build a second and they sit side by side here.</p> : <div className="pwr-cmp">
        <span className="pwr-row">{[0, 1].map(s => <label key={s} className="pwr-pick"><small>{s ? 'B' : 'A'}</small><select className="m-input" value={pick[s]} onChange={e => setPick(p => (s ? [p[0], Number(e.target.value)] : [Number(e.target.value), p[1]]))} data-testid={`pdr-pick-${s ? 'b' : 'a'}`}>
          {Array.from({ length: n }, (_, i) => n - i).map(i => <option key={i} value={i}>v{i}{i === n ? ' · newest' : ''}</option>)}</select></label>)}
          {diff ? <span className="pwr-diff" data-testid="pdr-diff"><b className="m-num is-add">+{diff.added}</b><b className="m-num is-del">−{diff.removed}</b><small>lines A → B</small></span> : null}</span>
        <div className="pwr-two"><Version v={vers[pick[0]]} side="a" /><Version v={vers[pick[1]]} side="b" /></div></div>) : null}
      {say ? <p className="pwr-say" role="status" data-testid="pdr-say">{say}</p> : null}
    </motion.div> : null}
  </section>;
}
