import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { INKS, SHAPES, band, collectivePrint, geom, inkOf, part, pickTwo, printOf } from '../../lib/proofprint';
import { proofRows } from './ProofsFolder';
import { LiveCount } from './BoostFolder';
import { BoostCoin } from './DeskShell';
import '../../styles/boosts.css';

// 🧬 THE PROOFPRINT (owner 2026-11-04): shown in 3 places, always from real proofs. Big and faint behind its desktop, whole in its own folder, and in the Collective from proofs really sent. Only its owner sees what is inside.
const PER = 12;
const faintCount = (rings, grow = 6) => Math.max(grow, Math.min(18, rings * 2 + 4));
// The view always fits the print: a young print fills its frame, and it zooms out as it grows.
const fitBox = n => { const h = 24 + n * 10.3 + 26; const w = (h * 480) / 540; return `${(240 - w).toFixed(1)} ${(255 - h).toFixed(1)} ${(w * 2).toFixed(1)} ${(h * 2).toFixed(1)}`; };
const Ridges = React.memo(function Ridges({ rings, shape, ink, selected, run, onPick, grow = 6 }) {
  const faint = useMemo(() => { const n = faintCount(rings.length, grow); return Array.from({ length: n }, (_, j) => part(shape, j, 0, Math.PI * 2, 60)); }, [shape, rings.length, grow]);
  const lines = useMemo(() => rings.map((r, i) => { const n = r.checkpoints.length; return r.checkpoints.map((c, k) => ({ d: part(shape, i * 2 + 2, (k / PER) * Math.PI * 2, ((k + 1) / PER) * Math.PI * 2), c, k, i, n })); }), [rings, shape]);
  return <><g className="pp-faint">{faint.map((d, j) => <path key={j} d={d} />)}</g>
    {lines.flat().map(({ d, c, k, i }) => { const on = selected === i; const hot = on && run === k; const col = inkOf(c.score, ink);
      return <g key={`${i}-${k}`}><path className="pp-ridge" d={d} stroke={col} strokeWidth={hot ? 5.8 : on ? 4.2 : 3.1} opacity={selected >= 0 && !on ? 0.42 : 1} style={hot ? { filter: `drop-shadow(0 0 7px ${col})` } : undefined} />{onPick ? <path className="pp-hit" d={d} onClick={() => onPick(i, k)} /> : null}</g>; })}</>;
});
function Spark({ cps, run, ink, onPick }) {
  const n = cps.length; const X = j => 8 + (j / Math.max(1, n - 1)) * 180; const Y = v => 73 - (v / 100) * 61;
  return <svg className="pp-spark" viewBox="0 0 196 86" role="img" aria-label="Its results on this ridge">{[25, 50, 75, 100].map(v => <line key={v} x1="8" x2="188" y1={Y(v)} y2={Y(v)} />)}{cps.slice(1).map((c, j) => <line key={c.id} className="is-seg" x1={X(j)} y1={Y(cps[j].score)} x2={X(j + 1)} y2={Y(c.score)} stroke={inkOf(c.score, ink)} />)}{cps.map((c, j) => <circle key={c.id} cx={X(j)} cy={Y(c.score)} r={j === run ? 4.7 : 2.6} fill={inkOf(c.score, ink)} onClick={() => onPick(j)} />)}</svg>;
}
export function PrintStage({ print, shape, ink, label, height = 460, empty, onOpen, testid = 'pp-stage' }) {
  const [sel, setSel] = useState(-1); const [run, setRun] = useState(0); const cam = useRef(null); const stage = useRef(null); const v = useRef({ z: 1, x: 0, y: 0, gz: 1, gx: 0, gy: 0, raf: 0, drag: null, moved: false }); const rings = print.rings;
  const paint = () => { const s = v.current; if (cam.current) cam.current.setAttribute('transform', `translate(${s.x} ${s.y}) translate(240 270) scale(${s.z}) translate(-240 -270)`); };
  const go = () => { const s = v.current; cancelAnimationFrame(s.raf); const tick = () => { s.z += (s.gz - s.z) * 0.17; s.x += (s.gx - s.x) * 0.17; s.y += (s.gy - s.y) * 0.17; paint(); if (Math.abs(s.gz - s.z) + Math.abs(s.gx - s.x) + Math.abs(s.gy - s.y) > 0.035) s.raf = requestAnimationFrame(tick); else { s.z = s.gz; s.x = s.gx; s.y = s.gy; paint(); } }; s.raf = requestAnimationFrame(tick); };
  useEffect(() => () => cancelAnimationFrame(v.current.raf), []);
  const pick = (i, k) => { if (v.current.moved) return; setSel(i); setRun(k); const [x, y] = geom(shape, i * 2 + 2, ((k + 0.5) / PER) * Math.PI * 2); const s = v.current; s.gz = Math.max(s.z, 1.42); s.gx = (240 - x) * s.gz * 0.6; s.gy = (270 - y) * s.gz * 0.6; go(); };
  const home = () => { setSel(-1); Object.assign(v.current, { gz: 1, gx: 0, gy: 0 }); go(); };
  const zoom = f => { const s = v.current; s.gz = Math.max(0.7, Math.min(3, s.z * f)); s.gx = s.x; s.gy = s.y; go(); };
  useEffect(() => { const el = stage.current; if (!el) return undefined; const wheel = e => { e.preventDefault(); zoom(e.deltaY < 0 ? 1.12 : 0.89); }; el.addEventListener('wheel', wheel, { passive: false }); return () => el.removeEventListener('wheel', wheel); }, []);   // eslint-disable-line react-hooks/exhaustive-deps
  const down = e => { const s = v.current; s.drag = { x: e.clientX, y: e.clientY, ox: s.x, oy: s.y }; s.moved = false; };
  const move = e => { const s = v.current; if (!s.drag) return; const dx = e.clientX - s.drag.x; const dy = e.clientY - s.drag.y; if (Math.abs(dx) + Math.abs(dy) > 5) s.moved = true; if (s.moved) { cancelAnimationFrame(s.raf); const r = stage.current.getBoundingClientRect(); s.x = s.drag.ox + (dx / r.width) * 480; s.y = s.drag.oy + (dy / r.height) * 540; s.gx = s.x; s.gy = s.y; paint(); } };
  const up = () => { const s = v.current; s.drag = null; setTimeout(() => { s.moved = false; }, 0); };
  const r = rings[sel]; const c = r?.checkpoints[run]; const cps = r?.checkpoints || []; const peak = cps.length ? Math.max(...cps.map(x => x.score)) : 0; const delta = c ? c.score - (run ? cps[run - 1].score : c.score) : 0; const shots = pickTwo(c?.shots);
  return <section className="pp-stage" ref={stage} style={{ '--pp-h': `${height}px` }} data-testid={testid}>
    <div className="pp-top"><b>{label}</b><small>{print.total ? `${rings.length} ridge${rings.length > 1 ? 's' : ''} · ${print.total} proofs` : 'Waiting on its first result'}</small></div>
    <div className="pp-ctl"><button type="button" className="m-btn" onClick={() => zoom(1.25)} aria-label="Zoom in" data-tip="Zoom in">+</button><button type="button" className="m-btn" onClick={() => zoom(0.8)} aria-label="Zoom out" data-tip="Zoom out">−</button><button type="button" className="m-btn" onClick={home} aria-label="Reset the view" data-tip="Back to the whole print">⌂</button></div>
    <svg viewBox={fitBox(faintCount(rings.length))} role="img" aria-label={`${label}: ${print.total} proofs`} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onPointerLeave={up}><g ref={cam}><Ridges rings={rings} shape={shape} ink={ink} selected={sel} run={run} onPick={pick} /></g></svg>
    {!print.total ? <p className="pp-empty">{empty}</p> : <p className="pp-tip">Tap a ridge · drag to move · scroll to zoom</p>}
    {c ? <article className="pp-card" data-testid="pp-card"><header><span><small>{r.code} · {c.at ? new Date(c.at * 1000).toLocaleDateString() : `#${run + 1}`}</small><strong>{c.name}</strong>{c.sub ? <em>{c.sub}</em> : null}</span><button type="button" className="m-btn" onClick={home} aria-label="Close" data-tip="Close">✕</button></header>
      <div className="pp-vit">{[['RESULT', c.shown ?? c.score], ['PEAK', peak], ['CHANGE', `${delta > 0 ? '+' : ''}${delta}`]].map(([k, val]) => <span key={k}><small>{k}</small><b className="m-num">{val}</b></span>)}</div>
      <Spark cps={cps} run={run} ink={ink} onPick={setRun} /><p className="pp-band" style={{ color: inkOf(c.score, ink) }}>{band(c.score)} · {c.score}/100</p>
      {shots.length ? <div className="pp-shots">{shots.map(s => <button key={s.file} type="button" onClick={() => onOpen?.(s)} data-tip={s.site}><img src={s.src} alt={s.site} loading="lazy" /></button>)}</div> : null}</article> : null}
  </section>;
}
// Behind the icons: big, faint and cut off by the desk's edge. Only the ridges take a click, so the empty desk still behaves like a desk.
export function DeskPrint({ d, style, level = 0, onOpen }) {
  const print = useMemo(() => printOf(proofRows(d)), [d]);
  return <button type="button" className="pp-desk" style={{ '--pp-a': 0.2 + Math.min(1, level / 100) * 0.34 }} onClick={onOpen} data-tip="Its Proofprint: every proof it filed. Open the folder" data-testid="pp-desk" tabIndex={0} aria-label="Open its Proofprint"><svg viewBox={fitBox(faintCount(print.rings.length, 14))} aria-hidden="true"><Ridges rings={print.rings} shape={style?.shape || 'whorl'} ink={style?.ink || 'proof'} selected={-1} run={0} grow={14} /></svg></button>;
}
export function MiniPrint({ print, shape = 'whorl', ink = 'blue', tip }) {
  return <span className="pp-mini" data-tip={tip} data-testid="pp-mini"><svg viewBox={fitBox(faintCount(print.rings.length, 8))} role="img" aria-label={`${print.total} proofs sent`}><Ridges rings={print.rings} shape={shape} ink={ink} selected={-1} run={0} grow={8} /></svg></span>;
}
export function CollectivePrint({ feed }) {
  const print = useMemo(() => collectivePrint(feed), [feed]);
  return <PrintStage print={print} shape="double" ink="blue" label="THE COLLECTIVE'S PRINT" height={340} empty="It starts with the first proof sent, a ridge for each agent." testid="pp-collective" />;
}
export function ProofprintFolder({ cat, d, work, pool }) {
  const rows = useMemo(() => proofRows(d).map(r => ({ ...r, shots: (r.shots || []).map(s => ({ ...s, src: String(s.src || '').replace('{cat}', cat.id) })) })), [d, cat.id]); const print = useMemo(() => printOf(rows), [rows]);
  const [style, setStyle] = useState({ shape: 'whorl', ink: 'proof' }); const [err, setErr] = useState(''); const [big, setBig] = useState(null); const seeded = useRef(false);
  useEffect(() => { if (!seeded.current && pool?.printStyle) { seeded.current = true; setStyle(x => ({ ...x, ...pool.printStyle })); } }, [pool]);
  const save = async next => { setStyle(next); setErr(''); try { await work(cat.id, { op: 'print_style', text: next.shape, job: next.ink }); } catch (e) { setErr(e.message || 'Not saved'); } };
  const list = rows.filter(r => r.value != null).slice(0, 30); const level = pool?.printLevel ?? 0;
  return <div className="pp" data-testid="pp-folder">
    <header className="pp-head"><BoostCoin /><div><small>EARNED FROM PROOFS SENT</small>{pool ? <LiveCount pool={pool.pool} readAt={pool.readAt} testid="pp-count" /> : <b className="bst-num">…</b>}</div>
      <span className="pp-level" data-tip="Grows with every proof it files, and what it learns from them. Only you see what is inside."><small>PRINT LEVEL</small><b className="m-num">{level}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, level / 100)})` }} /></i></span></header>
    <div className="pp-style"><span className="m-seg" role="group" aria-label="Its shape">{SHAPES.map(([k, l]) => <button key={k} type="button" className={style.shape === k ? 'active' : ''} aria-pressed={style.shape === k} onClick={() => save({ ...style, shape: k })} data-tip="This shape also shows big behind its desktop" data-testid={`pp-shape-${k}`}>{l}</button>)}</span>
      <span className="m-seg" role="group" aria-label="Its ink">{INKS.map(([k, l]) => <button key={k} type="button" className={style.ink === k ? 'active' : ''} aria-pressed={style.ink === k} onClick={() => save({ ...style, ink: k })} data-tip={k === 'proof' ? 'Green strong, gold medium, red weak' : 'A look only: the results stay in the card'} data-testid={`pp-ink-${k}`}>{l}</button>)}</span></div>
    {err ? <p className="lct-err" role="alert">⚠ {err}</p> : null}
    <PrintStage print={print} shape={style.shape} ink={style.ink} label="LIVING PROOFPRINT" empty="Its first finished proof draws its first ridge." onOpen={setBig} />
    <section className="pp-list"><h4><Ic3 e="🧾" /> EVERY PROOF<small>Best 2 snapshots each. Saved sealed on FEELESS's own disk, free.</small></h4>
      {list.length ? <ol>{list.map(r => { const two = pickTwo(r.shots); return <li key={r.id}><span><b>{r.name}</b><small>{r.sub}</small></span><em className="m-num">{r.shown}</em>{two.length ? <span className="pp-shots">{two.map(s => <button key={s.file} type="button" onClick={() => setBig(s)} data-tip={s.site}><img src={s.src} alt={s.site} loading="lazy" /></button>)}</span> : null}{r.decisions?.[0] ? <p>{r.decisions[0][0]}: {String(r.decisions[0][1]).slice(0, 160)}</p> : null}</li>; })}</ol> : <p className="fch-nil">No finished proofs yet.</p>}</section>
    {big ? <div className="ast-shade" role="dialog" aria-modal="true" aria-label={big.site} onClick={() => setBig(null)}><img src={big.src} alt={big.site} /></div> : null}
  </div>;
}
