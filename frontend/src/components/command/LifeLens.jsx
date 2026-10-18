import React, { useEffect, useMemo, useState } from 'react';
import { genRisk, tug, dedupeAutopsies, readAs, missedWord, dropFrac, winRate, genEdge, genTimeline, genBoard } from '../../lib/lifeLens';
import '../../styles/lifeLens.css';

// 🧬 THE LIFE LENS (owner, 2026-10-15: "a cool way to show stuff like this in live realtime meta degen animation"): the generations, the rug
// autopsy and the creed were a wall of unstyled text. Now: one pod per role (its gen, life left before replacement, wins vs losses, its
// lesson, the generations it replaced as tombstones), a wall of rug cards (how far it fell, what we read, what we missed) and the creed folded.
// A new generation re-keys its pod so the rebirth plays; a pod near replacement pulses. transform / opacity only.

const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - Number(t || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
const STATUS = { ACTIVE: ['🟢', 'ACTIVE', 'is-good'], PROBATION: ['⚠', 'PROBATION', 'is-warn'], SHADOW: ['👻', 'SHADOW', 'is-dim'], RETIRED: ['☠', 'RETIRED', 'is-dim'], BENCHED: ['⏸', 'BENCHED', 'is-dim'] };

// a number that flashes when it changes (re-keyed by value → the one-shot animation replays)
const Flip = ({ v, children }) => <b className="lfl-flip" key={String(v)}>{children ?? v}</b>;

// the live win ring: arc = win rate, the dot orbits faster the busier the generation is (decisions on record)
function WinRing({ r, busy }) {
  const c = 2 * Math.PI * 22; const f = r == null ? 0 : r / 100;
  return <span className={`lfl-ring ${r == null ? 'is-none' : r >= 55 ? 'is-good' : r < 45 ? 'is-bad' : 'is-calm'}`} style={{ '--spin': `${Math.max(2.5, 9 - Math.min(6, busy / 6))}s` }} aria-hidden>
    <svg viewBox="0 0 52 52"><circle cx="26" cy="26" r="22" className="lfl-ring-bg" /><circle cx="26" cy="26" r="22" className="lfl-ring-fg" strokeDasharray={`${(c * f).toFixed(1)} ${c.toFixed(1)}`} /></svg>
    <i className="lfl-orbit"><i /></i><em>{r == null ? '—' : <Flip v={r}>{r}%</Flip>}</em></span>;
}

function Meter({ label, frac, word, tone, tip }) {
  return <span className={`lfl-meter ${tone || ''}`} data-tip={tip}><small>{label}</small><span className="lfl-track"><i style={{ transform: `scaleX(${Math.max(0, Math.min(1, frac || 0)).toFixed(3)})` }} /></span><Flip v={word}>{word}</Flip></span>;
}

export function GenPod({ g, a, i }) {
  const r = genRisk(g); const t = tug(g); const st = STATUS[g.status] || ['•', g.status || '—', 'is-dim'];
  const wr = winRate(g); const e = genEdge(g); const tl = genTimeline(g);
  const lesson = Object.entries(g.lessonVector || {});
  const [, tick] = useState(0);
  useEffect(() => { const id = setInterval(() => tick(x => x + 1), 30000); return () => clearInterval(id); }, []);
  const ni = g.netImpact;
  return <li key={`${g.role}-${g.generation}`} className={`lfl-pod ${r.tone} ${r.frac >= 0.66 ? 'is-hot' : ''} ${e.tone === 'is-good' ? 'is-rising' : e.tone === 'is-bad' ? 'is-falling' : ''}`} style={{ '--i': i }} data-testid={`gen-${g.role}`} data-tip={g.why || undefined}>
    <header><span className="lfl-ico" aria-hidden>{a.icon || '🤖'}</span><b>{a.name || g.role}</b>
      <span className="lfl-gen" key={g.generation} data-testid={`lfl-gen-${g.role}`}>gen {g.generation}</span>
      <em className={`lfl-st ${st[2]}`} data-testid={`gen-status-${g.role}`}>{st[0]} {st[1]}</em></header>
    <div className="lfl-core">
      <WinRing r={wr} busy={g.decisions || 0} />
      <div className="lfl-edge" data-testid={`gen-edge-${g.role}`}>
        <small>VS OLDER GENS</small>
        <span className={`lfl-vs ${e.tone}`}>{e.delta == null ? <i>{e.word}</i> : <><Flip v={e.delta}>{e.delta > 0 ? '▲' : e.delta < 0 ? '▼' : '='} {Math.abs(e.delta)} pts</Flip><i>{e.now}% now · {e.past}% before</i></>}</span>
        <small className="lfl-age">{Number(g.bornAt) > 0 ? `born ${ago(g.bornAt)} ago · ` : ''}{g.decisions ?? 0} real exits</small>
      </div></div>
    <div className="lfl-meters">
      <Meter label="WIN RATE" frac={wr == null ? 0 : wr / 100} word={wr == null ? '—' : `${wr}%`} tone={wr == null ? '' : wr >= 55 ? 'is-good' : wr < 45 ? 'is-bad' : ''} tip="real exits it was credited for vs pinned on it" />
      <Meter label="LIFE" frac={1 - r.frac} word={r.word} tone={r.tone} tip={r.net == null ? 'no real exits judged yet' : `net ${r.net} (losses pinned − wins credited) · replaced at ${r.at}`} />
      <Meter label="TYPICAL" frac={ni == null ? 0 : Math.min(1, Math.abs(ni) / 20)} word={ni == null ? '—' : pc(ni)} tone={ni == null ? '' : ni >= 0 ? 'is-good' : 'is-bad'} tip="its typical real result" />
      <Meter label="W · L" frac={t ? t.share : 0} word={t ? `${t.w}·${t.l}` : '—'} tone={t ? (t.share >= 0.55 ? 'is-good' : t.share < 0.45 ? 'is-bad' : '') : ''} tip={t ? `${t.w} wins credited · ${t.l} losses pinned` : 'no wins or losses credited yet'} />
    </div>
    <ol className="lfl-line" aria-label="generations">{tl.map((p, j) => <li key={`${p.gen}-${j}`} className={`${p.live ? 'is-live' : 'is-past'} ${p.r == null ? '' : p.r >= 55 ? 'is-good' : p.r < 45 ? 'is-bad' : ''}`} style={{ '--j': j, '--sz': `${Math.min(1.6, 0.7 + p.n / 20).toFixed(2)}` }}
      data-tip={`gen ${p.gen}${p.live ? ' (now)' : ''} · ${p.r == null ? 'no record' : `${p.r}% won of ${p.n}`}${p.why ? ` · ${p.why}` : ''}`}><i /><small>{p.live ? '●' : '☠'} gen {p.gen}{!p.live && p.status ? ` ${p.status}` : ''}</small></li>)}</ol>
    <div className="lfl-chips">{lesson.length ? lesson.slice(0, 3).map(([k, v]) => <i key={k} className="lfl-chip is-lesson">🎓 {k} {v}</i>) : <i className="lfl-chip">🎓 defaults</i>}</div>
  </li>;
}

export function GenPods({ gens, agents }) {
  const meta = useMemo(() => Object.fromEntries((agents || []).map(a => [a.key, a])), [agents]);
  const board = useMemo(() => genBoard(gens), [gens]);
  if (!(gens || []).length) return <div className="lfl-box" data-testid="agd-gens"><h4>🧬 GENERATIONS</h4><small className="m-dim">the lifecycle book arrives with the first office pass</small></div>;
  const hot = gens.filter(g => genRisk(g).frac >= 0.66).length;
  const nm = k => (meta[k] || {}).name || k;
  return <div className="lfl-box m-card" data-testid="agd-gens"><h4>🧬 GENERATIONS <small>one lifecycle for all ten roles · judged on real exits only{hot ? ` · ⚠ ${hot} near replacement` : ''}</small></h4>
    <div className="lfl-board" data-testid="gen-board">
      {board.best ? <span className="lfl-crown is-good"><small>👑 BEST NOW</small><b>{nm(board.best.role)}</b><Flip v={board.best.r}>{board.best.r}% won</Flip></span> : <span className="lfl-crown"><small>👑 BEST NOW</small><b>—</b></span>}
      {board.improved ? <span className="lfl-crown is-rise"><small>📈 MOST IMPROVED</small><b>{nm(board.improved.role)}</b><Flip v={board.improved.e.delta}>+{board.improved.e.delta} pts on old gens</Flip></span> : null}
    </div>
    <ul className="lfl-pods">{gens.map((g, i) => <GenPod key={`${g.role}-${g.generation}`} g={g} a={meta[g.role] || {}} i={i} />)}</ul></div>;
}

export function RugCard({ r, i }) {
  const read = readAs(r.text); const missed = (r.missed || []).slice(0, 4);
  return <li className={`lfl-rug ${r.go ? 'is-go' : ''}`} style={{ '--i': i }} data-testid="lfl-rug">
    <header><b>${r.sym || '?'}</b>{r.go ? <em className="lfl-chip is-bad">after a GO</em> : null}<small>{ago(r.calledAt)} ago</small></header>
    <div className="lfl-drops"><span><small>5 MIN</small><span className="lfl-track is-drop"><i style={{ transform: `scaleX(${dropFrac(r.p5)})` }} /></span><em>{pc(r.p5)}</em></span>
      <span><small>60 MIN</small><span className="lfl-track is-drop"><i style={{ transform: `scaleX(${dropFrac(r.p60)})` }} /></span><em>{r.p60 == null ? 'pending' : pc(r.p60)}</em></span></div>
    {read.length ? <div className="lfl-chips"><small>READ AS</small>{read.map(w => <i key={w} className="lfl-chip">{w}</i>)}</div> : null}
    {missed.length ? <div className="lfl-chips"><small>MISSED</small>{missed.map(w => <i key={w} className="lfl-chip is-bad">{missedWord(w)}</i>)}</div> : null}
  </li>;
}

export function RugWall({ list, signs }) {
  const rows = useMemo(() => dedupeAutopsies(list), [list]); const [all, setAll] = useState(false);
  const show = all ? rows : rows.slice(0, 6);
  const go = rows.filter(r => r.go).length;
  return <div className="lfl-box m-card" data-testid="agd-autopsy"><h4>🔬 RUG AUTOPSY <small>{rows.length ? `${rows.length} rug${rows.length === 1 ? '' : 's'} on the desk${go ? ` · ${go} after a GO` : ''} · what it fell, what we read, what we missed` : 'no rug on the desk yet'}</small></h4>
    {rows.length ? <ul className="lfl-rugs">{show.map((r, i) => <RugCard key={`${r.sym}-${r.calledAt}`} r={r} i={i} />)}</ul> : null}
    {rows.length > 6 ? <button type="button" className="m-btn lfl-more" onClick={() => setAll(v => !v)} data-testid="lfl-rugs-more">{all ? 'Show fewer' : `Show all ${rows.length}`}</button> : null}
    {(signs || []).length > 0 && <div className="lfl-chips"><small>RUG SIGNS</small>{signs.map(x => <i key={x.key} className={`lfl-chip ${x.n >= 3 ? 'is-bad' : ''}`}>☠ {x.words} ×{x.n}</i>)}</div>}</div>;
}

export function CreedFold({ creed }) {
  const [open, setOpen] = useState(false);
  useEffect(() => { setOpen(false); }, [creed]);
  if (!(creed || []).length) return null;
  return <details className="lfl-box lfl-creed m-card" data-testid="agd-creed" open={open} onToggle={e => setOpen(e.currentTarget.open)}>
    <summary><h4>📜 THE CREED <small>{creed.length} lines engraved in their code · tap to read</small></h4></summary>
    <ol>{creed.map((c, i) => <li key={i} style={{ '--i': i }}>{c}</li>)}</ol></details>;
}
