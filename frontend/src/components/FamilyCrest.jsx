import React, { useId } from 'react';
import '../styles/familyCrest.css';

// 🛡 THE FAMILY CREST (owner, 2026-10-22: "badge customizing sucks" → a Call of Duty emblem-editor style crest, our twist). One SVG drawn the same
// everywhere FamilyBadge goes (board, podium, chips, cards): SHAPE → FIELD (c1 / c2) → CHARGE (drawn art, c3, with its own scale / rotate / flip
// that survive a shape change) → FRAME metal (rim gradient + rivets / spikes) → BANNER with the TAG. crews.py PARTS / ADJUST — change both.
// Every drawing lives in a 100 × 112 shield box; the charge in a 60 × 60 box centred on the shape's own centre.
export const SHAPES = {
  heater: 'M2,2 H98 V46 C98,80 76,100 50,110 C24,100 2,80 2,46 Z',
  round: 'M2,2 H98 V60 A48,48 0 0 1 2,60 Z',
  kite: 'M50,2 C80,6 98,20 98,42 C98,70 72,94 50,110 C28,94 2,70 2,42 C2,20 20,6 50,2 Z',
  coin: 'M2,56 A48,48 0 1 1 98,56 A48,48 0 1 1 2,56 Z',
  chevron: 'M2,12 L50,2 L98,12 V62 L50,110 L2,62 Z',
  card: 'M12,2 H88 Q98,2 98,12 V100 Q98,110 88,110 H12 Q2,110 2,100 V12 Q2,2 12,2 Z',
};
const CENTER_Y = { heater: 48, round: 52, kite: 48, coin: 56, chevron: 50, card: 56 };
const RIVETS = {
  heater: [[50, 2], [12, 2], [88, 2], [98, 24], [2, 24], [94, 69], [6, 69], [50, 110]],
  round: [[50, 2], [12, 2], [88, 2], [98, 34], [2, 34], [84, 94], [16, 94], [50, 108]],
  kite: [[50, 2], [85, 15], [15, 15], [98, 42], [2, 42], [82, 80], [18, 80], [50, 110]],
  coin: [[50, 8], [84, 22], [16, 22], [98, 56], [2, 56], [84, 90], [16, 90], [50, 104]],
  chevron: [[50, 2], [98, 12], [2, 12], [98, 40], [2, 40], [74, 86], [26, 86], [50, 110]],
  card: [[50, 2], [95, 5], [5, 5], [98, 56], [2, 56], [95, 107], [5, 107], [50, 110]],
};
export const METAL = {
  iron: ['#2b3036', '#9aa1a8', '#3b4148', '#7b828a', '#24282d'], silver: ['#7d838b', '#f6f8fb', '#a7adb5', '#e9edf2', '#6f757d'],
  gold: ['#7a5410', '#ffe9a6', '#c8922c', '#fff1c4', '#8a6116'], blood: ['#3d0209', '#ff5a73', '#8a0a1f', '#ff8095', '#4a0510'],
  holo: ['#6fd3ff', '#9b5cff', '#ff8fa3', '#ffd36b', '#45e486'], black: ['#000000', '#3c3c3c', '#0a0a0a', '#2c2c2c', '#000000'],
  warlord: ['#1d0d0f', '#b3122e', '#ffd36b', '#b3122e', '#1d0d0f'],
};
const RIVET = { iron: '#c3c9cf', silver: '#ffffff', gold: '#fff1c4', blood: '#ff8095', holo: '#ffffff', black: '#d4af37', warlord: '#ffd36b' };
export const FIELDS = ['plain', 'split', 'bend', 'chevron', 'quarterly', 'stripes'];
export const CHARGE_WORD = { rose: 'Rose', skull: 'Skull', snake: 'Viper', dice: 'Dice', gun: 'Piece', hat: "Don's hat", scorp: 'Scorpion', dragon: 'Dragon', crown: 'Crown', diamond: 'Diamond', sword: 'Crossed blades', wolf: 'Wolf', lion: 'Lion' };

