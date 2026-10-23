import React, { useCallback, useEffect, useId, useRef, useState } from 'react';
import '../styles/panther.css';

// 🐆 FEECAT IS A BLACK PANTHER (owner, 2026-10-20: "a cool live animation and 8 gestures for this cartoon-like black panther, not the alien cats —
// users can choose different panther variants, like a pink panther"). One SVG rig, every part its own group so a gesture moves only transform /
// opacity: idle (breathe + blink + tail) · wave · pounce · roar · purr · sleep · celebrate · think. `crop="head"` = the small mark (FeeCatMark).
export const GESTURES = ['idle', 'wave', 'pounce', 'roar', 'purr', 'sleep', 'celebrate', 'think'];
export const GESTURE_WORD = { idle: '😼 idle', wave: '👋 wave', pounce: '💥 pounce', roar: '🔥 roar', purr: '💚 purr', sleep: '💤 sleep', celebrate: '🎉 celebrate', think: '🤔 think' };
export const COATS = {
  black: { name: 'Black panther', fur: '#16171c', fur2: '#2b2d36', eye: '#45e486', nose: '#3a2b33', glow: 'rgba(69,228,134,.45)' },
  pink: { name: 'Pink panther', fur: '#f17aa8', fur2: '#ffb3cf', eye: '#ffe066', nose: '#b03a6b', glow: 'rgba(255,128,180,.5)' },
  gold: { name: 'Gold panther', fur: '#c9971f', fur2: '#f5cf5c', eye: '#0f3d24', nose: '#6b4a10', glow: 'rgba(245,197,66,.5)' },
  snow: { name: 'Snow panther', fur: '#dfe6ee', fur2: '#ffffff', eye: '#4fb8ff', nose: '#8a97a6', glow: 'rgba(160,210,255,.5)' },
  royal: { name: 'Royal panther', fur: '#0b2a19', fur2: '#15553a', eye: '#45e486', nose: '#041a0f', glow: 'rgba(21,209,106,.55)' },
  shadow: { name: 'Shadow panther', fur: '#231436', fur2: '#43286b', eye: '#d6b4ff', nose: '#170b26', glow: 'rgba(180,140,255,.5)' },
  neon: { name: 'Neon panther', fur: '#06080c', fur2: '#0e1520', eye: '#ff3df0', nose: '#2a1030', glow: 'rgba(255,61,240,.55)' },
};
const KEY = 'feeless.panther';
export const readCoat = () => { try { return localStorage.getItem(KEY) || 'black'; } catch { return 'black'; } };
export function setCoat(k) { try { localStorage.setItem(KEY, k); } catch { /* private window */ } window.dispatchEvent(new CustomEvent('feeless:panther', { detail: k })); }
export function useCoat() {
  const [c, setC] = useState(readCoat);
  useEffect(() => { const f = e => setC(e.detail || readCoat()); window.addEventListener('feeless:panther', f); return () => window.removeEventListener('feeless:panther', f); }, []);
  return c;
}

// 🎨 a user's built cat (owner, 2026-10-23 FeeCat redo: "drawn, not emoji props"): its COAT PATTERN drawn on the head, its GEAR drawn in SVG
// inside the head group (it moves with every gesture), its EYES recoloured. Mirrors feecat_service.LOOK_OPTIONS + CatLook.LOOK.
// pure: a coat's highlight — its fur lifted 30 % toward white (the head's radial light), so a dark coat stays dark
export const lift = (hex, k = 0.3) => { const m = /^#?([0-9a-f]{6})$/i.exec(String(hex || '')); if (!m) return hex; const n = parseInt(m[1], 16);
  const ch = sh => Math.round(((n >> sh) & 255) + (255 - ((n >> sh) & 255)) * k); return `#${[16, 8, 0].map(sh => ch(sh).toString(16).padStart(2, '0')).join('')}`; };
