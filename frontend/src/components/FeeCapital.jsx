import React from 'react';
import { Building } from './FamilyBlock';
import { Billboard, Bridge, Car, CAR_COLORS, Plot } from './cityParts';

// 👑 FEE CITY — the capital (owner, 2026-10-21: "the main city … bigger than the 4 other cities … real looking bridges, land, atmosphere …
// a big real-looking stadium for FUSE ARENA … feature our biggest money-makers"). One island, 8 × 6 cells: 24 premium plots ring five
// landmarks (the stadium, The House, the Creator's Mansion, Rug Shield HQ, the Launch Pad) and Fee Plaza; four suspension bridges run out to
// the outer cities. Every landmark wears its live number on a billboard. CSS 3D, transform / opacity only.
const CELL = 58; const ST = 14; export const SEA = 120;
const at = c => ST + c * (CELL + ST); const span = n => n * CELL + (n - 1) * ST;
export const ISW = span(8) + 2 * ST; export const ISH = span(6) + 2 * ST;
export const FEE_W = ISW + 2 * SEA; export const FEE_H = ISH + 2 * SEA;
export const FEE_PLOTS = [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0], [5, 0], [6, 0], [7, 0], [0, 1], [0, 2], [0, 3], [1, 3], [6, 3], [7, 3],
  [0, 4], [1, 4], [2, 4], [3, 4], [4, 4], [5, 4], [6, 4], [7, 4], [0, 5], [7, 5]];
export const FEE_MARKS = { arena: [2, 1, 4, 3], house: [1, 1, 1, 2], mansion: [6, 1, 2, 1], shield: [6, 2, 1, 1], launch: [7, 2, 1, 1] };
const PLAZA = [1, 5, 6, 1];
const cellRect = ([c, r, w = 1, h = 1]) => ({ x: at(c), y: at(r), w: span(w), h: span(h) });   // island-local
// the bridge out of each side → the city it reaches
export const GATES = [['heights', 'n'], ['harbor', 'w'], ['bay', 'e'], ['docks', 's']];

// pure: world centre of a Fee City plot or landmark (the camera flies there, the vitals stand there)
export function feeSpot(item) {
  const r = cellRect(item?.lm ? FEE_MARKS[item.lm] : FEE_PLOTS[item?.i] || [0, 0]);
  return { x: SEA + r.x + r.w / 2, y: SEA + r.y + r.h / 2 };
}

// pure: the live line each landmark's billboard shows
export function markLine(k, live) {
  const n = x => Math.round(Number(x) || 0).toLocaleString('en-US');
  if (!live) return k === 'mansion' ? 'awaiting the creator family' : '—';
  return { arena: `${n(live.raids)} raids live · MP battles ≥ ${n(live.minMp)} MP`, house: `${n(live.mp)} MP in the vault`,
    mansion: `[${live.tag}] ${live.name} · power ${n(live.power)}`, shield: `${n(live.flagged)} flagged · ${n(live.snipers)} snipers · ${n(live.bundlers)} bundlers`,
    launch: `${n(live.coins)} family coins launched` }[k] || '—';
}

function gateRect(at_) {
  if (at_ === 'n') return { x: SEA + ISW / 2 - 13, y: 0, w: 26, h: SEA + 6, horiz: false };
  if (at_ === 's') return { x: SEA + ISW / 2 - 13, y: SEA + ISH - 6, w: 26, h: SEA + 6, horiz: false };
  if (at_ === 'w') return { x: 0, y: SEA + ISH / 2 - 13, w: SEA + 6, h: 26, horiz: true };
  return { x: SEA + ISW - 6, y: SEA + ISH / 2 - 13, w: SEA + 6, h: 26, horiz: true };
}

// ⚔ the stadium: concrete bowl, three crowd tiers, a lit pitch, two Fuse cards squaring up, four floodlight masts, two sky beams
function Stadium({ hot }) {
  return <div className={`fc-std ${hot ? 'is-hot' : ''}`}>
    <i className="fc-std-base" /><i className="fc-std-tier t1" /><i className="fc-std-tier t2" /><i className="fc-std-tier t3" />
    <i className="fc-std-pitch"><b /></i><i className="fc-std-card a" /><i className="fc-std-card b" /><i className="fc-std-clash" />
    {['m1', 'm2', 'm3', 'm4'].map(m => <i key={m} className={`fc-std-mast ${m}`}><b /></i>)}<i className="fc-std-beam b1" /><i className="fc-std-beam b2" />
  </div>;
}

const ART = {
  arena: live => <Stadium hot={(live?.raids || 0) > 0} />,
  house: () => <><Building l={{ b: 'bank', lvl: 10 }} nowS={0} /><i className="fc-vault" /></>,
  mansion: () => <><i className="fc-lawn" /><Building l={{ b: 'lounge', lvl: 9 }} nowS={0} /><i className="fc-gold" /></>,
  shield: () => <><Building l={{ b: 'tower', lvl: 5 }} nowS={0} /><i className="fc-search"><b /></i></>,
  launch: () => <><i className="fc-pad" /><i className="fc-rocket"><b /><u /></i></>,
};

