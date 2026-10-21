import React from 'react';
import { CatAvatar } from './FeeBack';
import '../../styles/createCat.css';

// 🐆 Make the cat yours: a gear piece, an aura, eyes and a name tag on top of its coat. Pure look — the engine never reads it.
// Mirrors feecat_service.LOOK_OPTIONS (change both).
export const LOOK = {
  gear: [['none', 'None', ''], ['crown', 'Crown', '👑'], ['shades', 'Shades', '🕶'], ['chain', 'Gold chain', '⛓'], ['headset', 'Headset', '🎧'],
    ['halo', 'Halo', '😇'], ['cap', 'Snapback', '🧢'], ['bow', 'Bow', '🎀'], ['rose', 'Rose', '🌹']],
  aura: [['none', 'None'], ['royal', 'Royal'], ['gold', 'Gold'], ['ice', 'Ice'], ['blaze', 'Blaze'], ['nebula', 'Nebula'], ['toxic', 'Toxic']],
  eyes: [['classic', 'Classic'], ['laser', 'Laser'], ['gold', 'Gold'], ['ice', 'Ice'], ['void', 'Void']],
};
export const DEFAULT_LOOK = { gear: 'none', aura: 'royal', eyes: 'classic', tag: '' };

export const cleanLook = l => {
  const ok = (k, v) => LOOK[k].some(([id]) => id === v);
  const x = { ...DEFAULT_LOOK, ...(l || {}) };
  return { gear: ok('gear', x.gear) ? x.gear : 'none', aura: ok('aura', x.aura) ? x.aura : 'none', eyes: ok('eyes', x.eyes) ? x.eyes : 'classic',
    tag: String(x.tag || '').replace(/[^\w .$-]/g, '').slice(0, 12) };
};

export function LookAvatar({ cat, look, large = false }) {
  const l = cleanLook(look);
  const g = LOOK.gear.find(([id]) => id === l.gear);
  return <span className={`clk clk-a-${l.aura} clk-e-${l.eyes} ${large ? 'is-large' : ''}`} data-testid="cat-look-avatar">
    {l.aura !== 'none' && <span className="clk-aura" aria-hidden><i /><i /></span>}
    <CatAvatar cat={cat} large={large} />
    {l.eyes !== 'classic' && <span className="clk-eyes" aria-hidden><i /><i /></span>}
    {g && g[2] && <span className={`clk-gear clk-g-${l.gear}`} aria-hidden>{g[2]}</span>}
    {l.tag && <span className="clk-tag">{l.tag}</span>}
  </span>;
}

export function LookPicker({ look, onChange }) {
  const l = cleanLook(look);
  const set = (k, v) => onChange(cleanLook({ ...l, [k]: v }));
  const row = (k, label) => <div className="clk-row" key={k}><span className="paper-field-label">{label}</span><div className="clk-seg" role="group" aria-label={label}>
    {LOOK[k].map(([id, name, icon]) => <button type="button" key={id} className={l[k] === id ? 'is-on' : ''} aria-pressed={l[k] === id} onClick={() => set(k, id)} data-testid={`look-${k}-${id}`}>
      {k === 'aura' && id !== 'none' ? <i className={`clk-sw clk-sw-${id}`} /> : icon ? <span>{icon}</span> : null}{name}</button>)}</div></div>;
  return <div className="clk-picker" data-testid="cat-look-picker">
    {row('gear', 'Gear')}{row('aura', 'Aura')}{row('eyes', 'Eyes')}
    <label className="clk-row"><span className="paper-field-label">Name tag</span><input className="m-input" maxLength="12" value={l.tag} onChange={e => set('tag', e.target.value)} placeholder="e.g. 10X OR BUST" data-testid="look-tag" /></label>
  </div>;
}