// pure: hex mix (t > 0 toward white, t < 0 toward black) — the enamel shading on every charge
export function shade(hex, t) {
  const h = /^#?([0-9a-f]{6})$/i.exec(hex || '') ? hex.replace('#', '') : 'ffffff';
  const to = t >= 0 ? 255 : 0; const k = Math.min(1, Math.abs(t));
  return `#${[0, 2, 4].map(i => Math.round(parseInt(h.slice(i, i + 2), 16) * (1 - k) + to * k).toString(16).padStart(2, '0')).join('')}`;
}
// pure: dark or light ink for text sitting on `hex`
export const inkOn = hex => { const h = (hex || '#ffffff').replace('#', ''); const [r, g, b] = [0, 2, 4].map(i => parseInt(h.slice(i, i + 2), 16) || 0); return (r * 299 + g * 587 + b * 114) / 1000 > 140 ? '#160f05' : '#fff4dc'; };
const BASE = 1.15;   // the charge fills ~70 % of the shield at 100 %
// pure: the charge transform — centred on the shape, then its own rotate / scale / flip (crews.ADJUST ranges, clamped here too)
export function chargeXf(b, shape) {
  const es = Math.min(1.3, Math.max(0.7, Number(b?.es) || 1)); const er = Math.min(30, Math.max(-30, Number(b?.er) || 0));
  const k = +(es * BASE).toFixed(3);
  return `translate(50 ${CENTER_Y[shape] || 50}) rotate(${er}) scale(${b?.ef ? -k : k} ${k}) translate(-30 -30)`;
}
// pure: a spike on the warlord rim — a triangle at the rivet, tip pointing away from the centre
function spike([x, y], cy) {
  const dx = x - 50; const dy = y - cy; const l = Math.hypot(dx, dy) || 1; const ux = dx / l; const uy = dy / l;
  return `M${(x - uy * 3.5).toFixed(1)},${(y + ux * 3.5).toFixed(1)} L${(x + ux * 9).toFixed(1)},${(y + uy * 9).toFixed(1)} L${(x + uy * 3.5).toFixed(1)},${(y - ux * 3.5).toFixed(1)} Z`;
}
const star = (n, ro, ri, cx = 30, cy = 30) => Array.from({ length: n * 2 }, (_, i) => { const a = (Math.PI * i) / n - Math.PI / 2; const r = i % 2 ? ri : ro; return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`; }).join(' ');
const LION_MANE = star(14, 29, 21);

function Field({ kind, c1, c2 }) {
  const a = { fill: c2 };
  return <g>
    <rect x="0" y="0" width="100" height="112" fill={c1} />
    {kind === 'split' && <rect x="50" y="0" width="50" height="112" {...a} />}
    {kind === 'bend' && <polygon points="0,0 30,0 100,80 100,112 70,112 0,32" {...a} />}
    {kind === 'chevron' && <polygon points="0,72 50,32 100,72 100,94 50,54 0,94" {...a} />}
    {kind === 'quarterly' && <><rect x="50" y="0" width="50" height="56" {...a} /><rect x="0" y="56" width="50" height="56" {...a} /></>}
    {kind === 'stripes' && <><rect x="20" y="0" width="20" height="112" {...a} /><rect x="60" y="0" width="20" height="112" {...a} /></>}
  </g>;
}

// 🎨 the charges — drawn, never emoji. `f` = enamel gradient fill, `d` = dark ink for the detail lines, `s` = deep shade of the accent
function Charge({ k, f, d, s, c }) {
  const ink = { fill: 'none', stroke: d, strokeWidth: 1.4, strokeLinecap: 'round', strokeLinejoin: 'round' };
  const body = { fill: f, stroke: d, strokeWidth: 1.6, strokeLinejoin: 'round' };
  switch (k) {
    case 'skull': return <g><path {...body} d="M30,5 C43,5 53,14 53,27 C53,35 49,39 45,41 L45,48 C45,51 42,54 39,54 L21,54 C18,54 15,51 15,48 L15,41 C11,39 7,35 7,27 C7,14 17,5 30,5 Z" />
      <ellipse cx="21" cy="28" rx="6" ry="7" fill={d} /><ellipse cx="39" cy="28" rx="6" ry="7" fill={d} /><path d="M30,35 L26,42 L34,42 Z" fill={d} />
      <path {...ink} d="M23,46 V54 M30,46 V54 M37,46 V54 M17,44 H43" /><path {...ink} stroke={c} strokeOpacity=".5" d="M14,20 C16,13 22,9 28,8" /></g>;
    case 'snake': return <g><path d="M12,55 C2,44 16,35 30,38 C45,41 55,30 45,20 C39,14 31,16 29,11" fill="none" stroke={d} strokeWidth="10" strokeLinecap="round" />
      <path d="M12,55 C2,44 16,35 30,38 C45,41 55,30 45,20 C39,14 31,16 29,11" fill="none" stroke={f} strokeWidth="7" strokeLinecap="round" />
      <path d="M12,55 C2,44 16,35 30,38 C45,41 55,30 45,20 C39,14 31,16 29,11" fill="none" stroke={d} strokeWidth="1" strokeDasharray="2 3" strokeOpacity=".7" />
      <path {...body} d="M22,10 C22,4 28,1 33,3 C38,5 38,11 34,13 C30,15 22,15 22,10 Z" /><circle cx="31" cy="7" r="1.4" fill={d} />
      <path d="M22,9 L16,8 M16,8 L13,6 M16,8 L13,10" stroke="#ff4d6d" strokeWidth="1.2" strokeLinecap="round" fill="none" /></g>;
    case 'dice': return <g><polygon {...body} points="30,6 53,18 30,30 7,18" /><polygon {...body} points="7,18 30,30 30,56 7,44" /><polygon {...body} points="30,30 53,18 53,44 30,56" />
      <polygon points="7,18 30,30 30,56 7,44" fill={d} fillOpacity=".22" /><polygon points="30,30 53,18 53,44 30,56" fill={d} fillOpacity=".42" />
      <ellipse cx="30" cy="18" rx="3.4" ry="2" fill={d} /><circle cx="14" cy="28" r="2.2" fill={d} /><circle cx="23" cy="45" r="2.2" fill={d} />
      <circle cx="47" cy="26" r="2.2" fill={d} /><circle cx="41.5" cy="37" r="2.2" fill={d} /><circle cx="36" cy="48" r="2.2" fill={d} /></g>;
    case 'gun': return <g><path {...body} d="M5,21 L44,21 L46,17 L50,17 L50,21 L56,21 L56,29 L30,29 L28,33 L23,33 C23,40 21,48 19,55 L8,55 C10,47 12,39 12,32 L5,30 Z" />
      <circle cx="31" cy="25" r="5.5" fill={s} stroke={d} strokeWidth="1.2" /><path {...ink} d="M28,25 H34 M31,22 V28" /><path {...ink} d="M23,33 C23,41 32,41 32,33" />
      <path {...ink} d="M11,40 L20,40 M10,46 L19,46" strokeOpacity=".6" /><path d="M8,22 H42" stroke={c} strokeOpacity=".55" strokeWidth="1.2" /></g>;
    case 'hat': return <g><path {...body} d="M3,41 C13,48 47,48 57,41 C55,37 51,36 47,37 C41,39 19,39 13,37 C9,36 5,37 3,41 Z" />
      <path {...body} d="M14,38 C12,26 16,14 22,12 C26,11 28,16 30,16 C32,16 34,11 38,12 C44,14 48,26 46,38 C40,40 20,40 14,38 Z" />
      <path d="M14,32 C22,35 38,35 46,32 L46,38 C38,41 22,41 14,38 Z" fill={d} /><path {...ink} d="M30,17 C29,22 29,26 30,31" /><path {...ink} stroke={c} strokeOpacity=".5" d="M18,30 C17,24 18,18 21,15" /></g>;
    case 'scorp': return <g><path d="M30,44 C30,53 41,57 47,51 C53,45 50,34 43,33" fill="none" stroke={d} strokeWidth="7" strokeLinecap="round" />
      <path d="M30,44 C30,53 41,57 47,51 C53,45 50,34 43,33" fill="none" stroke={f} strokeWidth="4.6" strokeLinecap="round" strokeDasharray="5 1.5" />
      <path {...body} d="M43,33 L37,30 L42,27 Z" />
      <path d="M23,28 C15,25 11,19 11,13 M37,28 C45,25 49,19 49,13" fill="none" stroke={d} strokeWidth="4.4" strokeLinecap="round" />
      <path d="M23,28 C15,25 11,19 11,13 M37,28 C45,25 49,19 49,13" fill="none" stroke={f} strokeWidth="2.4" strokeLinecap="round" />
      <path {...body} d="M11,13 C6,9 8,3 13,4 C11,7 13,10 16,9 C15,12 13,13 11,13 Z" /><path {...body} d="M49,13 C54,9 52,3 47,4 C49,7 47,10 44,9 C45,12 47,13 49,13 Z" />
      <path {...ink} strokeWidth="1.6" d="M24,32 L13,30 M24,36 L12,38 M24,40 L14,45 M36,32 L47,30 M36,36 L48,38 M36,40 L46,45" />
      <ellipse {...body} cx="30" cy="34" rx="7.5" ry="11" /><path {...ink} d="M23,30 H37 M23,35 H37 M24,40 H36" strokeOpacity=".7" /></g>;
    case 'dragon': return <g><path {...body} d="M26,22 C22,12 16,6 7,3 C13,10 17,17 19,25 Z" /><path {...body} d="M33,20 C31,10 27,4 20,0 C24,8 26,15 26,22 Z" />
      <path {...body} d="M8,51 L1,47 L8,44 Z M10,43 L2,37 L11,36 Z M14,35 L7,28 L16,29 Z" />
      <path {...body} d="M6,58 C6,44 12,32 22,24 C27,20 32,19 38,20 L50,22 C54,23 57,25 57,28 L56,32 L36,34 L52,38 C50,42 46,44 40,44 C34,45 30,47 28,52 L26,58 Z" />
      <path d="M42,33 L43.5,36.5 L45,33 Z M47,32.7 L48.5,36 L50,32.5 Z M44,38.6 L45.5,35.6 L47,39 Z" fill="#fff4dc" stroke={d} strokeWidth=".5" />
      <path d="M36,26 Q40,22 45,25 Q40,28.5 36,26 Z" fill={d} /><circle cx="41" cy="25.4" r="1.3" fill="#ffd36b" /><circle cx="53" cy="25.5" r="1.1" fill={d} />
      <path {...ink} d="M33,22 C37,19.5 41,19.5 46,21.5 M28,30 C31,34 33,35.5 36,34 M12,52 C14,50 16,50 18,52 M14,45 C16,43 18,43 20,45 M17,38 C19,36 21,36 23,38" />
      <path d="M55,36 L60,37 M58,37 L60,35 M58,37 L60,39.5" stroke="#ff4d6d" strokeWidth="1.3" strokeLinecap="round" fill="none" /><path {...ink} stroke={c} strokeOpacity=".5" d="M24,27 C29,23 34,22 38,22" /></g>;
    case 'crown': return <g><path {...body} d="M6,44 L9,15 L20,29 L30,7 L40,29 L51,15 L54,44 Z" /><rect {...body} x="5" y="44" width="50" height="9" rx="2" />
      <circle cx="9" cy="14" r="3.4" fill={c} stroke={d} strokeWidth="1.2" /><circle cx="30" cy="6" r="3.8" fill={c} stroke={d} strokeWidth="1.2" /><circle cx="51" cy="14" r="3.4" fill={c} stroke={d} strokeWidth="1.2" />
      <circle cx="18" cy="48.5" r="2.2" fill="#ff4d6d" stroke={d} strokeWidth=".8" /><path d="M30,45.5 L33,48.5 L30,51.5 L27,48.5 Z" fill="#6fd3ff" stroke={d} strokeWidth=".8" /><circle cx="42" cy="48.5" r="2.2" fill="#15d16a" stroke={d} strokeWidth=".8" />
      <path {...ink} d="M14,40 L46,40" strokeOpacity=".5" /></g>;
    case 'diamond': return <g><path {...body} d="M14,8 H46 L56,22 L30,55 L4,22 Z" /><polygon points="14,8 22,22 4,22" fill="#fff" fillOpacity=".35" /><polygon points="30,8 38,22 22,22" fill="#fff" fillOpacity=".2" />
      <polygon points="38,22 56,22 30,55" fill={d} fillOpacity=".3" /><path {...ink} d="M4,22 H56 M14,8 L22,22 L30,8 L38,22 L46,8 M22,22 L30,55 L38,22" /></g>;
    case 'sword': return <g>{[-40, 40].map(r => <g key={r} transform={`rotate(${r} 30 30)`}><path {...body} d="M28,2 L32,2 L32,40 L30,44 L28,40 Z" /><path d="M30,4 V40" stroke={d} strokeWidth=".8" strokeOpacity=".6" />
      <rect {...body} x="21" y="40" width="18" height="4" rx="1.5" /><rect x="28.6" y="44" width="2.8" height="9" fill={s} stroke={d} strokeWidth="1" /><circle cx="30" cy="55" r="2.8" fill={f} stroke={d} strokeWidth="1.2" /></g>)}</g>;
    case 'wolf': return <g><path {...body} d="M30,55 L22,47 L14,41 L10,27 L6,5 L18,15 L24,13 L30,15 L36,13 L42,15 L54,5 L50,27 L46,41 L38,47 Z" />
      <path d="M10,9 L16,17 L13,24 Z M50,9 L44,17 L47,24 Z" fill={d} fillOpacity=".45" /><path d="M18,28 L26,31 L19,33 Z M42,28 L34,31 L41,33 Z" fill={d} />
      <path d="M26,44 L34,44 L30,49 Z" fill={d} /><path {...ink} d="M30,34 V44 M22,38 L26,42 M38,38 L34,42" /><path {...ink} stroke={c} strokeOpacity=".5" d="M14,30 L18,40" /></g>;
    case 'lion': return <g><polygon points={LION_MANE} fill={s} stroke={d} strokeWidth="1.4" strokeLinejoin="round" />
      <path {...body} d="M30,13 C40,13 45,21 45,30 C45,40 38,48 30,48 C22,48 15,40 15,30 C15,21 20,13 30,13 Z" />
      <path d="M21,28 L27,29 L22,32 Z M39,28 L33,29 L38,32 Z" fill={d} /><path d="M26,36 L34,36 L30,41 Z" fill={d} /><path {...ink} d="M30,41 V44 M30,44 C27,46 24,45 23,43 M30,44 C33,46 36,45 37,43" />
      <path {...ink} d="M19,20 C20,17 22,15 25,14" stroke={c} strokeOpacity=".5" /></g>;
    default: return <g><path d="M30,35 C29,43 31,50 30,58" fill="none" stroke={d} strokeWidth="4" strokeLinecap="round" /><path d="M30,35 C29,43 31,50 30,58" fill="none" stroke={s} strokeWidth="2.2" strokeLinecap="round" />
      <path d="M30,46 C22,42 17,44 14,49 C20,51 26,50 30,46 Z M30,50 C38,46 43,48 46,53 C40,55 34,54 30,50 Z" fill={s} stroke={d} strokeWidth="1.3" />
      <path {...body} d="M30,5 C41,5 47,12 47,21 C47,31 39,37 30,37 C21,37 13,31 13,21 C13,12 19,5 30,5 Z" />
      <path {...ink} d="M30,12 C35,12 38,16 37,21 C36,26 30,28 26,25 C23,22 25,18 29,18 C32,18 33,21 31,22" /><path {...ink} d="M15,24 C19,31 25,33 30,31 M45,24 C41,31 35,33 30,31 M19,10 C22,14 22,18 20,22 M41,10 C38,14 38,18 40,22" /></g>;
  }
}

function Banner({ kind, tag, c2, metal }) {
  const ink = inkOn(c2); const txt = String(tag || '').slice(0, 6);
  const t = { fill: ink, fontFamily: '"JetBrains Mono", monospace', fontWeight: 900, fontSize: 10.5, letterSpacing: 2.2, textAnchor: 'middle' };
  if (kind === 'plate') return <g className="fcr-banner"><path d="M14,114 H106 L111,124 L106,134 H14 L9,124 Z" fill={`url(#${metal})`} stroke="#000" strokeOpacity=".6" strokeWidth="1.2" />
    <path d="M18,117 H102 L105,124 L102,131 H18 L15,124 Z" fill="#000" fillOpacity=".55" /><circle cx="13" cy="124" r="1.6" fill="#fff" fillOpacity=".7" /><circle cx="107" cy="124" r="1.6" fill="#fff" fillOpacity=".7" />
    <text x="60" y="128" {...t} fill="#ffe9a6">{txt}</text></g>;
  if (kind === 'scroll') return <g className="fcr-banner"><rect x="16" y="115" width="88" height="17" fill={c2} stroke="#000" strokeOpacity=".55" strokeWidth="1.2" />
    <rect x="16" y="115" width="88" height="5" fill="#fff" fillOpacity=".18" /><ellipse cx="16" cy="123.5" rx="5" ry="9" fill={shade(c2, -0.35)} stroke="#000" strokeOpacity=".55" strokeWidth="1.2" />
    <ellipse cx="104" cy="123.5" rx="5" ry="9" fill={shade(c2, -0.35)} stroke="#000" strokeOpacity=".55" strokeWidth="1.2" /><ellipse cx="16" cy="123.5" rx="2" ry="4" fill="#000" fillOpacity=".4" /><ellipse cx="104" cy="123.5" rx="2" ry="4" fill="#000" fillOpacity=".4" />
    <text x="60" y="127.5" {...t}>{txt}</text></g>;
  return <g className="fcr-banner"><path d="M26,118 L4,118 L12,126 L4,134 L26,134 Z M94,118 L116,118 L108,126 L116,134 L94,134 Z" fill={shade(c2, -0.4)} stroke="#000" strokeOpacity=".55" strokeWidth="1.2" />
    <path d="M18,114 Q60,124 102,114 L102,130 Q60,140 18,130 Z" fill={c2} stroke="#000" strokeOpacity=".55" strokeWidth="1.2" /><path d="M18,114 Q60,124 102,114 L102,118 Q60,128 18,118 Z" fill="#fff" fillOpacity=".2" />
    <text {...t}><textPath href={`#${metal}-rib`} startOffset="50%">{txt}</textPath></text><path id={`${metal}-rib`} d="M20,125.5 Q60,135.5 100,125.5" fill="none" /></g>;
}

// size: px width. `banner` false = the shield alone (chips / mini tiles). `grid` = the editor's alignment grid over the field. `only` = draw the
// layers up to this one (the editor's layer thumbnails).
const ORDER = ['shape', 'field', 'charge', 'frame', 'banner', 'fx'];
export function FamilyCrest({ b, px = 64, banner = true, grid = false, sheen = true, only, title }) {
  const raw = useId(); const id = `fc${raw.replace(/[^a-zA-Z0-9]/g, '')}`;
  const show = k => !only || ORDER.indexOf(k) <= ORDER.indexOf(only);
  const shape = SHAPES[b?.shape] ? b.shape : 'heater'; const path = SHAPES[shape]; const frame = METAL[b?.frame] ? b.frame : 'iron';
  const c1 = b?.c1 || '#15d16a'; const c2 = b?.c2 || '#ffd36b'; const c3 = b?.c3 || '#ffffff'; const cy = CENTER_Y[shape];
  const withBanner = banner && show('banner'); const vb = withBanner ? '0 0 120 140' : '7 1 106 118';
  const M = METAL[frame];
  return <svg className={`fcr fcr-${frame}`} viewBox={vb} width={px} height={px * (withBanner ? 140 / 120 : 118 / 106)} role="img" aria-label={title || `${b?.name || 'family'} crest`} data-testid="family-crest">
    <defs>
      <clipPath id={`${id}-clip`}><path d={path} /></clipPath>
      <linearGradient id={`${id}-metal`} x1="0" y1="0" x2="1" y2="1">{M.map((c, i) => <stop key={i} offset={i / (M.length - 1)} stopColor={c} />)}</linearGradient>
      <linearGradient id={`${id}-enamel`} x1="0" y1="0" x2=".4" y2="1"><stop offset="0" stopColor={shade(c3, 0.45)} /><stop offset=".55" stopColor={c3} /><stop offset="1" stopColor={shade(c3, -0.38)} /></linearGradient>
      <radialGradient id={`${id}-lit`} cx=".32" cy=".18" r=".9"><stop offset="0" stopColor="#fff" stopOpacity=".32" /><stop offset=".45" stopColor="#fff" stopOpacity="0" /><stop offset="1" stopColor="#000" stopOpacity=".5" /></radialGradient>
      <linearGradient id={`${id}-sheen`} x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#fff" stopOpacity="0" /><stop offset=".5" stopColor="#fff" stopOpacity=".28" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></linearGradient>
    </defs>
    <g transform="translate(10 4)">
      <path d={path} transform="translate(0 3)" fill="#000" opacity=".45" />
      <g clipPath={`url(#${id}-clip)`}>
        {show('field') ? <Field kind={b?.field} c1={c1} c2={c2} /> : <rect width="100" height="112" fill={shade(c1, -0.2)} />}
        {grid ? <g className="fcr-grid">{Array.from({ length: 9 }, (_, i) => <path key={i} d={`M${(i + 1) * 10},0 V112 M0,${(i + 1) * 11.2} H100`} />)}<path className="fcr-axis" d={`M50,0 V112 M0,${cy} H100`} /></g> : null}
        {show('charge') ? <g transform={chargeXf(b, shape)}><Charge k={b?.emblem} f={`url(#${id}-enamel)`} d="#120a0c" s={shade(c3, -0.3)} c={shade(c3, 0.6)} /></g> : null}
        <rect width="100" height="112" fill={`url(#${id}-lit)`} />
        {sheen && px >= 48 ? <rect className="fcr-sheen" x="-60" y="-10" width="40" height="132" fill={`url(#${id}-sheen)`} transform="skewX(-18)" /> : null}
      </g>
      {show('frame') ? <g className="fcr-frame">
        <path d={path} fill="none" stroke="#000" strokeOpacity=".7" strokeWidth="10" strokeLinejoin="round" />
        <path d={path} fill="none" stroke={`url(#${id}-metal)`} strokeWidth="7" strokeLinejoin="round" />
        <path d={path} fill="none" stroke="#fff" strokeOpacity=".35" strokeWidth=".9" strokeLinejoin="round" />
        <path d={path} fill="none" stroke={frame === 'black' ? '#d4af37' : c2} strokeOpacity=".75" strokeWidth="1.2" transform={`translate(50 ${cy}) scale(.88) translate(-50 -${cy})`} />
        {frame === 'warlord' ? RIVETS[shape].map(p => <path key={p.join()} d={spike(p, cy)} fill={`url(#${id}-metal)`} stroke="#000" strokeOpacity=".7" strokeWidth=".8" />) : null}
        {px >= 40 ? RIVETS[shape].map(([x, y]) => <circle key={`${x},${y}`} cx={x} cy={y} r={frame === 'warlord' ? 2 : 1.7} fill={RIVET[frame]} stroke="#000" strokeOpacity=".6" strokeWidth=".6" />) : null}
      </g> : null}
    </g>
    {withBanner ? <Banner kind={b?.banner} tag={b?.tag} c2={c2} metal={`${id}-metal`} /> : null}
  </svg>;
}
