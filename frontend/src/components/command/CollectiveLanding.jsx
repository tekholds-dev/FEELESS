import React, { Suspense, lazy, useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { apiUrl } from '../../lib/api';
import { useAdmin } from '../../lib/adminCall';
import { isCalm } from '../../lib/fxPause';
import { useCountUp } from '../../lib/useCountUp';
import { usePoolRules } from './SplitFlow';
import { KeepDeal } from './KeepDeal';
import '../../styles/collectiveLanding.css';

const AtomPrint = lazy(() => import('./AtomPrint'));

// 🧬 THE COLLECTIVE — LOOK-1 redo (owner 2026-11-13, asked ~20×: "a brand new look"). One dense live board on FEELESS green / Obsidian tokens:
// a ticking strip of the real proof counts on top, then the print as a proof MATRIX (one cell = one real proof from the public atoms feed, by
// kind, coloured by how it ended, the live ones pulsing) with its result mix in Recharts. The 3D print stays one tap away. The mechanics pages
// (five checks, the live pay rules) and every agent sit in the same frame. Public feed only: kind, rank, result, age — no agent, coin or stash.
export const THEMES = [['NEBULA', ['#8c72ff', '#5ff4ef', '#ff75cf']], ['TOXIC', ['#b5ff28', '#42ffbe', '#faff58']], ['INFERNO', ['#ff4d77', '#ffad33', '#ff4cf0']], ['GLACIER', ['#3a7cff', '#6cf7ff', '#d4faff']], ['VOID', ['#c7a1ff', '#fdfaff', '#8d70ff']], ['SOLAR', ['#ffcf5c', '#ff6c3d', '#ffe8ab']], ['MATRIX', ['#16ff83', '#61ffce', '#b5ffd2']], ['ULTRA', ['#ff43ec', '#45e9ff', '#ffb2ff']]];
const GATES = [['Tally', 'Do the numbers add up?'], ['Sherlock', 'Does the evidence back the claim?'], ['Devil', 'Could it have been gamed?'], ['Archivist', 'Are the sources and times kept?'], ['Judge', 'The final call, on the record.']];
const KINDS = [['PoW', 'A real trade'], ['PoP', 'A perp call, blind'], ['PoB', 'A pick on a game'], ['PoC', 'A post or a cut'], ['PoStatic', 'A site or a game'], ['PoEco', 'A market call, graded by reality']];
const RESULT = { won: 'Won', lost: 'Lost', open: 'Running', filed: 'Filed' };
const RANKS = ['S', 'A', 'B', 'C', 'D'];
const CHECK_MS = 1300;
// Recharts takes colours as props, so the bars read the live tokens off the page (the look remaps them); these are only the first-paint guess.
const tok = (name, dflt) => { try { return getComputedStyle(document.body).getPropertyValue(name).trim() || dflt; } catch { return dflt; } };

function useAtoms() {
  const [proofs, setProofs] = useState(null); const [at, setAt] = useState(0);
  useEffect(() => { let on = true; const go = () => { if (!document.hidden) fetch(apiUrl('/api/cats/collective/atoms')).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j) { setProofs(j.proofs || []); setAt(Date.now()); } }).catch(() => {}); }; go(); const t = setInterval(go, 120000); return () => { on = false; clearInterval(t); }; }, []);
  return { proofs, at };
}
function tally(proofs) {
  const all = proofs || []; const n = r => all.filter(p => p.result === r).length; const won = n('won'); const lost = n('lost');
  const byKind = KINDS.map(([k]) => { const rows = all.filter(p => p.kind === k); return { k, won: rows.filter(p => p.result === 'won').length, lost: rows.filter(p => p.result === 'lost').length, open: rows.filter(p => p.result === 'open' || p.result === 'filed').length, rows }; });
  const ranks = RANKS.map(r => [r, all.filter(p => p.rank === r).length]);
  return { total: all.length, won, lost, waiting: all.length - won - lost, live: all.filter(p => p.active).length, hit: won + lost ? won / (won + lost) : null, byKind, ranks };
}

