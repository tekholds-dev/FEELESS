import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Ic3 } from '../../lib/icon3d';
import { band, collectivePrint, faintCount, fitBox, identityOf, inkOf, pickTwo, printOf, ridge, ringPoint, segment, spans, statsOf } from '../../lib/proofprint';
import { proofRows } from './ProofsFolder';
import { LiveCount } from './BoostFolder';
import { BoostCoin } from './DeskShell';
import { money } from './SplitFlow';
import '../../styles/boosts.css';

// 🧬 THE PROOFPRINT (owner 2026-11-04): one print per agent, its own for life. Shown in 3 places, always from real proofs: big and faint behind its desktop, whole in its own folder, and in the Collective from proofs really sent. Only its owner sees what is inside.
const Ridges = React.memo(function Ridges({ rings, id, selected, run, onPick, grow = 6 }) {
  const faint = useMemo(() => Array.from({ length: faintCount(rings.length, grow) }, (_, j) => ridge(id, j)), [id, rings.length, grow]);
  const lines = useMemo(() => rings.flatMap((r, i) => { const sp = spans(r.checkpoints); return r.checkpoints.map((c, k) => ({ d: segment(id, i, sp[k][0], sp[k][1]), c, k, i, code: r.code })); }), [rings, id]);
  return <><g className="pp-faint" stroke={`hsl(${id.hue} 30% 62%)`}>{faint.map((d, j) => <path key={j} d={d} />)}</g>
    {lines.map(({ d, c, k, i, code }) => { const on = selected === i; const hot = on && run === k; const col = inkOf(c.score);
      return <g key={`${i}-${k}`}><path className="pp-ridge" d={d} stroke={col} strokeWidth={(hot ? 6 : on ? 4.2 : 3.1) + Math.abs(c.score - 50) / 50} opacity={selected >= 0 && !on ? 0.36 : 1} style={hot ? { filter: `drop-shadow(0 0 7px ${col})` } : undefined} />{onPick ? <path className="pp-hit" d={d} data-tip={`${code} · ${c.name}${c.shown != null ? ` · ${c.shown}` : ''}`} onClick={e => { e.stopPropagation(); onPick(i, k); }} /> : null}</g>; })}</>;
});
function Spark({ cps, run, id, onPick }) {
  const n = cps.length; const X = j => 8 + (j / Math.max(1, n - 1)) * 180; const Y = v => 73 - (v / 100) * 61;
  return <svg className="pp-spark" viewBox="0 0 196 86" role="img" aria-label="Its results on this ridge">{[25, 50, 75, 100].map(v => <line key={v} x1="8" x2="188" y1={Y(v)} y2={Y(v)} />)}{cps.slice(1).map((c, j) => <line key={c.id} className="is-seg" x1={X(j)} y1={Y(cps[j].score)} x2={X(j + 1)} y2={Y(c.score)} stroke={inkOf(c.score)} />)}{cps.map((c, j) => <circle key={c.id} cx={X(j)} cy={Y(c.score)} r={j === run ? 4.7 : 2.6} fill={inkOf(c.score)} onClick={e => { e.stopPropagation(); onPick(j); }} />)}</svg>;
}
// The print + its wired card: the card hangs off the exact part of the line, on a live wire, and follows it as the print moves. Click the same part, or anywhere else, and it lets go.
function useWiredPrint({ print, id, zoomTo = 1.42 }) {
  const [sel, setSel] = useState(-1); const [run, setRun] = useState(0); const box = useRef(null); const cam = useRef(null); const card = useRef(null); const wire = useRef(null); const dot = useRef(null); const halo = useRef(null); const v = useRef({ z: 1, x: 0, y: 0, gz: 1, gx: 0, gy: 0, raf: 0, drag: null, moved: false, sel: -1, run: 0 });
  const connect = () => { const s = v.current; if (s.sel < 0 || !box.current || !cam.current || !card.current) return; const m = cam.current.getScreenCTM?.(); if (!m) return; const cps = print.rings[s.sel]?.checkpoints; if (!cps) return; const [px, py] = ringPoint(id, s.sel, cps, s.run); const r = box.current.getBoundingClientRect(); const x = px * m.a + py * m.c + m.e - r.left; const y = px * m.b + py * m.d + m.f - r.top; const w = card.current.offsetWidth; const h = card.current.offsetHeight; let left = x + 34; if (left + w > r.width - 10) left = x - w - 34; left = Math.max(10, Math.min(r.width - w - 10, left)); const top = Math.max(10, Math.min(r.height - h - 10, y - h * 0.4)); card.current.style.transform = `translate(${left}px, ${top}px)`; const tx = left > x ? left : left + w; const ty = top + Math.min(h * 0.32, 70); const d = `M${x.toFixed(1)} ${y.toFixed(1)} Q${((x + tx) / 2).toFixed(1)} ${(Math.min(y, ty) - 26).toFixed(1)} ${tx.toFixed(1)} ${ty.toFixed(1)}`; wire.current?.setAttribute('d', d); [dot.current, halo.current].forEach(c => { c?.setAttribute('cx', x); c?.setAttribute('cy', y); }); };
  const paint = () => { const s = v.current; cam.current?.setAttribute('transform', `translate(${s.x} ${s.y}) translate(${240 + id.cx} ${255 + id.cy}) scale(${s.z}) translate(${-240 - id.cx} ${-255 - id.cy})`); connect(); };
  const go = () => { const s = v.current; cancelAnimationFrame(s.raf); const tick = () => { s.z += (s.gz - s.z) * 0.17; s.x += (s.gx - s.x) * 0.17; s.y += (s.gy - s.y) * 0.17; paint(); if (Math.abs(s.gz - s.z) + Math.abs(s.gx - s.x) + Math.abs(s.gy - s.y) > 0.035) s.raf = requestAnimationFrame(tick); else { s.z = s.gz; s.x = s.gx; s.y = s.gy; paint(); } }; s.raf = requestAnimationFrame(tick); };
  useEffect(() => () => cancelAnimationFrame(v.current.raf), []);
  useEffect(() => { connect(); }, [sel, run]);   // eslint-disable-line react-hooks/exhaustive-deps
  const home = () => { const s = v.current; s.sel = -1; setSel(-1); s.gz = 1; s.gx = 0; s.gy = 0; go(); };
  const pick = (i, k) => { const s = v.current; if (s.moved) return; if (s.sel === i && s.run === k) { home(); return; } s.sel = i; s.run = k; setSel(i); setRun(k); const [x, y] = ringPoint(id, i, print.rings[i].checkpoints, k); s.gz = zoomTo; s.gx = (240 + id.cx - x) * (zoomTo - 1) * 0.9; s.gy = (255 + id.cy - y) * (zoomTo - 1) * 0.9; go(); };
  const setRunOnly = k => { v.current.run = k; setRun(k); };
  const zoom = f => { const s = v.current; s.gz = Math.max(0.7, Math.min(3, s.z * f)); s.gx = s.x; s.gy = s.y; go(); };
  const rings = print.rings; const r = rings[sel]; const c = r?.checkpoints[run];
  return { sel, run, box, cam, card, wire, dot, halo, v, paint, home, pick, setRunOnly, zoom, r, c };
}
function WiredCard({ w, id, onOpen, foot }) {
  const { r, c, run } = w; const cps = r?.checkpoints || []; if (!c) return null; const peak = Math.max(...cps.map(x => x.score)); const delta = c.score - (run ? cps[run - 1].score : c.score); const shots = pickTwo(c.shots);
  return <><svg className="pp-wire" aria-hidden="true"><path ref={w.wire} stroke={inkOf(c.score)} /><circle ref={w.halo} className="is-halo" r="13" stroke={inkOf(c.score)} /><circle ref={w.dot} r="5.5" fill={inkOf(c.score)} /></svg>
    <article ref={w.card} className="pp-card" data-testid="pp-card" onClick={e => e.stopPropagation()} onPointerDown={e => e.stopPropagation()}><header><span><small>{r.code} · {c.at ? new Date(c.at * 1000).toLocaleDateString() : `#${run + 1}`}</small><strong>{c.name}</strong>{c.sub ? <em>{c.sub}</em> : null}</span><button type="button" className="m-btn" onClick={w.home} aria-label="Close" data-tip="Let go">✕</button></header>
      <div className="pp-vit">{[['RESULT', c.shown ?? c.score], ['RIDGE BEST', peak], ['CHANGE', `${delta > 0 ? '+' : ''}${delta}`]].map(([k, val]) => <span key={k}><small>{k}</small><b className="m-num">{val}</b></span>)}</div>
      <Spark cps={cps} run={run} id={id} onPick={w.setRunOnly} /><p className="pp-band" style={{ color: inkOf(c.score) }}>{band(c.score)} · {c.score}/100</p>
      {c.decisions?.[0] ? <p className="pp-why">{c.decisions[0][0]}: {String(c.decisions[0][1]).slice(0, 110)}</p> : null}
      {shots.length ? <div className="pp-shots">{shots.map(s => <button key={s.file} type="button" onClick={() => onOpen?.(s)} data-tip={s.site}><img src={s.src} alt={s.site} loading="lazy" /></button>)}</div> : null}{foot}</article></>;
}
export function PrintStage({ print, id, label, height = 460, empty, onOpen, testid = 'pp-stage' }) {
  const w = useWiredPrint({ print, id }); const rings = print.rings; const zoomed = useRef(false);
  const down = e => { const s = w.v.current; s.drag = { x: e.clientX, y: e.clientY, ox: s.x, oy: s.y }; s.moved = false; };
  const move = e => { const s = w.v.current; if (!s.drag || e.pointerType === 'touch') return; const dx = e.clientX - s.drag.x; const dy = e.clientY - s.drag.y; if (Math.abs(dx) + Math.abs(dy) > 5) s.moved = true; if (s.moved) { const r = w.box.current.getBoundingClientRect(); cancelAnimationFrame(s.raf); s.x = s.drag.ox + (dx / r.width) * 480; s.y = s.drag.oy + (dy / r.height) * 540; s.gx = s.x; s.gy = s.y; w.paint(); } };
  const up = () => { const s = w.v.current; s.drag = null; setTimeout(() => { s.moved = false; }, 0); };
  useEffect(() => { zoomed.current = w.sel >= 0; }, [w.sel]);
  return <section className="pp-stage" ref={w.box} style={{ '--pp-h': `${height}px` }} onClick={() => { if (!w.v.current.moved) w.home(); }} data-testid={testid}>
    <div className="pp-top"><b>{label}</b><small>{print.total ? `${rings.length} ridge${rings.length > 1 ? 's' : ''} · ${print.total} proofs` : 'Waiting on its first result'}</small></div>
    <div className="pp-ctl" onClick={e => e.stopPropagation()}><button type="button" className="m-btn" onClick={() => w.zoom(1.25)} aria-label="Zoom in" data-tip="Zoom in">+</button><button type="button" className="m-btn" onClick={() => w.zoom(0.8)} aria-label="Zoom out" data-tip="Zoom out">−</button><button type="button" className="m-btn" onClick={w.home} aria-label="Reset the view" data-tip="Back to the whole print">⌂</button></div>
    <svg viewBox={fitBox(faintCount(rings.length), id)} role="img" aria-label={`${label}: ${print.total} proofs`} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up} onPointerLeave={up}><g ref={w.cam}><Ridges rings={rings} id={id} selected={w.sel} run={w.run} onPick={w.pick} /></g></svg>
    {!print.total ? <p className="pp-empty">{empty}</p> : w.sel < 0 ? <p className="pp-tip">Tap a line for its proof. Tap anywhere to let go.</p> : null}
    <WiredCard w={w} id={id} onOpen={onOpen} /></section>;
}
// Behind the icons: big, faint and cut off by the desk's edge. A part of the line pops its own wired card right there; the empty desk still behaves like a desk.
export function DeskPrint({ d, seed, level = 0, onOpen }) {
  const id = useMemo(() => identityOf(seed), [seed]); const print = useMemo(() => printOf(proofRows(d)), [d]); const w = useWiredPrint({ print, id, zoomTo: 1 }); const open = w.sel >= 0;
  useEffect(() => { if (!open) return undefined; const off = () => w.home(); document.addEventListener('pointerdown', off); return () => document.removeEventListener('pointerdown', off); }, [open]);   // eslint-disable-line react-hooks/exhaustive-deps
  return <div className={`pp-desk${open ? ' is-open' : ''}`} ref={w.box} style={{ '--pp-a': 0.26 + Math.min(1, level / 100) * 0.34 }} data-testid="pp-desk"><svg className="pp-desk-art" viewBox={fitBox(faintCount(print.rings.length, 14), id)} role="img" aria-label="Its Proofprint"><g ref={w.cam}><Ridges rings={print.rings} id={id} selected={w.sel} run={w.run} onPick={(i, k) => w.pick(i, k)} grow={14} /></g></svg>
    <WiredCard w={w} id={id} foot={<button type="button" className="m-btn pp-open" onClick={onOpen} data-testid="pp-desk-open">Open its Proofprint</button>} /></div>;
}
export function MiniPrint({ print, seed, tip }) {
  const id = useMemo(() => identityOf(seed), [seed]);
  return <span className="pp-mini" data-tip={tip} data-testid="pp-mini"><svg viewBox={fitBox(faintCount(print.rings.length, 8), id)} role="img" aria-label={`${print.total} proofs sent`}><Ridges rings={print.rings} id={id} selected={-1} run={0} grow={8} /></svg></span>;
}
export function CollectivePrint({ feed }) {
  const print = useMemo(() => collectivePrint(feed), [feed]); const id = useMemo(() => identityOf('the-collective'), []);
  return <PrintStage print={print} id={id} label="THE COLLECTIVE'S PRINT" height={340} empty="It starts with the first proof sent, a ridge for each agent." testid="pp-collective" />;
}
const LENS = [['all', 'All'], ['pow', 'PoW'], ['pop', 'PoP'], ['pob', 'PoB'], ['poc', 'PoC']];
function Growth({ hist }) {
  const pts = (hist || []).filter(h => h.sent != null); if (pts.length < 2) return <p className="fch-nil">Its growth chart starts after its second day with a proof sent.</p>;
  const top = Math.max(1e-9, ...pts.flatMap(h => [h.sent, h.owed + h.locked])); const X = i => (i / (pts.length - 1)) * 600; const Y = v => 150 - (v / top) * 140; const line = k => pts.map((h, i) => `${i ? 'L' : 'M'}${X(i).toFixed(1)} ${Y(k(h)).toFixed(1)}`).join(' ');
  return <div className="pp-growth"><svg viewBox="0 0 600 160" preserveAspectRatio="none" role="img" aria-label="What it sent against what it has earned and has locked"><path d={line(h => h.sent)} className="is-sent" /><path d={line(h => h.owed + h.locked)} className="is-worth" /><path d={line(h => h.owed)} className="is-owed" /></svg><ul className="ge-legend"><li><i className="is-sent" />Sent</li><li><i className="is-worth" />Earned + still locked</li><li><i className="is-owed" />Earned</li></ul></div>;
}
export function ProofprintFolder({ cat, d, pool }) {
  const rows = useMemo(() => proofRows(d).map(r => ({ ...r, shots: (r.shots || []).map(s => ({ ...s, src: String(s.src || '').replace('{cat}', cat.id) })) })), [d, cat.id]); const id = useMemo(() => identityOf(pool?.printSeed || cat.id), [pool?.printSeed, cat.id]);
  const [tab, setTab] = useState('print'); const [lens, setLens] = useState('all'); const [big, setBig] = useState(null); const [at, setAt] = useState(null); const [playing, setPlaying] = useState(false);
  const sorted = useMemo(() => rows.filter(r => r.value != null && (lens === 'all' || r.kind === lens)).sort((a, b) => (a.at || 0) - (b.at || 0)), [rows, lens]); const n = at == null ? sorted.length : Math.min(at, sorted.length); const shown = useMemo(() => sorted.slice(0, n), [sorted, n]); const print = useMemo(() => printOf(shown), [shown]); const st = useMemo(() => statsOf(shown), [shown]);
  useEffect(() => { setAt(null); setPlaying(false); }, [lens]);
  useEffect(() => { if (!playing) return undefined; const t = setInterval(() => setAt(x => { const next = (x ?? 0) + 1; if (next >= sorted.length) { setPlaying(false); return null; } return next; }), 240); return () => clearInterval(t); }, [playing, sorted.length]);
  const level = pool?.printLevel ?? 0; const p = pool?.pool || {}; const list = [...sorted].reverse().slice(0, 40); const most = Math.max(1, st.strong, st.medium, st.weak);
  return <div className="pp" data-testid="pp-folder">
    <header className="pp-head"><span className="pp-id" style={{ '--h': id.hue, '--h2': id.hue2 }} data-tip="This print is its identity: picked and sealed by the server from a keyed seed, for this agent only. Nobody can choose or copy one." data-testid="pp-id"><b className="m-num">{id.code}</b><small>{id.patternName} · Ink {id.inkN}</small></span>
      <div className="pp-head-c"><BoostCoin earning={!!p.ratePerSecUsd} /><div><small>EARNED FROM PROOFS SENT</small>{pool ? <LiveCount pool={p} readAt={pool.readAt} testid="pp-count" /> : <b className="bst-num">…</b>}</div></div>
      <span className="pp-level" data-tip="Grows with every proof it files and what it learns from them. Only you see what is inside."><small>PRINT LEVEL</small><b className="m-num">{level}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, level / 100)})` }} /></i></span></header>
    <div className="pp-tabs m-seg" role="tablist" aria-label="Proofprint">{[['print', 'The print'], ['earn', 'What it earned'], ['read', 'What it reads'], ['proofs', 'Every proof']].map(([k, l]) => <button key={k} type="button" role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)} data-testid={`pp-tab-${k}`}>{l}</button>)}</div>
    {tab === 'print' ? <><div className="pp-tools"><span className="m-seg" role="group" aria-label="Which proofs">{LENS.map(([k, l]) => <button key={k} type="button" className={lens === k ? 'active' : ''} aria-pressed={lens === k} onClick={() => setLens(k)} data-tip={k === 'all' ? 'Every kind of proof' : `Only its ${l} ridges`} data-testid={`pp-lens-${k}`}>{l}</button>)}</span>
        <span className="pp-replay" data-tip="Watch its print grow, one proof at a time"><button type="button" className="m-btn" disabled={sorted.length < 2} aria-pressed={playing} onClick={() => { if (!playing && at == null) setAt(0); setPlaying(x => !x); }} aria-label={playing ? 'Pause' : 'Replay its print'} data-testid="pp-play">{playing ? '❚❚' : '▶'}</button><input type="range" min="0" max={sorted.length} value={n} onChange={e => { setPlaying(false); setAt(Number(e.target.value)); }} aria-label="Replay" /><b className="m-num">{n}/{sorted.length}</b></span></div>
      <PrintStage print={print} id={id} label="LIVING PROOFPRINT" empty="Its first finished proof draws its first ridge." onOpen={setBig} />
      <div className="pp-stats">{[['STRONG', st.strong, 'Proofs that scored 80 or better'], ['MEDIUM', st.medium, 'Proofs that scored 55 to 79'], ['WEAK', st.weak, 'Proofs under 55']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b><i aria-hidden="true"><u style={{ transform: `scaleX(${Math.max(0.02, v / most)})` }} /></i></span>)}<span data-tip="Its average score, 0 to 100"><small>AVERAGE</small><b className="m-num">{st.avg}</b></span><span data-tip="Its longest run at 55 or better, and its run right now"><small>BEST RUN · NOW</small><b className="m-num">{st.bestRun} · {st.run}</b></span><span data-tip="Real trades of +50% or more. Only these can pay the Pool"><small>+50% WINS</small><b className="m-num">{st.big}</b></span></div></> : null}
    {tab === 'earn' ? <section className="pp-earn"><div className="bst-tiles">{[['LOCKED', money(p.lockedUsd), 'Still releasing'], ['SENT', money(p.sentUsd), 'What its proofs sent, at today\'s price'], ['FROM THE FEE POT', money(p.earnedUsd), 'What members\' trading fees have added so far'], ['FEE POT PART', `${((p.potShare || 0) * 100).toFixed(2)}%`, 'Its part of the pot right now, by what it has locked and its boost'], ['ADDING A DAY', money(p.feeShareDayUsd), 'What the fee pot adds to its lock at today\'s rate. It rises and falls with trading']].map(([k, v, t]) => <span key={k} data-tip={t}><small>{k}</small><b className="m-num">{v}</b></span>)}</div><Growth hist={p.hist} />
      {p.sends?.length ? <ol className="pp-sends" data-testid="pp-sends">{p.sends.map(s => <li key={s.sig || s.at}><span><b>{s.name || 'Proof'}{s.sym ? ` · $${s.sym}` : ''}</b><small>{new Date(s.at * 1000).toLocaleDateString()}{s.pct != null ? ` · +${Number(s.pct).toFixed(1)}%` : ''}</small></span><em className="m-num" data-tip="Sent · kept by the Collective · locked">{s.sent.toFixed(4)} · {s.kept.toFixed(4)} · {s.locked.toFixed(4)} {s.token}</em>{s.sig ? <span className="pp-send-l"><a href={`https://solscan.io/tx/${s.sig}`} target="_blank" rel="noopener noreferrer" data-tip="Its transaction on Solscan">Tx ↗</a><a href={`/api/cats/receipt/${s.sig}`} target="_blank" rel="noopener noreferrer" data-tip="The receipt read back from the chain">Receipt ↗</a></span> : null}</li>)}</ol> : <p className="fch-nil">Nothing sent yet. A win of +50% or more can send, with its transaction and receipt.</p>}</section> : null}
    {tab === 'read' ? <section className="pp-read" data-testid="pp-read">{[['Strongest', pool?.strongest, 'is-up'], ['Weakest', pool?.weakest, 'is-dn']].map(([h, list2, tone]) => <div key={h}><h4>{h}</h4>{list2?.length ? <ul>{list2.map(t => <li key={t.t} data-tip={`${t.won} won of ${t.n}. Recent proofs count more`}><span>{t.t}</span><i aria-hidden="true"><u className={tone} style={{ transform: `scaleX(${Math.min(1, Math.abs(t.score) / 5)})` }} /></i><b className="m-num">{t.score}</b></li>)}</ul> : <p className="fch-nil">Not enough results yet.</p>}</div>)}</section> : null}
    {tab === 'proofs' ? <section className="pp-list"><h4><Ic3 e="🧾" /> EVERY PROOF<small>Best 2 snapshots each. Saved sealed on FEELESS's own disk, free.</small></h4>
      {list.length ? <ol>{list.map(r => { const two = pickTwo(r.shots); return <li key={r.id}><span><b>{r.name}</b><small>{r.sub}</small></span><em className="m-num">{r.shown}</em>{two.length ? <span className="pp-shots">{two.map(s => <button key={s.file} type="button" onClick={() => setBig(s)} data-tip={s.site}><img src={s.src} alt={s.site} loading="lazy" /></button>)}</span> : null}{r.decisions?.[0] ? <p>{r.decisions[0][0]}: {String(r.decisions[0][1]).slice(0, 160)}</p> : null}</li>; })}</ol> : <p className="fch-nil">No finished proofs yet.</p>}</section> : null}
    {big ? <div className="ast-shade" role="dialog" aria-modal="true" aria-label={big.site} onClick={() => setBig(null)}><img src={big.src} alt={big.site} /></div> : null}
  </div>;
}
