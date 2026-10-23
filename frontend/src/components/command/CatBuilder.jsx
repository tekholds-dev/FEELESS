import React, { useState } from 'react';
import { toast } from 'sonner';
import { CAT_VARIATIONS } from './catCoats';
import { LOOK, cleanLook, LookAvatar } from './CatLook';
import { FeeCatMark } from '../FeeCatMark';
import { EYE_COLOR, GESTURES } from '../Panther';
import { readMyCat, saveMyCat, DEFAULT_CAT } from '../../lib/myCat';
import { goTo } from './FeeCatShell';
import '../../styles/catBuilder.css';

// 🎨 BUILD A CAT (owner, 2026-10-23 — the collection page was a grid of floating heads, "3 fur patterns" that all drew the same, a "Set as featured
// cat" button that only printed a line, and 25 of its 50 coats were copies): a real builder. The STUDIO = your full panther on a violet stage under
// a spotlight (tap a move: it waves, pounces, roars…); the BENCH = coat · pattern · gear · eyes · aura · name, every option drawn (gear tiles
// show the panther wearing it). ⭐ Make it my cat saves it (the FeeCat shell wears it, new agents start from it); 🤖 Give it a job opens
// Create-an-agent with this cat. A look only — nothing is signed, nothing is bought.
export const PATTERNS = [['stripes', 'Stripes'], ['spots', 'Spots'], ['patch', 'Patch']];
const MOVES = GESTURES.filter(g => !['idle', 'sleep'].includes(g));
const AURA_HEX = { none: '#3a3448', royal: '#15d16a', gold: '#f5c542', ice: '#7fd3ff', blaze: '#ff7a3d', nebula: '#b388ff', toxic: '#c6ff3d' };
let builderMoveT = null;
export const LOOKS_TOTAL = CAT_VARIATIONS.length * PATTERNS.length * LOOK.gear.length * LOOK.eyes.length * LOOK.aura.length;

// pure: a random build (Surprise me) — `rnd` injectable for tests
export function surprise(rnd = Math.random) {
  const pick = a => a[Math.floor(rnd() * a.length) % a.length];
  return { coat: Math.floor(rnd() * CAT_VARIATIONS.length) % CAT_VARIATIONS.length, pattern: pick(PATTERNS)[0],
    look: cleanLook({ gear: pick(LOOK.gear)[0], eyes: pick(LOOK.eyes)[0], aura: pick(LOOK.aura)[0], tag: '' }) };
}

