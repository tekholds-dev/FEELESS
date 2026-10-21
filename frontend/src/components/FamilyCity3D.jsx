import React, { useMemo, useRef, useState } from 'react';
import { Building } from './FamilyBlock';
import '../styles/familyCity3d.css';

// 🌃 THE CITY IN 3D (owner, 2026-10-21: "it doesn't look nothing like the Sicario block and no cars — you have emojis sliding around a block").
// The SAME building renderer as the family block (CSS 3D boxes: top + four walls, lit windows), six island districts on night water joined by
// suspension bridges, asphalt streets with lane lines and lamps, cars with headlights + taillights driving the streets and crossing the bridges,
// people on the sidewalks, a neon sign per district. Drag to turn, scroll to zoom. transform / opacity only; still in fx-lite / reduced motion.
export const ISLAND = 300;
export const GAP = 84;
export const MARGIN = 46;
const LOT = (ISLAND - 14 * 5) / 4;          // 57.5 — four lots a row, 14px streets
export const lotPos = i => ({ x: 14 + (i % 4) * (LOT + 14), y: 14 + Math.floor(i / 4) * (LOT + 14) });
export const islandPos = (col, row) => ({ x: MARGIN + col * (ISLAND + GAP), y: MARGIN + row * (ISLAND + GAP) });
const STYLES = { family: ['tower', 'casino', 'lounge', 'bank', 'mart', 'lab'], cpu: ['casino', 'tower', 'lounge', 'bank'], cartel: ['docks', 'laundry', 'lab', 'pharma'], mine: ['tower', 'casino', 'bank', 'lounge'] };
const hash = s => { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
// pure: what is drawn on a block — a store building for a held block (level from power), nothing on a free lot
export function buildingOf(b) {
  if (!b.owner) return null;
  const kind = b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : 'family';
  const set = STYLES[kind];
  const lvl = Math.max(1, Math.min(6, Math.round(Math.log10(1 + (b.power || 0)) * 1.6)));
  return { kind, l: { b: b.home ? 'tower' : set[hash(b.id) % set.length], lvl, at: 0 } };
}
// pure: a bridge deck between two neighbouring islands → { x, y, w, h, horiz }
export function bridgeRect(a, b) {
  const pa = islandPos(a.col, a.row); const pb = islandPos(b.col, b.row);
  if (a.row === b.row) { const l = Math.min(pa.x, pb.x) + ISLAND; return { x: l - 6, y: pa.y + ISLAND / 2 - 13, w: GAP + 12, h: 26, horiz: true }; }
  const t = Math.min(pa.y, pb.y) + ISLAND; return { x: pa.x + ISLAND / 2 - 13, y: t - 6, w: 26, h: GAP + 12, horiz: false };
}
const CAR_COLORS = ['#e8e3d6', '#1a1a1e', '#b3122e', '#d4af37', '#2a4a7a', '#7a2a6a', '#3a6a3a'];

function Car({ route, i, color }) {
  return <i className={`fcy-car r-${route}`} style={{ '--i': i, '--car': color }}><b className="fcy-cbody"><u className="fcy-croof" /></b><s className="fcy-beam" /></i>;
}

// an empty lot is never a bare tile: a parking lot with parked cars, or a little park — the FOR SALE sign shows on hover
function FreeLot({ id }) {
  const h = hash(id);
  return <>{h % 2 ? <i className="fcy-park"><b className="fcy-tree a" /><b className="fcy-tree b" /><b className="fcy-tree c" /></i>
    : <i className="fcy-lotp">{[0, 1, 2].map(k => <b key={k} className="fcy-parked" style={{ '--k': k, '--car': CAR_COLORS[(h + k) % CAR_COLORS.length] }} />)}</i>}
    <i className="fcy-sale"><b>FOR SALE</b></i></>;
}

function Island({ b, blocks, boom, sel, onPick, reach }) {
  const p = islandPos(b.col, b.row);
  return <div className={`fcy-isl ${boom === b.key ? 'is-boom' : ''} ${reach === false ? 'is-far' : ''} k-${b.key}`} style={{ transform: `translate(${p.x}px, ${p.y}px)` }} data-testid={`borough-${b.key}`}>
    <i className="fcy-lanes" aria-hidden="true" />
    {[0, 1, 2, 3, 4].flatMap(k => [<i key={`l${k}`} className="fcy-lamp" style={{ transform: `translate(${k * (LOT + 14) + 5}px, 3px) translateZ(14px)` }} />,
      <i key={`r${k}`} className="fcy-lamp" style={{ transform: `translate(${k * (LOT + 14) + 5}px, ${ISLAND - 7}px) translateZ(14px)` }} />])}
    {blocks.map(x => { const d = buildingOf(x); const q = lotPos(x.i); return <button key={x.id} type="button" className={`fcy-lot ${d ? `t-${d.kind}` : 't-free'} ${sel === x.id ? 'is-sel' : ''} ${x.home ? 'is-home' : ''}`}
      style={{ transform: `translate(${q.x}px, ${q.y}px)`, width: LOT, height: LOT }} onClick={() => onPick(x)} data-testid={`blk-${x.id}`}
      data-tip={x.owner ? `[${x.tag}] ${x.name}${x.home ? ' · home block' : ''} · power ${Math.round(x.power || 0).toLocaleString('en-US')}` : 'Free block — buy it for turf (+4 % production, +1 recruit seat, more reach)'}>
      {d ? <><Building l={d.l} nowS={0} /><i className="fcy-crown" /><span className="fcy-tag">{x.tag}</span></> : <FreeLot id={x.id} />}
      {sel === x.id ? <i className="fcy-beamup" /> : null}
    </button>; })}
    {['a', 'b', 'c'].map((r, i) => <Car key={r} route={r} i={i + b.col * 3 + b.row} color={CAR_COLORS[(hash(b.key) + i) % CAR_COLORS.length]} />)}
    {[0, 1, 2, 3].map(i => <i key={`p${i}`} className={`fcy-ped w-${i}`} style={{ '--i': i + b.col }} />)}
    <div className="fcy-sign"><b>{b.name}</b><small>×{b.tier}{boom === b.key ? ' · 🔥 BOOM' : ''}</small></div>
  </div>;
}

export function FamilyCity3D({ v, sel, setSel }) {
  const stage = useRef(null); const rz = useRef(-28); const rx = useRef(54); const zoom = useRef(0.62); const drag = useRef(null); const moved = useRef(false);
  const [spin, setSpin] = useState(false);
  const apply = () => { const s = stage.current; if (!s) return; s.style.setProperty('--rz', `${rz.current}deg`); s.style.setProperty('--rx', `${rx.current}deg`); s.style.setProperty('--zoom', zoom.current); };
  const byB = useMemo(() => { const m = {}; (v.blocks || []).forEach(x => { (m[x.b] = m[x.b] || []).push(x); }); return m; }, [v.blocks]);
  const bors = v.boroughs || [];
  const W = MARGIN * 2 + 3 * ISLAND + 2 * GAP; const H = MARGIN * 2 + 2 * ISLAND + GAP;
  const bridges = (v.bridges || []).map(br => { const a = bors.find(b => b.key === br.a); const b = bors.find(x => x.key === br.b); return a && b ? { ...br, r: bridgeRect(a, b) } : null; }).filter(Boolean);
  React.useEffect(() => { apply(); if (!spin) return undefined; let raf; let last = performance.now();
    const go = t => { rz.current += (t - last) * 0.006; last = t; apply(); raf = requestAnimationFrame(go); }; raf = requestAnimationFrame(go); return () => cancelAnimationFrame(raf); }, [spin]);
  const down = e => { drag.current = { x: e.clientX, y: e.clientY, rz: rz.current, rx: rx.current }; moved.current = false; };
  const move = e => { const d = drag.current; if (!d) return; const dx = e.clientX - d.x; const dy = e.clientY - d.y; if (Math.abs(dx) + Math.abs(dy) > 6) moved.current = true;
    rz.current = d.rz + dx * 0.35; rx.current = Math.max(30, Math.min(68, d.rx - dy * 0.15)); apply(); };
  const up = () => { drag.current = null; };
  const wheel = e => { zoom.current = Math.max(0.38, Math.min(1.4, zoom.current * (e.deltaY > 0 ? 0.92 : 1.08))); apply(); };
  const pick = x => { if (!moved.current) setSel(x); };
  const wx = v.season?.weather || 'clear';
  return <div className={`fcy wx-${wx}`} ref={stage} onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerLeave={up} onWheel={wheel} data-testid="world-map">
    <div className="fcy-sky" aria-hidden="true"><i className="fcy-moon" />{Array.from({ length: 22 }, (_, i) => <i key={i} className="fcy-star" style={{ '--i': i }} />)}</div>
    <div className="fcy-skyline" aria-hidden="true">{Array.from({ length: 18 }, (_, i) => <i key={i} style={{ '--i': i, '--h': `${40 + ((i * 37) % 70)}px` }} />)}</div>
    <div className="fcy-world" style={{ width: W, height: H }}>
      <i className="fcy-water" aria-hidden="true" />
      {bridges.map(br => <div key={br.name} className={`fcy-bridge ${br.r.horiz ? 'is-h' : 'is-v'}`} style={{ transform: `translate(${br.r.x}px, ${br.r.y}px)`, width: br.r.w, height: br.r.h }} data-tip={`🌉 ${br.name}`}>
        <i className="fcy-rail r1" /><i className="fcy-rail r2" /><i className="fcy-tower t1" /><i className="fcy-tower t2" /><i className="fcy-cable" />
        <i className="fcy-bcar c1" style={{ '--car': '#ffd36b' }} /><i className="fcy-bcar c2" style={{ '--car': '#e8e3d6' }} /></div>)}
      {bors.map(b => <Island key={b.key} b={b} blocks={byB[b.key] || []} boom={v.boom?.borough} sel={sel?.id} onPick={pick} reach={v.me?.reach?.[b.key]} />)}
    </div>
    {wx !== 'clear' ? <div className="fcy-wx" aria-hidden="true">{Array.from({ length: wx === 'fog' ? 4 : 30 }, (_, i) => <i key={i} style={{ '--i': i, '--x': `${(i * 37) % 100}%` }} />)}</div> : null}
    <div className="fcy-ctl"><button type="button" className={spin ? 'active' : ''} onClick={() => setSpin(s => !s)} aria-pressed={spin} data-tip="Slowly turn the whole city" data-testid="city-spin">{spin ? '⏸ Stop' : '⟲ 360°'}</button>
      <button type="button" onClick={() => { zoom.current = Math.min(1.4, zoom.current * 1.2); apply(); }} data-tip="Zoom in">＋</button>
      <button type="button" onClick={() => { zoom.current = Math.max(0.38, zoom.current / 1.2); apply(); }} data-tip="Zoom out">－</button>
      <small>drag to turn · scroll to zoom</small></div>
    <ul className="fcy-key"><li className="t-mine">yours</li><li className="t-family">families</li><li className="t-cpu">CPU towns</li><li className="t-cartel">cartels</li><li className="t-free">for sale</li></ul>
  </div>;
}
