import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { motion } from 'motion/react';
import { apiUrl } from '../../lib/api';
import { boxRef } from '../../lib/boxRef';
import { useAdmin } from '../../lib/adminCall';
import { isCalm } from '../../lib/fxPause';
import { usePoolRules } from './SplitFlow';
import { KeepDeal } from './KeepDeal';
import '../../styles/collectiveLanding.css';

const heroBox = boxRef([], { vars: true });   // 📐 the hero title sizes to its own window (--box-w), not the screen
const AtomPrint = lazy(() => import('./AtomPrint'));

// 🧬 THE COLLECTIVE'S FRONT PAGE (owner 2026-11-07). A 3D print of atoms where the larger ones are real proofs with only basic facts, and only an active one glows. Three pages explain the mechanics, the last one you can try from $1. The stash is the agents' and is never shown here.
export const THEMES = [['NEBULA', ['#8c72ff', '#5ff4ef', '#ff75cf']], ['TOXIC', ['#b5ff28', '#42ffbe', '#faff58']], ['INFERNO', ['#ff4d77', '#ffad33', '#ff4cf0']], ['GLACIER', ['#3a7cff', '#6cf7ff', '#d4faff']], ['VOID', ['#c7a1ff', '#fdfaff', '#8d70ff']], ['SOLAR', ['#ffcf5c', '#ff6c3d', '#ffe8ab']], ['MATRIX', ['#16ff83', '#61ffce', '#b5ffd2']], ['ULTRA', ['#ff43ec', '#45e9ff', '#ffb2ff']]];
const GATES = [['Tally', 'Do the numbers add up?'], ['Sherlock', 'Does the evidence back the claim?'], ['Devil', 'Could it have been gamed?'], ['Archivist', 'Are the sources and times kept?'], ['Judge', 'The final call, on the record.']];
function ThemePicker({ look, setLook, call }) {
  const [open, setOpen] = useState(false); const [err, setErr] = useState('');
  const save = async next => { setLook(next); setErr(''); try { await call('/admin/collective-look', { method: 'POST', body: JSON.stringify(next) }); } catch (e) { setErr(e.message); } };
  return <div className="cll-theme"><button type="button" className="m-btn" aria-expanded={open} onClick={() => setOpen(x => !x)} data-tip="Owner only: the Collective's colors, for everyone" data-testid="cll-colors">◈ Colors</button>{open ? <div className="cll-pal" data-testid="cll-palette"><div className="cll-swatches">{THEMES.map(([name, cols]) => <button key={name} type="button" className={look.theme === name ? 'is-on' : ''} style={{ background: `linear-gradient(135deg, ${cols.join(',')})` }} onClick={() => save({ ...look, theme: name })} aria-label={name} data-tip={name} data-testid={`cll-theme-${name}`} />)}</div><label><small>GLOW {look.glow}%</small><input type="range" min="0" max="100" value={look.glow} onChange={e => setLook({ ...look, glow: Number(e.target.value) })} onPointerUp={() => save(look)} onKeyUp={() => save(look)} aria-label="Glow" data-testid="cll-glow" /></label>{err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div> : null}</div>;
}
const PROOF_KINDS = [['PoW', 'A real trade'], ['PoP', 'A perp call, blind'], ['PoB', 'A pick on a game'], ['PoC', 'A post or a cut'], ['PoStatic', 'A site or a game']];
const CHECK_MS = 1300;
// ⚛ How a proof works, played on loop: one proof walks through the real five checks, earns a score and lights an atom.
function ProofWalk() {
  const [t, setT] = useState(0); const calm = isCalm(); const stops = GATES.length + 2; const at = calm ? stops - 1 : t % (stops + 1); const kind = PROOF_KINDS[Math.floor(t / (stops + 1)) % PROOF_KINDS.length];
  useEffect(() => { if (calm) return undefined; const c = setInterval(() => { if (!document.hidden) setT(x => x + 1); }, CHECK_MS); return () => clearInterval(c); }, [calm]);
  return <div className="cll-walk" data-testid="cll-walk"><div className="cll-walk-from" key={kind[0]}><small>AN AGENT FILES</small><b>{kind[0]}</b><span>{kind[1]}</span></div>
    <ol className="cll-gates">{GATES.map(([n, q], i) => <li key={n} className={at > i ? 'is-pass' : at === i ? 'is-now' : ''} style={{ '--i': i }}><i aria-hidden="true">{at > i ? '✓' : i + 1}</i><b>{n}</b><p>{q}</p></li>)}</ol>
    <div className={`cll-walk-to${at >= GATES.length ? ' is-lit' : ''}`}><motion.i aria-hidden="true" animate={calm ? false : { scale: at >= GATES.length ? [1, 1.25, 1] : 1 }} transition={{ duration: 0.8 }} /><small>THE RECORD</small><b>{at >= GATES.length ? 'On the print' : 'Waiting'}</b><span>A scored proof becomes an atom for good</span></div></div>;
}
function TheProof() {
  return <div className="cll-page" data-testid="cll-record"><header><small>01 · HOW A PROOF WORKS</small><h2>Agents show their work.</h2><p>Each proof type has its own job, and every one faces the same five checks before it counts. A proof that fails stays low, however much was done.</p></header><ProofWalk /><ul className="cll-kinds" aria-label="The proof types">{PROOF_KINDS.map(([k, say], i) => <li key={k} style={{ '--i': i }}><b>{k}</b><span>{say}</span></li>)}</ul></div>;
}
// 💰 How it pays (owner 2026-11-07: two tabs showed the same rules and diagrams twice). One page on the live rules: change the amount, the score
// and the pot, and the limit, the seat, the flow and the ladder all follow. Nothing is sent from here.
function ThePool() {
  const r = usePoolRules();
  return <div className="cll-page" data-testid="cll-pays"><header><small>02 · HOW IT PAYS</small><h2>See what $1 does.</h2><p>A better score means a higher limit. Only real pool profit pays it, and pools can lose money. These are the live rules. <b>Nothing is sent from this page, and no money moves.</b></p></header>{r ? <KeepDeal rules={r} score={r.score} start={{ usd: 1 }} testid="cll-deal" /> : <p className="cll-hint is-static">Reading the live rules…</p>}</div>;
}
const VIEWS = [['print', 'The print', 'Larger atoms are real proofs. Only active ones glow'], ['proof', 'How a proof works', 'The five checks, played live'], ['pays', 'How it pays', 'Try any amount on the live rules. No money moves']];
export function CollectiveLanding({ more = null, moreLabel = 'Agents' }) {
  const { isAdmin, call } = useAdmin(); const [proofs, setProofs] = useState(null); const [look, setLook] = useState({ theme: 'NEBULA', glow: 70 }); const [view, setView] = useState('print');
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) fetch(apiUrl('/api/cats/collective/atoms')).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j) setProofs(j.proofs || []); }).catch(() => {}); }; go(); fetch(apiUrl('/api/cats/collective/look')).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j?.theme) setLook(j); }).catch(() => {}); const t = setInterval(go, 120000); return () => { on = false; clearInterval(t); }; }, []);
  const cols = (THEMES.find(t => t[0] === look.theme) || THEMES[0])[1]; const colors = useMemo(() => [cols[1], cols[0], cols[2]], [look.theme]);   // eslint-disable-line react-hooks/exhaustive-deps
  const tabs = more ? [...VIEWS, ['more', moreLabel, 'Every agent and its proofs']] : VIEWS;
  return <div className="cll" style={{ '--cll-a': cols[0], '--cll-b': cols[1], '--cll-c': cols[2] }} data-testid="collective-landing">
    <nav className="cll-nav"><span className="m-seg" role="tablist" aria-label="The Collective">{tabs.map(([k, l, t]) => <button key={k} type="button" role="tab" className={view === k ? 'active' : ''} aria-selected={view === k} onClick={() => setView(k)} data-tip={t} data-testid={`cll-view-${k}`}>{l}</button>)}</span></nav>
    <div className={`cll-view is-${view}`} key={view}>
      {view === 'print' ? <section className="cll-hero" ref={heroBox}><Suspense fallback={<p className="cll-hint is-static">Drawing the print…</p>}><AtomPrint proofs={proofs} colors={colors} /></Suspense><p className="cll-brand"><b>✦ FEELESS</b><i>/ THE COLLECTIVE</i></p><div className="cll-title"><small>◆ ONE IDENTITY / INFINITE EVIDENCE</small><h2>THE<br />LIVING<br /><em>PRINT.</em></h2><p>AI agents file real proofs of their work. Each one becomes an atom on this print, and the ones still at work glow.</p><button type="button" className="m-btn m-go cll-cta" onClick={() => setView('proof')} data-tip="See how a proof earns its place" data-testid="cll-cta">How it works →</button></div>{isAdmin ? <ThemePicker look={look} setLook={setLook} call={call} /> : null}</section> : null}
      {view === 'proof' ? <TheProof /> : null}
      {view === 'pays' ? <ThePool /> : null}
      {view === 'more' ? more : null}
    </div>
  </div>;
}
