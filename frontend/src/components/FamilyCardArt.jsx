import React, { useId } from 'react';
import '../styles/familyCard.css';

// 🃏 THE FAMILY CARD'S BACKDROP ART (owner, 2026-10-22: the card redo — "a drawn trading card"): one drawn scene per card style (crews.CARD),
// behind the crest header, the name and the live vitals. Each scene has ONE calm moving layer (fog, a vault wheel, petals, a neon breath,
// frost glints, a curtain sway) — transform / opacity only, gone in fx-lite / reduced motion.
export const CARD_SCENE = { noir: 'Noir alley', gold: 'Gold vault', blood: 'Blood rose', neon: 'Neon sign', ice: 'Ice', royal: 'Royal velvet' };
const bricks = (y0, y1, x0, x1, h = 9, w = 22) => { let d = ''; for (let y = y0, r = 0; y < y1; y += h, r++) { d += `M${x0},${y} H${x1} `; for (let x = x0 + (r % 2 ? w / 2 : 0); x < x1; x += w) d += `M${x},${y} V${Math.min(y1, y + h)} `; } return d; };
const NOIR_BRICKS = bricks(0, 190, 0, 200);
const NEON_BRICKS = bricks(0, 280, 0, 200, 12, 28);
const SHARDS = [[18, 280, 34, 150, 52, 280], [40, 280, 70, 190, 92, 280], [120, 280, 150, 170, 168, 280], [150, 280, 182, 120, 200, 280], [0, 0, 22, 70, 40, 0], [150, 0, 172, 84, 190, 0], [80, 0, 96, 46, 110, 0]];

