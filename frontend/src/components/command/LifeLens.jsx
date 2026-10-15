import React, { useEffect, useMemo, useState } from 'react';
import { genRisk, tug, dedupeAutopsies, readAs, missedWord, dropFrac } from '../../lib/lifeLens';
import '../../styles/lifeLens.css';

// 🧬 THE LIFE LENS (owner, 2026-10-15: "a cool way to show stuff like this in live realtime meta degen animation"): the generations, the rug
// autopsy and the creed were a wall of unstyled text. Now: one pod per role (its gen, life left before replacement, wins vs losses, its
// lesson, the generations it replaced as tombstones), a wall of rug cards (how far it fell, what we read, what we missed) and the creed folded.
// A new generation re-keys its pod so the rebirth plays; a pod near replacement pulses. transform / opacity only.

const pc = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const ago = t => { const s = Math.max(0, Math.round(Date.now() / 1000 - Number(t || 0))); return s < 60 ? `${s}s` : s < 3600 ? `${Math.round(s / 60)}m` : s < 86400 ? `${Math.round(s / 3600)}h` : `${Math.round(s / 86400)}d`; };
const STATUS = { ACTIVE: ['🟢', 'ACTIVE', 'is-good'], PROBATION: ['⚠', 'PROBATION', 'is-warn'], SHADOW: ['👻', 'SHADOW', 'is-dim'], RETIRED: ['☠', 'RETIRED', 'is-dim'], BENCHED: ['⏸', 'BENCHED', 'is-dim'] };

export function GenPod({ g, a, i }) {
  const r = genRisk(g); const t = tug(g); const st = STATUS[g.status] || ['•', g.status || '—', 'is-dim'];
  const lesson = Object.entries(g.lessonVector || {}); const past = (g.lineage || []).slice(0, 6);
  return <li key={`${g.role}-${g.generation}`} className={`lfl-pod ${r.tone} ${r.frac >= 0.66 ? 'is-hot' : ''}`} style={{ '--i': i }} data-testid={`gen-${g.role}`} data-tip={g.why || undefined}>
    <header><span className="lfl-ico" aria-hidden>{a.icon || '🤖'}</span><b>{a.name || g.role}</b>
      <span className="lfl-gen" key={g.generation} data-testid={`lfl-gen-${g.role}`}>gen {g.generation}</span>
      <em className={`lfl-st ${st[2]}`} data-testid={`gen-status-${g.role}`}>{st[0]} {st[1]}</em></header>
    <div className="lfl-life" data-tip={r.net == null ? 'no real exits judged yet' : `net ${r.net} (losses pinned − wins credited) · replaced at ${r.at}`}>
      <small>LIFE</small><span className="lfl-track"><i style={{ transform: `scaleX(${1 - r.frac})` }} /></span><em>{r.word}</em></div>
    <div className="lfl-tug" data-tip={t ? `${t.w} wins credited · ${t.l} losses pinned` : 'no wins or losses credited yet'}>
      <span className="lfl-split" aria-hidden>{t ? <><i className="is-w" style={{ flexGrow: t.share }} /><i className="is-l" style={{ flexGrow: 1 - t.share }} /></> : null}</span>
      <small>{t ? `${t.w} W · ${t.l} L` : 'no credit yet'} · {g.decisions ?? 0} real exits{g.netImpact != null ? ` · typical ${pc(g.netImpact)}` : ''}</small></div>
    <div className="lfl-chips">{lesson.length ? lesson.slice(0, 3).map(([k, v]) => <i key={k} className="lfl-chip is-lesson">🎓 {k} {v}</i>) : <i className="lfl-chip">🎓 defaults</i>}</div>
    {past.length ? <div className="lfl-tombs" aria-label="replaced generations">{past.map((p, j) => <i key={`${p.gen}-${j}`} className="lfl-tomb" style={{ '--j': j }} data-tip={`gen ${p.gen} ${p.status || 'replaced'}${p.changed ? ` — next gen: ${p.changed}` : ''}${p.why ? ` · ${p.why}` : ''}`}>☠ gen {p.gen} {p.status || ''}</i>)}</div> : null}
  </li>;
}

export function GenPods({ gens, agents }) {
  const meta = useMemo(() => Object.fromEntries((agents || []).map(a => [a.key, a])), [agents]);
  if (!(gens || []).length) return <div className="lfl-box" data-testid="agd-gens"><h4>🧬 GENERATIONS</h4><small className="m-dim">the lifecycle book arrives with the first office pass</small></div>;
  const hot = gens.filter(g => genRisk(g).frac >= 0.66).length;
  return <div className="lfl-box m-card" data-testid="agd-gens"><h4>🧬 GENERATIONS <small>one lifecycle for all ten roles · judged on real exits only{hot ? ` · ⚠ ${hot} near replacement` : ''}</small></h4>
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
