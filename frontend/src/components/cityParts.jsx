import React from 'react';
import { Building } from './FamilyBlock';

// a city building is always finished: Building draws a crane + scaffold while now − at < 45s, and at = 0 made EVERY city building look
// under construction (the owner's "wand over the buildings", 2026-10-21)
export const BUILT = 1e12;

// 🧱 The pieces every Familia city draws with (Fee City + the four outer cities): a plot, a free lot, a car, a bridge with a gate sign.
const STYLES = { family: ['tower', 'casino', 'lounge', 'bank', 'mart', 'lab'], cpu: ['casino', 'tower', 'lounge', 'bank'], cartel: ['docks', 'laundry', 'lab', 'pharma'], mine: ['tower', 'casino', 'bank', 'lounge'] };
export const hash = s => { let h = 7; for (const ch of String(s)) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h; };
export const CAR_COLORS = ['#e8e3d6', '#1a1a1e', '#b3122e', '#d4af37', '#2a4a7a', '#7a2a6a', '#3a6a3a'];

// pure: what is drawn on a block — a store building for a held block (level from power), nothing on a free lot
export function buildingOf(b) {
  if (!b.owner) return null;
  const kind = b.mine ? 'mine' : b.kind === 'cpu' ? 'cpu' : b.kind === 'cartel' ? 'cartel' : 'family';
  const set = STYLES[kind];
  const lvl = Math.max(1, Math.min(6, Math.round(Math.log10(1 + (b.power || 0)) * 1.6)));
  return { kind, l: { b: b.home ? 'tower' : set[hash(b.id) % set.length], lvl, at: 0 } };
}

export function Car({ route, i, color }) {
  return <i className={`fcy-car r-${route}`} style={{ '--i': i, '--car': color }}><b className="fcy-cbody"><u className="fcy-croof" /></b><s className="fcy-beam" /></i>;
}

// an empty lot is never a bare tile: a parking lot with parked cars, or a little park — the FOR SALE sign shows on hover
function FreeLot({ id }) {
  const h = hash(id);
  return <>{h % 2 ? <i className="fcy-park"><b className="fcy-tree a" /><b className="fcy-tree b" /><b className="fcy-tree c" /></i>
    : <i className="fcy-lotp">{[0, 1, 2].map(k => <b key={k} className="fcy-parked" style={{ '--k': k, '--car': CAR_COLORS[(h + k) % CAR_COLORS.length] }} />)}</i>}
    <i className="fcy-sale"><b>FOR SALE</b></i></>;
}

export function Plot({ x, r, sel, onPick, premium, raid }) {
  const d = buildingOf(x);
  return <button type="button" className={`fcy-lot ${d ? `t-${d.kind}` : 't-free'} ${sel ? 'is-sel' : ''} ${x.home ? 'is-home' : ''} ${premium ? 'is-prem' : ''}`}
    style={{ transform: `translate(${r.x}px, ${r.y}px)`, width: r.w, height: r.h }} onClick={() => onPick(x)} data-testid={`blk-${x.id}`}
    data-tip={x.owner ? `[${x.tag}] ${x.name}${x.home ? ' · home block' : ''} · power ${Math.round(x.power || 0).toLocaleString('en-US')}` : `${premium ? 'Premium Fee City plot' : 'Free block'} — buy it for turf (+4 % production, +1 recruit seat, more reach)`}>
    {d ? <><Building l={d.l} nowS={BUILT} /><i className="fcy-crown" /><span className="fcy-tag">{x.tag}</span></> : <FreeLot id={x.id} />}
    {sel ? <i className="fcy-beamup" /> : null}{raid ? <i className="fc-raid" aria-hidden="true" /> : null}
  </button>;
}

// a suspension bridge deck: rails, two gold towers, the cable, cars crossing; `gate` puts a sign at its far end that takes you to that city
export function Bridge({ r, name, gate }) {
  return <div className={`fcy-bridge ${r.horiz ? 'is-h' : 'is-v'}`} style={{ transform: `translate(${r.x}px, ${r.y}px)`, width: r.w, height: r.h }} data-tip={`🌉 ${name}`}>
    <i className="fcy-rail r1" /><i className="fcy-rail r2" /><i className="fcy-tower t1" /><i className="fcy-tower t2" /><i className="fcy-cable" />
    <i className="fcy-bcar c1" style={{ '--car': '#ffd36b' }} /><i className="fcy-bcar c2" style={{ '--car': '#e8e3d6' }} />
    {gate ? <button type="button" className={`fc-gate at-${gate.at}`} onClick={gate.go} data-testid={`gate-${gate.key}`} data-tip={`Cross the ${name} to ${gate.name}`}>
      <b>{gate.at === 'w' || gate.at === 'n' ? '◂ ' : ''}{gate.name}{gate.at === 'e' || gate.at === 's' ? ' ▸' : ''}</b>{gate.sub ? <small>{gate.sub}</small> : null}</button> : null}
  </div>;
}

// a sign that always faces the viewer, standing `z` px above its spot (vitals, billboards, the tour pins)
export function Billboard({ x, y, z = 90, className = '', children }) {
  return <div className={`fc-bb ${className}`} style={{ transform: `translate(${x}px, ${y}px)`, '--z': `${z}px` }}><div className="fc-bbin">{children}</div></div>;
}