export const EYE_COLOR = { laser: '#ff2a3d', gold: '#f5c542', ice: '#7fd3ff', void: '#b48cff' };
function Pattern({ kind, color }) {
  if (kind === 'stripes') return <g className="pt-pat" fill={color} opacity=".55"><path d="M94 34l3 14 3-14zM84 37l4 12 2-12zM110 37l-4 12-2-12z" /><path d="M58 76l14 2-14 4zM142 76l-14 2 14 4zM60 88l12 0-11 4zM140 88l-12 0 11 4z" /></g>;
  if (kind === 'spots') return <g className="pt-pat" fill="none" stroke={color} strokeWidth="2.2" opacity=".6"><circle cx="78" cy="44" r="4" /><circle cx="122" cy="46" r="3.5" /><circle cx="100" cy="40" r="3" /><circle cx="66" cy="84" r="3" /><circle cx="134" cy="84" r="3.5" /></g>;
  if (kind === 'patch') return <path className="pt-pat" d="M104 38c18-2 34 10 36 30 1 12-6 20-16 22-10-8-18-24-20-52z" fill={color} opacity=".5" />;
  return null;
}
export function Gear({ kind }) {
  switch (kind) {
    case 'crown': return <g className="pt-gear g-crown"><path d="M76 34l6-22 9 13 9-18 9 18 9-13 6 22z" fill="#f5c542" stroke="#8a6410" strokeWidth="1.6" strokeLinejoin="round" /><path d="M76 34h48" stroke="#8a6410" strokeWidth="2" /><circle cx="100" cy="10" r="2.6" fill="#ff5d73" /><circle cx="82" cy="14" r="2" fill="#6ad7ff" /><circle cx="118" cy="14" r="2" fill="#45e486" /></g>;
    case 'shades': return <g className="pt-gear g-shades"><path d="M63 59h31l-3 12c-1 5-5 7-11 7h-5c-6 0-10-3-11-8zM106 59h31l-1 11c-1 5-5 8-11 8h-5c-6 0-10-2-11-7z" fill="#0b0d14" stroke="#d6d9e0" strokeWidth="1.6" /><path d="M94 62h12" stroke="#d6d9e0" strokeWidth="2.4" /><path d="M69 63l9-1M112 63l9-1" stroke="#fff" strokeWidth="2" opacity=".55" strokeLinecap="round" /></g>;
    case 'chain': return <g className="pt-gear g-chain"><path d="M66 100c10 18 58 18 68 0" fill="none" stroke="#f5c542" strokeWidth="4.5" strokeDasharray="5 3" strokeLinecap="round" /><circle cx="100" cy="117" r="7" fill="#f5c542" stroke="#8a6410" strokeWidth="1.5" /><path d="M100 112v10M97 114h5a2 2 0 010 4h-4a2 2 0 000 4h5" stroke="#5a3d00" strokeWidth="1.4" fill="none" /></g>;
    case 'headset': return <g className="pt-gear g-headset"><path d="M57 70c0-38 86-38 86 0" fill="none" stroke="#22252e" strokeWidth="6" strokeLinecap="round" /><rect x="49" y="60" width="13" height="22" rx="6" fill="#15d16a" /><rect x="138" y="60" width="13" height="22" rx="6" fill="#15d16a" /><path d="M55 82c3 14 16 19 31 19" stroke="#22252e" strokeWidth="2.6" fill="none" strokeLinecap="round" /><circle cx="88" cy="101" r="3.4" fill="#45e486" /></g>;
    case 'halo': return <g className="pt-gear g-halo"><ellipse cx="100" cy="16" rx="27" ry="6.5" fill="none" stroke="#ffe9a0" strokeWidth="4.5" /><ellipse cx="100" cy="16" rx="27" ry="6.5" fill="none" stroke="#fff" strokeWidth="1.2" opacity=".8" /></g>;
    case 'cap': return <g className="pt-gear g-cap"><path d="M60 46c3-26 77-26 80 0z" fill="#ff5d73" /><path d="M60 46c-12 1-24 5-29 12h37z" fill="#c23a50" /><path d="M100 22v24" stroke="#c23a50" strokeWidth="1.4" /><circle cx="100" cy="21" r="3" fill="#c23a50" /><text x="112" y="40" fontSize="11" fontWeight="900" fill="#fff" fontFamily="JetBrains Mono, monospace">F</text></g>;
    case 'bow': return <g className="pt-gear g-bow" transform="translate(128 30)"><path d="M0 0l-15-9v18zM0 0l15-9v18z" fill="#ff7ab0" stroke="#c2185b" strokeWidth="1.2" /><circle r="4.5" fill="#ff4d8f" /></g>;
    case 'rose': return <g className="pt-gear g-rose" transform="translate(70 30)"><path d="M3 6c7 5 14 5 18 0" stroke="#2f8a3a" strokeWidth="2.6" fill="none" strokeLinecap="round" /><circle r="7.5" fill="#e0234e" /><path d="M-4-1c2-5 7-5 9 0M-2 3c2 2 5 2 6 0" stroke="#7a0a22" strokeWidth="1.3" fill="none" /></g>;
    default: return null;
  }
}