function Mark({ k, mark, sel, onPick }) {
  const r = cellRect(FEE_MARKS[k]);
  return <button type="button" className={`fc-mark k-${k} ${sel ? 'is-sel' : ''}`} style={{ transform: `translate(${r.x}px, ${r.y}px)`, width: r.w, height: r.h }}
    onClick={() => onPick({ lm: k })} data-testid={`lm-${k}`} data-tip={mark?.lore || k}>{ART[k](mark?.live)}</button>;
}

const BILL_Z = { arena: 130, house: 175, mansion: 128, shield: 205, launch: 92 };   // staggered so neighbouring signs never stack
const TOUR = [['mansion', '1', 'FORM A FAMILY', 'start one or take an invite'], [null, '2', 'BUY PLOTS', 'MP buys turf · Fee City pays ×2.5'],
  ['arena', '3', 'FAMILY FUSE', 'cards match ±1 coin · MP needs 2K'], ['w', '4', 'CROSS & RAID', 'chess on their block']];

export function FeeCapital({ v, sel, onPick, onGo, tour }) {
  const plots = (v.blocks || []).filter(b => b.b === 'fee');
  const marks = Object.fromEntries((v.landmarks || []).map(m => [m.key, m]));
  const cities = Object.fromEntries((v.cities || []).map(c => [c.key, c]));
  const bridge = Object.fromEntries((v.bridges || []).filter(b => b.a === 'fee' || b.b === 'fee').map(b => [b.a === 'fee' ? b.b : b.a, b.name]));
  const routes = [['ra', 2], ['rb', 2], ['rc', 2], ['rd', 2]];
  return <>
    {GATES.map(([k, g]) => { const c = cities[k]; return c ? <Bridge key={k} r={gateRect(g)} name={bridge[k] || 'bridge'}
      gate={{ key: k, at: g, name: c.name, sub: `${c.held}/${c.plots} held`, go: () => onGo(k) }} /> : null; })}
    <div className="fcy-isl fc-isl" style={{ width: ISW, height: ISH, transform: `translate(${SEA}px, ${SEA}px)` }} data-testid="fee-capital">
      <i className="fcy-lanes" aria-hidden="true" /><i className="fc-avenue" aria-hidden="true" />
      {plots.map(x => <Plot key={x.id} x={x} r={cellRect(FEE_PLOTS[x.i] || [0, 0])} sel={sel?.id === x.id} onPick={onPick} premium />)}
      {Object.keys(FEE_MARKS).map(k => <Mark key={k} k={k} mark={marks[k]} sel={sel?.lm === k} onPick={onPick} />)}
      <div className="fc-plaza" style={{ transform: `translate(${cellRect(PLAZA).x}px, ${cellRect(PLAZA).y}px)`, width: cellRect(PLAZA).w, height: cellRect(PLAZA).h }}>
        <i className="fc-fountain"><b /><b /></i>{[0, 1, 2, 3].map(i => <i key={i} className="fc-ped" style={{ '--i': i }} />)}
        <i className="fcy-park fc-tr1"><b className="fcy-tree a" /><b className="fcy-tree b" /></i><i className="fcy-park fc-tr2"><b className="fcy-tree a" /><b className="fcy-tree c" /></i></div>
      {routes.flatMap(([rt, n], j) => Array.from({ length: n }, (_, i) => <Car key={`${rt}${i}`} route={rt} i={i * 3 + j} color={CAR_COLORS[(i + j * 2) % CAR_COLORS.length]} />))}
    </div>
    {Object.keys(FEE_MARKS).map(k => { const s = feeSpot({ lm: k }); return <Billboard key={k} x={s.x} y={s.y} z={BILL_Z[k]} className={`fc-bill k-${k} ${tour ? 'is-dim' : ''}`}>
      <b>{marks[k]?.name || k}</b><small key={markLine(k, marks[k]?.live)}>{markLine(k, marks[k]?.live)}</small></Billboard>; })}
    <Billboard x={SEA + ISW / 2} y={SEA + ISH + 30} z={60} className="fc-title"><b>FEE CITY</b><small>CAPITAL OF THE TRENCHES</small></Billboard>
    {tour ? TOUR.map(([k, n, t, d]) => { const s = k === 'w' ? { x: SEA - 40, y: SEA + ISH / 2 } : k ? feeSpot({ lm: k }) : feeSpot({ i: 3 });
      return <Billboard key={n} x={s.x} y={s.y} z={k === 'arena' ? 200 : 120} className="fc-pin"><i>{n}</i><b>{t}</b><small>{d}</small></Billboard>; }) : null}
  </>;
}