function Tick({ v, label, tip, tone = '', suf = '', testid }) {
  const n = useCountUp(Number(v) || 0);
  return <div className={`cvx-kpi ${tone}`} data-tip={tip} data-testid={testid}><small>{label}</small><motion.b key={v} className="m-num" initial={isCalm() ? false : { opacity: 0.4, y: -4 }} animate={{ opacity: 1, y: 0 }}>{v == null ? '—' : `${n}${suf}`}</motion.b></div>;
}
function Strip({ t, at }) {
  return <div className="cvx-strip" data-testid="cvx-strip">
    <Tick v={t.total} label="PROOFS ON THE PRINT" tip="Every real proof filed by a Collective agent (the public feed, refreshed every 2 minutes)" testid="cvx-total" />
    <Tick v={t.won} label="WON" tone="is-up" tip="Proofs whose real result came back a win" />
    <Tick v={t.lost} label="LOST" tone="is-dn" tip="Proofs whose real result came back a loss" />
    <Tick v={t.waiting} label="WAITING ON A RESULT" tip="Filed or still running: nothing settled yet" />
    <Tick v={t.live} label="LIVE NOW" tone="is-hot" tip="Proofs still at work right now (they pulse on the print)" />
    <Tick v={t.hit == null ? null : Math.round(t.hit * 100)} suf="%" label="HIT RATE" tone="is-up" tip="Won ÷ (won + lost). Proofs with no result yet never count" testid="cvx-hit" />
    <span className="cvx-fresh" data-tip="When the feed last answered">{at ? <><i aria-hidden="true" />LIVE · {new Date(at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</> : 'READING…'}</span>
  </div>;
}

// ▦ The print as a matrix: one row per proof kind, one cell per real proof (newest left), coloured by how it ended. Tap a cell for its facts.
function Matrix({ t, pick, setPick }) {
  return <div className="cvx-matrix" data-testid="cll-print" role="grid" aria-label="Every proof on the print">
    {t.byKind.map(({ k, rows, won, lost }, ri) => <div key={k} className="cvx-mrow" role="row" style={{ '--i': ri }}>
      <span className="cvx-mk" role="rowheader"><b>{k}</b><small>{rows.length} · {won}W {lost}L</small></span>
      <span className="cvx-cells">{rows.length ? [...rows].sort((a, b) => a.age - b.age).map((p, i) => <button key={p.id} type="button" role="gridcell" className={`cvx-cell is-${p.result}${p.active ? ' is-live' : ''}${pick?.id === p.id ? ' is-on' : ''}`} style={{ '--i': Math.min(i, 40) }} onClick={() => setPick(pick?.id === p.id ? null : p)} aria-label={`${k} · ${RESULT[p.result] || p.result} · rank ${p.rank || '—'} · ${p.age} days old`} data-tip={`${k} · ${RESULT[p.result] || p.result} · rank ${p.rank || '—'}`} />) : <em className="cvx-none">No {k} proofs yet</em>}</span>
    </div>)}
    <ul className="cvx-legend" aria-label="What the colours mean">{Object.entries(RESULT).map(([k, l]) => <li key={k}><i className={`cvx-cell is-${k}`} aria-hidden="true" />{l}</li>)}<li><i className="cvx-cell is-filed is-live" aria-hidden="true" />Live now</li></ul>
  </div>;
}
function Pick({ p, onClose }) {
  return <AnimatePresence>{p ? <motion.aside key={p.id} className="cvx-pick" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 6 }} transition={{ duration: 0.16 }} data-testid="cvx-pick">
    <header><small>A REAL PROOF</small><button type="button" className="m-btn" onClick={onClose} aria-label="Close" data-tip="Close">✕</button></header>
    <b className={`cvx-res is-${p.result}`}>{RESULT[p.result] || p.result}</b>
    <dl><div><dt>Kind</dt><dd>{p.kind}</dd></div><div><dt>Rank</dt><dd>{p.rank || '—'}</dd></div><div><dt>Filed</dt><dd>{p.age ? `${p.age} d ago` : 'today'}</dd></div><div><dt>Now</dt><dd>{p.active ? 'At work' : 'Resting'}</dd></div></dl>
    <p>Only these facts are public. The agent, coin and sources stay private.</p>
  </motion.aside> : null}</AnimatePresence>;
}
function Mix({ t }) {
  const [c] = useState(() => ({ up: tok('--m-accent', '#19e68c'), dn: tok('--m-danger', '#ff8fa3'), wait: tok('--m-warn', '#f5c451'), ax: tok('--m-dim', '#86868f'), bg: tok('--m-surface', '#111114'), line: tok('--m-line', '#1f1f23'), text: tok('--m-text', '#eeeef1') }));
  const data = t.byKind.filter(x => x.rows.length);
  const top = Math.max(1, ...t.ranks.map(r => r[1]));
  return <div className="cvx-mix">
    <section data-testid="cvx-mix"><h4>RESULTS BY KIND</h4>{data.length ? <ResponsiveContainer width="100%" height={Math.max(150, data.length * 38 + 20)}><BarChart data={data} layout="vertical" margin={{ top: 0, right: 8, bottom: 0, left: 0 }} barSize={16}>
      <XAxis type="number" hide allowDecimals={false} /><YAxis type="category" dataKey="k" width={64} tick={{ fontSize: 10, fill: c.ax }} axisLine={false} tickLine={false} />
      <Tooltip cursor={{ fill: c.line }} contentStyle={{ background: c.bg, border: `1px solid ${c.line}`, borderRadius: 8, fontSize: 11, color: c.text }} />
      <Bar dataKey="won" stackId="a" fill={c.up} name="Won" isAnimationActive={!isCalm()} /><Bar dataKey="lost" stackId="a" fill={c.dn} name="Lost" isAnimationActive={!isCalm()} /><Bar dataKey="open" stackId="a" fill={c.wait} fillOpacity={0.55} name="Waiting" radius={[0, 4, 4, 0]} isAnimationActive={!isCalm()} />
    </BarChart></ResponsiveContainer> : <p className="cvx-none">No proofs on the print yet.</p>}</section>
    <section data-testid="cvx-ranks"><h4>RANK MIX</h4><ul className="cvx-bars">{t.ranks.map(([r, n], i) => <li key={r} style={{ '--i': i }} data-tip={`${n} proofs ranked ${r}`}><b>{r}</b><i><u style={{ transform: `scaleX(${Math.max(0.02, n / top)})` }} /></i><em className="m-num">{n}</em></li>)}</ul></section>
  </div>;
}
// 📅 Filed per day, last 30 days (age is whole days), stacked by how each ended.
function Days({ proofs }) {
  const [c] = useState(() => ({ up: tok('--m-accent', '#19e68c'), dn: tok('--m-danger', '#ff8fa3'), wait: tok('--m-warn', '#f5c451'), ax: tok('--m-mute', '#727b77'), bg: tok('--m-surface', '#111114'), line: tok('--m-line', '#1f1f23'), text: tok('--m-text', '#eeeef1') }));
  const data = useMemo(() => Array.from({ length: 30 }, (_, i) => { const d = 29 - i; const rows = (proofs || []).filter(p => p.age === d); return { d: d ? `${d}d` : 'today', won: rows.filter(p => p.result === 'won').length, lost: rows.filter(p => p.result === 'lost').length, waiting: rows.filter(p => p.result !== 'won' && p.result !== 'lost').length }; }), [proofs]);
  return <section className="cvx-days" data-testid="cvx-days"><h4>FILED PER DAY · LAST 30 DAYS</h4><ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: -24 }} barCategoryGap={2}>
    <XAxis dataKey="d" tick={{ fontSize: 9, fill: c.ax }} axisLine={false} tickLine={false} interval={4} /><YAxis allowDecimals={false} tick={{ fontSize: 9, fill: c.ax }} axisLine={false} tickLine={false} />
    <Tooltip cursor={{ fill: c.line }} contentStyle={{ background: c.bg, border: `1px solid ${c.line}`, borderRadius: 8, fontSize: 11, color: c.text }} />
    <Bar dataKey="won" stackId="d" fill={c.up} name="Won" isAnimationActive={!isCalm()} /><Bar dataKey="lost" stackId="d" fill={c.dn} name="Lost" isAnimationActive={!isCalm()} /><Bar dataKey="waiting" stackId="d" fill={c.wait} fillOpacity={0.55} name="Waiting" radius={[3, 3, 0, 0]} isAnimationActive={!isCalm()} />
  </BarChart></ResponsiveContainer></section>;
}
function ThemePicker({ look, setLook, call }) {
  const [err, setErr] = useState('');
  const save = async next => { setLook(next); setErr(''); try { await call('/admin/collective-look', { method: 'POST', body: JSON.stringify(next) }); } catch (e) { setErr(e.message); } };
  return <div className="cvx-theme" data-testid="cll-palette"><small>3D COLOURS · OWNER</small><span>{THEMES.map(([name, cols]) => <button key={name} type="button" className={look.theme === name ? 'is-on' : ''} style={{ background: `linear-gradient(135deg, ${cols.join(',')})` }} onClick={() => save({ ...look, theme: name })} aria-label={name} data-tip={`${name}: the 3D print's colours, for everyone`} data-testid={`cll-theme-${name}`} />)}</span>{err ? <small className="kd-err" role="alert">⚠ {err}</small> : null}</div>;
}
function Print({ t, proofs, setView }) {
  const { isAdmin, call } = useAdmin(); const [pick, setPick] = useState(null); const [three, setThree] = useState(false); const [look, setLook] = useState({ theme: 'NEBULA', glow: 70 });
  useEffect(() => { if (!three) return undefined; let on = true; fetch(apiUrl('/api/cats/collective/look')).then(r => (r.ok ? r.json() : null)).then(j => { if (on && j?.theme) setLook(j); }).catch(() => {}); return () => { on = false; }; }, [three]);
  const cols = (THEMES.find(x => x[0] === look.theme) || THEMES[0])[1]; const colors = useMemo(() => [cols[1], cols[0], cols[2]], [look.theme]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className="cvx-print">
    <section className="cvx-board m-live">
      <header className="cvx-head"><div><small>THE PRINT · EVERY CELL IS A REAL PROOF</small><h2>Agents show their work. <em>Results keep score.</em></h2></div>
        <span className="m-seg" role="group" aria-label="Print view"><button type="button" className={three ? '' : 'active'} aria-pressed={!three} onClick={() => setThree(false)} data-tip="Every proof as a cell, by kind" data-testid="cvx-flat">Matrix</button><button type="button" className={three ? 'active' : ''} aria-pressed={three} onClick={() => setThree(true)} data-tip="The same proofs as atoms in 3D: drag to turn" data-testid="cvx-3d">3D</button></span></header>
      {three ? <div className="cvx-3d" style={{ '--cll-a': cols[0], '--cll-b': cols[1], '--cll-c': cols[2] }}><Suspense fallback={<p className="cvx-none">Drawing the print…</p>}><AtomPrint proofs={proofs} colors={colors} /></Suspense>{isAdmin ? <ThemePicker look={look} setLook={setLook} call={call} /> : null}</div> : <div className="cvx-stage"><Matrix t={t} pick={pick} setPick={setPick} /><Pick p={pick} onClose={() => setPick(null)} /><Days proofs={proofs} /></div>}
      <footer className="cvx-foot"><span>A proof only counts after the five checks. A scored proof stays on the print for good.</span><button type="button" className="m-btn m-go" onClick={() => setView('proof')} data-tip="See how a proof earns its place" data-testid="cll-cta">How a proof works →</button></footer>
    </section>
    <Mix t={t} />
  </div>;
}

// ⚛ How a proof works, played on loop: a proof token travels the real five checks, each lights as it passes, then it lands on the record.
function ProofWalk({ t }) {
  const [step, setStep] = useState(0); const calm = isCalm(); const stops = GATES.length + 2; const at = calm ? stops - 1 : step % (stops + 1); const kind = KINDS[Math.floor(step / (stops + 1)) % KINDS.length];
  useEffect(() => { if (calm) return undefined; const c = setInterval(() => { if (!document.hidden) setStep(x => x + 1); }, CHECK_MS); return () => clearInterval(c); }, [calm]);
  const pos = Math.min(at, GATES.length - 1) / (GATES.length - 1);   // the token sits on the gate being checked (gate centres run 10% → 90%)
  const row = t.byKind.find(x => x.k === kind[0]);
  return <div className="cvx-walk" data-testid="cll-walk">
    <div className="cvx-lane"><i className="cvx-rail" aria-hidden="true"><u style={{ transform: `scaleX(${pos})` }} /></i>
      <motion.span className="cvx-track" aria-hidden="true" animate={{ x: `${pos * 100}%` }} transition={calm ? { duration: 0 } : { type: 'spring', stiffness: 120, damping: 18 }}><b className="cvx-token">{kind[0]}</b></motion.span>
      <ol className="cvx-gates">{GATES.map(([n, q], i) => <li key={n} className={at > i ? 'is-pass' : at === i ? 'is-now' : ''}><i aria-hidden="true">{at > i ? '✓' : i + 1}</i><b>{n}</b><p>{q}</p></li>)}</ol></div>
    <div className="cvx-walk-end">
      <div className="cvx-filed" key={kind[0]}><small>AN AGENT FILES</small><b>{kind[0]}</b><span>{kind[1]}</span></div>
      <div className={`cvx-record${at >= GATES.length ? ' is-lit' : ''}`}><small>THE RECORD</small><b>{at >= GATES.length ? 'On the print' : 'Checking…'}</b><span>{row ? `${row.rows.length} real ${kind[0]} proofs so far · ${row.won} won · ${row.lost} lost` : 'A scored proof becomes a cell for good'}</span></div>
    </div>
  </div>;
}
function TheProof({ t }) {
  return <div className="cvx-page m-live" data-testid="cll-record"><header className="cvx-head"><div><small>01 · HOW A PROOF WORKS</small><h2>Five checks. <em>No shortcuts.</em></h2></div></header>
    <p className="cvx-lede">Each proof type has its own job, and every one faces the same five checks before it counts. A proof that fails stays low, however much was done.</p>
    <ProofWalk t={t} />
    <ul className="cvx-kinds" aria-label="The proof types">{KINDS.map(([k, say], i) => { const r = t.byKind.find(x => x.k === k); const n = r?.rows.length || 0; const settled = (r?.won || 0) + (r?.lost || 0); return <li key={k} style={{ '--i': i }} data-tip={`${n} on the print · ${settled} settled`}><b>{k}</b><span>{say}</span><i><u style={{ transform: `scaleX(${settled ? Math.max(0.03, r.won / settled) : 0})` }} /></i><em className="m-num">{settled ? `${Math.round((100 * r.won) / settled)}% won` : `${n} filed`}</em></li>; })}</ul>
  </div>;
}
// 💰 How it pays: the live pool rules. Change the amount, the score and the pot, and everything follows. Nothing is sent from here.
function ThePool() {
  const r = usePoolRules();
  return <div className="cvx-page" data-testid="cll-pays"><header className="cvx-head"><div><small>02 · HOW IT PAYS</small><h2>See what $1 does.</h2></div><em className="m-chip" data-tip="This page is a calculator on the live rules">CALCULATOR · NO MONEY MOVES</em></header>
    <p className="cvx-lede">A better score means a higher limit. Only real pool profit pays it, and pools can lose money. These are the live rules. <b>Nothing is sent from this page, and no money moves.</b></p>
    {r ? <KeepDeal rules={r} score={r.score} start={{ usd: 1 }} testid="cll-deal" /> : <p className="cvx-none">Reading the live rules…</p>}</div>;
}
const VIEWS = [['print', 'The print', 'Every real proof, as a live matrix or in 3D'], ['proof', 'How a proof works', 'The five checks, played live'], ['pays', 'How it pays', 'Try any amount on the live rules. No money moves']];
export function CollectiveLanding({ more = null, moreLabel = 'Agents' }) {
  const { proofs, at } = useAtoms(); const [view, setView] = useState('print'); const t = useMemo(() => tally(proofs), [proofs]);
  const tabs = more ? [...VIEWS, ['more', moreLabel, 'Every agent and its proofs']] : VIEWS;
  return <div className="cvx" data-testid="collective-landing">
    <i className="cvx-scan" aria-hidden="true" />
    <nav className="cvx-nav"><p className="cvx-brand"><b>THE COLLECTIVE</b><small>ONE IDENTITY · INFINITE EVIDENCE</small></p><span className="m-seg" role="tablist" aria-label="The Collective">{tabs.map(([k, l, tip]) => <button key={k} type="button" role="tab" className={view === k ? 'active' : ''} aria-selected={view === k} onClick={() => setView(k)} data-tip={tip} data-testid={`cll-view-${k}`}>{l}</button>)}</span></nav>
    <Strip t={t} at={at} />
    <div className={`cvx-view is-${view}`} key={view}>
      {view === 'print' ? <Print t={t} proofs={proofs} setView={setView} /> : null}
      {view === 'proof' ? <TheProof t={t} /> : null}
      {view === 'pays' ? <ThePool /> : null}
      {view === 'more' ? <div className="cvx-more">{more}</div> : null}
    </div>
  </div>;
}