export function CatBuilder() {
  const [cat, setCat] = useState(() => readMyCat() || { ...DEFAULT_CAT, coat: 1 });
  const [move, setMove] = useState(null); const [saved, setSaved] = useState(() => !!readMyCat());
  const coat = CAT_VARIATIONS[cat.coat] || CAT_VARIATIONS[0]; const look = cleanLook(cat.look);
  const set = patch => { setCat(c => ({ ...c, ...patch, look: cleanLook({ ...c.look, ...(patch.look || {}) }) })); setSaved(false); };
  const setLook = (k, v) => set({ look: { [k]: v } });
  const me = [coat[0], coat[1], coat[2], cat.pattern];
  const keep = () => { saveMyCat({ ...cat, look }); setSaved(true); toast.success(`⭐ ${cat.name || coat[0]} is your cat — the FeeCat bar wears it`); };
  const job = () => { saveMyCat({ ...cat, look }); goTo(`/terminal/feecat/agents?create=1&avatar=${cat.coat}`); };
  return <section className="cbx" data-testid="cat-builder">
    <div className="cbx-studio" style={{ '--aura': AURA_HEX[look.aura] || '#b388ff', '--fur': coat[1], '--acc': coat[2] }}>
      <i className="cbx-spot" aria-hidden="true" /><i className="cbx-floor" aria-hidden="true" />
      <div className="cbx-cat" data-testid="cbx-cat"><LookAvatar cat={me} look={look} full size={260} large gesture={move} /></div>
      <div className="cbx-plate"><b data-testid="cbx-name">{cat.name || coat[0]}</b><small>{coat[0]} · {cat.pattern} · {look.gear === 'none' ? 'no gear' : look.gear} · {look.eyes} eyes · {look.aura} aura</small></div>
      <div className="cbx-moves" role="group" aria-label="Make it move">{MOVES.map((g, i) => <button key={g} type="button" className={move === g ? 'active' : ''} style={{ '--i': i }}
        onClick={() => { setMove(g); clearTimeout(builderMoveT); builderMoveT = setTimeout(() => setMove(null), 3300); }} data-tip={`Make it ${g}`} data-testid={`cbx-move-${g}`}>{g}</button>)}</div>
      <span className="cbx-count" data-tip={`${CAT_VARIATIONS.length} coats × ${PATTERNS.length} patterns × ${LOOK.gear.length} gear × ${LOOK.eyes.length} eyes × ${LOOK.aura.length} auras`}>
        <b className="m-num">{LOOKS_TOTAL.toLocaleString('en-US')}</b><small>possible cats</small></span>
    </div>
    <div className="cbx-bench">
      <section className="cbx-step" style={{ '--i': 0 }}><header><em>01</em><b>COAT</b><small>{coat[0]}</small></header>
        <div className="cbx-coats" role="radiogroup" aria-label="Coat">{CAT_VARIATIONS.map((c, i) => <button key={c[0]} type="button" role="radio" aria-checked={cat.coat === i} className={cat.coat === i ? 'on' : ''}
          style={{ '--c1': c[1], '--c2': c[2] }} onClick={() => set({ coat: i })} data-tip={c[0]} aria-label={c[0]} data-testid={`cbx-coat-${i}`}><i /></button>)}</div></section>
      <section className="cbx-step" style={{ '--i': 1 }}><header><em>02</em><b>PATTERN</b><small>drawn on the head</small></header>
        <div className="cbx-tiles is-3">{PATTERNS.map(([k, l]) => <button key={k} type="button" className={cat.pattern === k ? 'on' : ''} onClick={() => set({ pattern: k })} aria-pressed={cat.pattern === k} data-testid={`cbx-pat-${k}`} data-tip={`${l} in your coat's accent`}>
          <FeeCatMark size={46} colors={[coat[1], coat[2]]} pattern={k} animate={false} label={`${l} pattern`} /><small>{l}</small></button>)}</div></section>
      <section className="cbx-step" style={{ '--i': 2 }}><header><em>03</em><b>GEAR</b><small>{LOOK.gear.find(g => g[0] === look.gear)?.[1]}</small></header>
        <div className="cbx-tiles">{LOOK.gear.map(([k, l]) => <button key={k} type="button" className={look.gear === k ? 'on' : ''} onClick={() => setLook('gear', k)} aria-pressed={look.gear === k} data-testid={`cbx-gear-${k}`} data-tip={l}>
          <FeeCatMark size={46} colors={[coat[1], coat[2]]} pattern={cat.pattern} gear={k} animate={false} label={`${l} gear`} /><small>{l}</small></button>)}</div></section>
      <div className="cbx-row2">
        <section className="cbx-step" style={{ '--i': 3 }}><header><em>04</em><b>EYES</b></header>
          <div className="cbx-dots">{LOOK.eyes.map(([k, l]) => <button key={k} type="button" className={look.eyes === k ? 'on' : ''} style={{ '--d': EYE_COLOR[k] || '#45e486' }} onClick={() => setLook('eyes', k)} aria-pressed={look.eyes === k} data-testid={`cbx-eyes-${k}`} data-tip={`${l} eyes`}><i /><small>{l}</small></button>)}</div></section>
        <section className="cbx-step" style={{ '--i': 4 }}><header><em>05</em><b>AURA</b></header>
          <div className="cbx-dots">{LOOK.aura.map(([k, l]) => <button key={k} type="button" className={look.aura === k ? 'on' : ''} style={{ '--d': AURA_HEX[k] }} onClick={() => setLook('aura', k)} aria-pressed={look.aura === k} data-testid={`cbx-aura-${k}`} data-tip={`${l} aura`}><i className="is-aura" /><small>{l}</small></button>)}</div></section>
      </div>
      <section className="cbx-step" style={{ '--i': 5 }}><header><em>06</em><b>NAME + TAG</b></header>
        <div className="cbx-names"><input className="m-input" maxLength={16} value={cat.name} onChange={e => set({ name: e.target.value.replace(/[^\w .$-]/g, '') })} placeholder={coat[0]} aria-label="Cat name" data-testid="cbx-name-input" />
          <input className="m-input" maxLength={12} value={look.tag} onChange={e => setLook('tag', e.target.value)} placeholder="tag · 10X OR BUST" aria-label="Name tag" data-testid="cbx-tag-input" /></div></section>
      <div className="cbx-go">
        <button type="button" className="m-btn" onClick={() => set(surprise())} data-testid="cbx-surprise" data-tip="A random coat, pattern, gear, eyes and aura">🎲 Surprise me</button>
        <button type="button" className={`m-btn cbx-keep ${saved ? 'is-saved' : ''}`} onClick={keep} data-testid="cbx-keep" data-tip="Save it as YOUR cat — the FeeCat bar wears it and new agents start from it">{saved ? '✓ YOUR CAT' : '⭐ Make it my cat'}</button>
        <button type="button" className="m-btn m-go" onClick={job} data-testid="cbx-job" data-tip="Create a trading agent wearing this cat (paper, your limits)">🤖 Give it a job →</button>
      </div>
    </div>
  </section>;
}