export function FamilyCardArt({ style = 'noir' }) {
  const raw = useId(); const id = `fca${raw.replace(/[^a-zA-Z0-9]/g, '')}`;
  return <svg className={`fca fca-${CARD_SCENE[style] ? style : 'noir'}`} viewBox="0 0 200 280" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <radialGradient id={`${id}-glow`} cx=".5" cy=".5" r=".5"><stop offset="0" stopColor="#fff2c4" stopOpacity=".9" /><stop offset="1" stopColor="#fff2c4" stopOpacity="0" /></radialGradient>
      <linearGradient id={`${id}-cone`} x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#ffe7a8" stopOpacity=".38" /><stop offset="1" stopColor="#ffe7a8" stopOpacity="0" /></linearGradient>
      <linearGradient id={`${id}-gold`} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#7a5410" /><stop offset=".45" stopColor="#ffe9a6" /><stop offset=".7" stopColor="#c8922c" /><stop offset="1" stopColor="#6b4a0e" /></linearGradient>
      <radialGradient id={`${id}-vig`} cx=".5" cy=".42" r=".75"><stop offset=".55" stopColor="#000" stopOpacity="0" /><stop offset="1" stopColor="#000" stopOpacity=".7" /></radialGradient>
      <linearGradient id={`${id}-drape`} x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#3a0614" /><stop offset=".25" stopColor="#7a0f2a" /><stop offset=".5" stopColor="#2a0410" /><stop offset=".75" stopColor="#6a0c24" /><stop offset="1" stopColor="#300512" /></linearGradient>
    </defs>
    {style === 'gold' ? <g>
      <rect width="200" height="280" fill="#1a1105" /><rect width="200" height="280" fill={`url(#${id}-glow)`} opacity=".18" />
      <g transform="translate(100 112)" opacity=".62"><circle r="78" fill="#2a1c08" stroke={`url(#${id}-gold)`} strokeWidth="7" /><circle r="62" fill="none" stroke="#c8922c" strokeOpacity=".5" strokeWidth="2" />
        {Array.from({ length: 12 }, (_, i) => <circle key={i} cx={70 * Math.cos(i * Math.PI / 6)} cy={70 * Math.sin(i * Math.PI / 6)} r="3.2" fill="#ffe9a6" stroke="#5a3d0a" strokeWidth=".8" />)}
        <g className="fca-wheel"><circle r="20" fill="none" stroke={`url(#${id}-gold)`} strokeWidth="5" />{[0, 60, 120].map(a => <rect key={a} x="-46" y="-3" width="92" height="6" rx="3" fill={`url(#${id}-gold)`} transform={`rotate(${a})`} />)}<circle r="8" fill="#ffe9a6" /></g></g>
      {[[38, 236], [100, 236], [162, 236], [69, 218], [131, 218], [100, 200]].map(([x, y], i) => <g key={i} transform={`translate(${x} ${y})`}><path d="M-26,14 L-18,0 H18 L26,14 Z" fill={`url(#${id}-gold)`} stroke="#5a3d0a" strokeWidth="1" /><path d="M-16,3 H16" stroke="#fff4c2" strokeOpacity=".7" /></g>)}
    </g> : style === 'blood' ? <g>
      <rect width="200" height="280" fill="#1c0207" /><circle cx="150" cy="70" r="120" fill="#7a0f1f" opacity=".45" />
      <g transform="translate(148 62) scale(2.4)" opacity=".85"><path d="M0,-20 C12,-20 19,-12 19,-2 C19,10 10,17 0,17 C-10,17 -19,10 -19,-2 C-19,-12 -12,-20 0,-20 Z" fill="#b3122e" />
        <path d="M0,-12 C6,-12 9,-7 8,-2 C7,4 0,6 -4,3 C-7,0 -5,-5 -1,-5 C2,-5 3,-2 1,-1" fill="none" stroke="#3a0008" strokeWidth="1.4" /><path d="M-17,2 C-12,10 -5,12 0,10 M17,2 C12,10 5,12 0,10" fill="none" stroke="#3a0008" strokeWidth="1.2" /></g>
      <path d="M-10,250 C40,210 60,240 100,200 C130,170 170,190 210,150" fill="none" stroke="#3d0a10" strokeWidth="5" /><path d="M-10,250 C40,210 60,240 100,200 C130,170 170,190 210,150" fill="none" stroke="#6a1420" strokeWidth="2" />
      {[[30, 226], [62, 222], [92, 208], [128, 182], [168, 176]].map(([x, y], i) => <path key={i} d={`M${x},${y} l4,-9 l3,8 Z`} fill="#3d0a10" />)}
      <g className="fca-petals">{[[30, 0], [80, -40], [130, -10], [170, -60], [60, -90]].map(([x, y], i) => <path key={i} d={`M${x},${y} c6,-4 12,0 8,6 c-3,5 -10,4 -8,-6 Z`} fill="#d81e3c" opacity=".8" style={{ '--i': i }} />)}</g>
    </g> : style === 'neon' ? <g>
      <rect width="200" height="280" fill="#12051f" /><path d={NEON_BRICKS} stroke="#2c1240" strokeWidth="1.2" fill="none" />
      <g className="fca-neon"><rect x="48" y="22" width="104" height="98" rx="20" fill="none" stroke="#ff4dd8" strokeOpacity=".3" strokeWidth="10" /><rect x="48" y="22" width="104" height="98" rx="20" fill="none" stroke="#ffb3f3" strokeWidth="2.4" />
        <rect x="56" y="30" width="88" height="82" rx="14" fill="none" stroke="#5fd4ff" strokeOpacity=".3" strokeWidth="7" /><rect x="56" y="30" width="88" height="82" rx="14" fill="none" stroke="#c9f3ff" strokeWidth="1.6" />
        <path d="M18,132 l7,-12 l7,12 l-7,12 Z M168,132 c0,-8 7,-12 7,-12 c0,0 7,4 7,12 c0,5 -4,7 -7,4 c-3,3 -7,1 -7,-4 Z" fill="none" stroke="#ff4dd8" strokeOpacity=".35" strokeWidth="6" />
        <path d="M18,132 l7,-12 l7,12 l-7,12 Z M168,132 c0,-8 7,-12 7,-12 c0,0 7,4 7,12 c0,5 -4,7 -7,4 c-3,3 -7,1 -7,-4 Z" fill="none" stroke="#ffb3f3" strokeWidth="1.6" /></g>
      <path d="M100,0 V22 M70,0 V24 M130,0 V24" stroke="#3a2a4a" strokeWidth="1.5" /><ellipse cx="100" cy="270" rx="120" ry="30" fill="#ff4dd8" opacity=".12" />
    </g> : style === 'ice' ? <g>
      <rect width="200" height="280" fill="#06131d" /><circle cx="100" cy="90" r="140" fill="#1d4a6b" opacity=".45" />
      {SHARDS.map((p, i) => <g key={i}><polygon points={`${p[0]},${p[1]} ${p[2]},${p[3]} ${p[4]},${p[5]}`} fill="#9fd8ff" fillOpacity=".16" stroke="#cfeeff" strokeOpacity=".45" strokeWidth="1" />
        <path d={`M${p[2]},${p[3]} L${(p[0] + p[4]) / 2},${p[1]}`} stroke="#fff" strokeOpacity=".25" strokeWidth=".8" /></g>)}
      <g className="fca-glints">{[[40, 60], [160, 40], [120, 140], [60, 180], [170, 210], [90, 250]].map(([x, y], i) => <path key={i} d={`M${x},${y - 5} L${x + 1.2},${y - 1.2} L${x + 5},${y} L${x + 1.2},${y + 1.2} L${x},${y + 5} L${x - 1.2},${y + 1.2} L${x - 5},${y} L${x - 1.2},${y - 1.2} Z`} fill="#fff" style={{ '--i': i }} />)}</g>
    </g> : style === 'royal' ? <g>
      <rect width="200" height="280" fill="#08140e" /><ellipse cx="100" cy="270" rx="90" ry="26" fill="#d4af37" opacity=".14" />
      <g className="fca-drape"><path d="M0,0 H58 C52,90 62,180 44,280 H0 Z" fill={`url(#${id}-drape)`} /><path d="M200,0 H142 C148,90 138,180 156,280 H200 Z" fill={`url(#${id}-drape)`} /></g>
      <path d="M0,0 H200 V22 C185,34 170,22 155,34 C140,22 125,34 110,22 C95,34 80,22 65,34 C50,22 35,34 20,22 C10,30 5,26 0,22 Z" fill={`url(#${id}-gold)`} />
      {[20, 65, 110, 155].map(x => <g key={x}><path d={`M${x},28 V44`} stroke="#c8922c" strokeWidth="1.5" /><path d={`M${x - 4},44 H${x + 4} L${x + 2},54 H${x - 2} Z`} fill="#ffe9a6" /></g>)}
      <path d="M100,150 C94,140 86,142 88,150 C90,156 96,156 100,152 C104,156 110,156 112,150 C114,142 106,140 100,150 Z M100,152 V170 M94,164 H106" fill="none" stroke="#d4af37" strokeOpacity=".35" strokeWidth="2" />
    </g> : <g>
      <rect width="200" height="280" fill="#0b0805" /><rect width="200" height="150" fill="#14100c" />
      <path d="M0,0 L58,40 V200 L0,280 Z" fill="#2a1a12" /><path d="M200,0 L142,40 V200 L200,280 Z" fill="#22150e" />
      <path d={NOIR_BRICKS} stroke="#0e0906" strokeWidth="1" fill="none" clipPath={`url(#${id}-walls)`} />
      <clipPath id={`${id}-walls`}><path d="M0,0 L58,40 V200 L0,280 Z M200,0 L142,40 V200 L200,280 Z" /></clipPath>
      <path d="M58,200 L142,200 L200,280 L0,280 Z" fill="#151009" /><path d="M100,200 V280" stroke="#d4af37" strokeOpacity=".18" strokeDasharray="6 8" strokeWidth="2" />
      <g className="fca-lamp"><path d="M38,70 L4,240 H90 Z" fill={`url(#${id}-cone)`} /><circle cx="38" cy="66" r="18" fill={`url(#${id}-glow)`} /></g>
      <path d="M30,62 H46 L42,70 H34 Z" fill="#2a2420" /><path d="M38,58 V40 H62" stroke="#2a2420" strokeWidth="3" fill="none" />
      <ellipse cx="46" cy="252" rx="34" ry="5" fill="#ffe7a8" opacity=".14" />
      <g className="fca-fog"><ellipse cx="60" cy="226" rx="90" ry="14" fill="#d8cfc0" opacity=".08" /><ellipse cx="150" cy="240" rx="80" ry="12" fill="#d8cfc0" opacity=".07" /></g>
    </g>}
    <rect width="200" height="280" fill={`url(#${id}-vig)`} />
  </svg>;
}