export function Panther({ size = 120, coat, gesture, auto = false, crop, colors, label, onGesture, className = '', pattern = null, gear = null, eyes = null }) {
  const mine = useCoat();
  const C0 = colors ? { fur: colors[0], fur2: lift(colors[0]), eye: '#45e486', nose: '#2a2a2a', glow: `${colors[1]}88` } : (COATS[coat || mine] || COATS.black);   // the fur is the fur; the accent draws the pattern
  const C = EYE_COLOR[eyes] ? { ...C0, eye: EYE_COLOR[eyes] } : C0;
  const id = `pt-${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const [g, setG] = useState(gesture || 'idle'); const timer = useRef(null);
  const play = useCallback((name, ms = 2600) => { setG(name); onGesture?.(name); clearTimeout(timer.current); if (name !== 'idle' && name !== 'sleep') timer.current = setTimeout(() => setG('idle'), ms); }, [onGesture]);
  useEffect(() => { if (gesture) play(gesture, 3200); }, [gesture, play]);
  useEffect(() => () => clearTimeout(timer.current), []);
  useEffect(() => { if (!auto) return undefined; let i = 0; const t = setInterval(() => { if (document.hidden) return; i = (i + 1) % GESTURES.length; play(GESTURES[i] === 'sleep' ? 'purr' : GESTURES[i]); }, 9000); return () => clearInterval(t); }, [auto, play]);
  const head = crop === 'head';
  const pick = () => play(GESTURES[1 + Math.floor(Math.random() * (GESTURES.length - 1))]);
  const worn = gear && gear !== 'none';
  return <svg className={`pt pt-g-${g}${head ? ' is-head' : ''}${eyes && eyes !== 'classic' ? ` pt-e-${eyes}` : ''} ${className}`} width={size} height={size} viewBox={head ? (worn ? '44 2 112 124' : '52 18 96 92') : '0 0 200 200'} role="img"
    aria-label={label || `FeeCat, the ${C.name || 'panther'} — ${g}`} onClick={head ? undefined : pick} onMouseEnter={head ? undefined : () => g === 'idle' && play('wave', 1800)}
    style={{ '--pt-glow': C.glow, '--pt-eye': C.eye }} data-gesture={g}>
    <defs>
      <radialGradient id={`${id}-f`} cx="45%" cy="35%" r="70%"><stop offset="0" stopColor={C.fur2} /><stop offset="1" stopColor={C.fur} /></radialGradient>
      <radialGradient id={`${id}-e`} cx="50%" cy="50%" r="50%"><stop offset="0" stopColor="#fff" stopOpacity=".95" /><stop offset=".35" stopColor={C.eye} /><stop offset="1" stopColor={C.eye} stopOpacity=".6" /></radialGradient>
    </defs>
    {!head ? <ellipse className="pt-shadow" cx="100" cy="186" rx="58" ry="8" fill="#000" opacity=".35" /> : null}
    <g className="pt-all">
      {!head ? <>
        <g className="pt-tail"><path d="M138 160c26-4 40-22 36-46-2-12-12-20-20-16 8 6 10 16 6 26-5 13-18 20-30 22z" fill={`url(#${id}-f)`} /></g>
        <g className="pt-body"><path d="M62 178c-6-34 6-70 38-74 32 4 44 40 38 74z" fill={`url(#${id}-f)`} /><path d="M86 120c8-4 20-4 28 0-2 18-6 34-14 46-8-12-12-28-14-46z" fill={C.fur2} opacity=".25" /></g>
        <g className="pt-pawL"><path d="M70 160c-4 10-4 18 2 22h18c3-6 2-14-2-22z" fill={`url(#${id}-f)`} /><path d="M74 180v-4M80 181v-5M86 180v-4" stroke={C.fur} strokeWidth="1.5" /></g>
        <g className="pt-pawR"><path d="M130 160c4 10 4 18-2 22h-18c-3-6-2-14 2-22z" fill={`url(#${id}-f)`} /><path d="M114 180v-4M120 181v-5M126 180v-4" stroke={C.fur} strokeWidth="1.5" /></g>
      </> : null}
      <g className="pt-head">
        <g className="pt-earL"><path d="M66 46l-6-26 26 14z" fill={`url(#${id}-f)`} /><path d="M67 40l-3-13 12 7z" fill={C.nose} opacity=".55" /></g>
        <g className="pt-earR"><path d="M134 46l6-26-26 14z" fill={`url(#${id}-f)`} /><path d="M133 40l3-13-12 7z" fill={C.nose} opacity=".55" /></g>
        <path d="M100 32c26 0 44 18 44 42 0 22-18 36-44 36s-44-14-44-36c0-24 18-42 44-42z" fill={`url(#${id}-f)`} />
        <path d="M78 86c6 10 14 14 22 14s16-4 22-14c-6 4-14 6-22 6s-16-2-22-6z" fill={C.fur2} opacity=".35" />
        <g className="pt-brow"><path d="M70 58c6-4 14-4 20 0M110 58c6-4 14-4 20 0" stroke={C.fur} strokeWidth="3" strokeLinecap="round" fill="none" opacity=".8" /></g>
        <g className="pt-eyes"><path className="pt-eye" d="M70 66c5-6 15-6 20 0-5 5-15 5-20 0z" fill={`url(#${id}-e)`} /><path className="pt-eye" d="M110 66c5-6 15-6 20 0-5 5-15 5-20 0z" fill={`url(#${id}-e)`} />
          <ellipse cx="80" cy="66" rx="1.6" ry="4" fill="#06110b" /><ellipse cx="120" cy="66" rx="1.6" ry="4" fill="#06110b" /></g>
        <path className="pt-lids" d="M68 66c6-7 16-7 24 0zM108 66c6-7 16-7 24 0z" fill={C.fur} />
        <path d="M95 78h10l-5 6z" fill={C.nose} />
        <g className="pt-mouth"><path d="M100 84v4M100 88c-3 4-8 4-10 1M100 88c3 4 8 4 10 1" stroke={C.nose} strokeWidth="1.6" fill="none" strokeLinecap="round" />
          <path className="pt-roar" d="M88 90c4 12 20 12 24 0-6 3-18 3-24 0z" fill="#6b1a2a" /><path className="pt-fangs" d="M92 91l2 5 2-5zM104 91l2 5 2-5z" fill="#fff" /></g>
        <g className="pt-whisk" stroke={C.fur2} strokeWidth="1" opacity=".6" strokeLinecap="round"><path d="M86 84l-22-2M86 87l-21 4M114 84l22-2M114 87l21 4" /></g>
        {pattern ? <Pattern kind={pattern} color={colors ? colors[1] : C.fur2} /> : null}
        {worn ? <Gear kind={gear} /> : null}
      </g>
      {!head ? <g className="pt-fx" aria-hidden="true">
        <text className="pt-z" x="146" y="40">z</text><text className="pt-z z2" x="156" y="26">Z</text>
        <text className="pt-q" x="148" y="34">?</text><text className="pt-heart" x="140" y="46">💚</text>
        <g className="pt-spark"><circle cx="40" cy="40" r="3" /><circle cx="164" cy="56" r="2.5" /><circle cx="30" cy="110" r="2" /><circle cx="172" cy="120" r="3" /><circle cx="100" cy="14" r="2.5" /></g>
        <path className="pt-roarwave" d="M146 70c8 6 8 22 0 28M156 64c12 10 12 30 0 40" stroke="var(--pt-eye)" strokeWidth="2.5" fill="none" strokeLinecap="round" />
      </g> : null}
    </g>
  </svg>;
}

export function PantherPicker({ size = 64 }) {
  const coat = useCoat();
  return <div className="pt-pick" role="radiogroup" aria-label="Pick your panther" data-testid="panther-pick">{Object.entries(COATS).map(([k, c]) => <button key={k} type="button" role="radio" aria-checked={coat === k}
    className={coat === k ? 'is-on' : ''} onClick={() => setCoat(k)} data-testid={`panther-${k}`}><Panther size={size} coat={k} crop="head" label={c.name} /><small>{c.name}</small></button>)}</div>;
}

export function PantherStage({ size = 220 }) {
  const [g, setG] = useState(null);
  return <div className="pt-stage" data-testid="panther-stage"><Panther size={size} gesture={g} auto onGesture={x => x !== g && setG(null)} />
    <div className="pt-gest" role="group" aria-label="Gestures">{GESTURES.map(k => <button key={k} type="button" onClick={() => setG(k === g ? `${k}` : k)} data-testid={`pt-do-${k}`}>{GESTURE_WORD[k]}</button>)}</div></div>;
}
