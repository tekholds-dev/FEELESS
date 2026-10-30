import React, { useId } from 'react';
import '../../styles/critters.css';

// 🐜 BUILD AN AGENT — the other bodies an agent can wear (owner, 2026-10-29: "users can choose between a Queen ant, a real big worker fly, 2 working
// ants — real-life ones with the real live gestures; the queen's customization minimal: wing colour + flutter; ants in real ant colours and types").
// Drawn from scratch, top-down, real anatomy: elbowed antennae, mandibles, compound eyes, head · thorax · petiole · gaster, six jointed legs on a
// TRIPOD GAIT (front + back of one side with the middle of the other — how real ants and flies walk), veined wings. Real gestures: ants tap
// antennae (antennation), raise the gaster on alarm and carry food; a fly rubs its front legs (grooming), buzzes and hovers; the queen fans her wings.
// A look only — nothing is signed or bought. transform / opacity only (crt* keyframes in critters.css).
export const SPECIES = [['cat', '🐱', 'Panther', 'the FeeCat body'], ['queen', '👑', 'Queen ant', 'wings · crown · a colony brain'],
  ['fly', '🪰', 'Worker fly', 'compound eyes · buzz · groom'], ['ants', '🐜', 'Worker ants ×2', 'two workers · they carry the bag']];
// real species, real colours: [key, name, head, thorax, gaster, legs]
export const ANTS = [['fire', 'Fire ant', '#a83c1c', '#b4471f', '#3a1a10', '#7a2e14'], ['carpenter', 'Carpenter ant', '#221c1b', '#2c2321', '#141111', '#4a3a33'],
  ['weaver', 'Weaver ant', '#d9862b', '#e09538', '#c97a22', '#b06a1e'], ['bullet', 'Bullet ant', '#3b1a10', '#4a2216', '#24110a', '#5a2a18'],
  ['honeypot', 'Honeypot ant', '#6b4523', '#7a5029', '#e6a93a', '#5a3a1c'], ['greenhead', 'Green-head ant', '#1f5a46', '#244c3e', '#1a2f2a', '#3a3a2a']];
// [key, name, thorax, stripes, abdomen, eyes]
export const FLIES = [['house', 'Housefly', '#6a6a64', '#2a2a28', '#8c7a52', '#b2322a'], ['blue', 'Bluebottle', '#3a4658', '#1e2430', '#2147a8', '#a8281e'],
  ['green', 'Greenbottle', '#2f8a58', '#1d5a3a', '#2fc074', '#b8301e'], ['hover', 'Hoverfly', '#3a2a12', '#1a1208', '#f2c230', '#5a2a12'],
  ['horse', 'Horse fly', '#4a463a', '#2a2820', '#6a5a3a', '#2f9a6a'], ['robber', 'Robber fly', '#6a5a46', '#3a3226', '#5a4a36', '#7a5a2a']];
export const WINGS = [['clear', 'Clear', '#dff4ff'], ['smoke', 'Smoke', '#7a808c'], ['violet', 'Violet', '#b388ff'], ['gold', 'Gold', '#f5c542'], ['alien', 'Alien', '#9dffcf'], ['rose', 'Rose', '#ff5dbb']];
export const FLUTTER = [['calm', 'Calm', 1.6], ['buzz', 'Buzz', 1], ['frenzy', 'Frenzy', 0.45]];
export const MOVES = { queen: ['flutter', 'antennate', 'march', 'crown'], fly: ['groom', 'buzz', 'hover', 'walk'], ants: ['march', 'carry', 'antennate', 'alarm'] };
export const DEFAULT_AGENT = { species: 'cat', ant: 'fire', fly: 'house', wing: 'clear', flutter: 'buzz' };

// pure: a saved agent body, cleaned (unknown keys fall back)
export function cleanAgent(a) {
  const x = { ...DEFAULT_AGENT, ...(a || {}) }; const has = (list, k) => list.some(r => r[0] === k);
  return { species: has(SPECIES, x.species) ? x.species : 'cat', ant: has(ANTS, x.ant) ? x.ant : 'fire', fly: has(FLIES, x.fly) ? x.fly : 'house',
    wing: has(WINGS, x.wing) ? x.wing : 'clear', flutter: has(FLUTTER, x.flutter) ? x.flutter : 'buzz' };
}
const P = ({ x, y, c, r = 0, children }) => <g transform={`translate(${x} ${y})${r ? ` rotate(${r})` : ''}`}><g className={c}>{children}</g></g>;
const gid = id => String(id).replace(/[^a-zA-Z0-9_-]/g, '');

// a jointed leg from its base (0,0): femur to the knee, tibia to the foot
const Leg = ({ k, f, col, w = 2.2 }) => <path d={`M0 0 L${k[0]} ${k[1]} L${f[0]} ${f[1]}`} stroke={col} strokeWidth={w} fill="none" strokeLinecap="round" strokeLinejoin="round" />;
// the six legs, tripod-grouped: a = left front, right middle, left back · b = the other three
function Legs({ col, y = [0, 8, 16], spread = 1, w }) {
  const L = [[[-14, -10], [-20, -24]], [[-17, 2], [-28, 4]], [[-15, 12], [-22, 28]]];
  return <>{L.map(([k, f], i) => [-1, 1].map(s => {
    const grp = (i % 2 === 0) === (s < 0) ? 'a' : 'b';
    return <P key={`${i}${s}`} x={s * 5} y={y[i]} c={`crt-leg is-${grp} i${i}${i === 0 ? ` is-front ${s < 0 ? 'is-l' : 'is-r'}` : ''}`}>
      <Leg k={[s * Math.abs(k[0]) * spread, k[1]]} f={[s * Math.abs(f[0]) * spread, f[1]]} col={col} w={w} /></P>; }))}</>;
}
const Antennae = ({ col, y = 0, len = 1, cx = 60 }) => <>{[-1, 1].map(s => <P key={s} x={cx + s * 4} y={y} c={`crt-ant ${s < 0 ? 'is-l' : 'is-r'}`}>
  <path d={`M0 0 L${s * 8 * len} ${-12 * len} L${s * 4 * len} ${-26 * len}`} stroke={col} strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
  <circle cx={s * 4 * len} cy={-26 * len} r="1.6" fill={col} /></P>)}</>;

// 🐜 one ant (worker or queen). Centred at (60, 80) in a 120×160 box, head up.
export function Ant({ type = 'fire', queen = false, wing = 'clear', carry = false, className = '' }) {
  const [, , head, thorax, gaster, legs] = ANTS.find(a => a[0] === type) || ANTS[0];
  const wc = (WINGS.find(w => w[0] === wing) || WINGS[0])[2]; const id = gid(useId()); const g = queen ? [21, 31] : [15, 21];
  return <svg className={`crt-svg crt-ant-svg ${queen ? 'is-queen' : ''} ${className}`} viewBox="0 0 120 160" aria-hidden="true">
    <defs><radialGradient id={`gs${id}`} cx="40%" cy="35%" r="70%"><stop offset="0" stopColor="#fff" stopOpacity=".45" /><stop offset=".35" stopColor={gaster} /><stop offset="1" stopColor="#000" stopOpacity=".9" /></radialGradient>
      <radialGradient id={`th${id}`} cx="40%" cy="30%" r="80%"><stop offset="0" stopColor="#fff" stopOpacity=".35" /><stop offset=".4" stopColor={thorax} /><stop offset="1" stopColor="#000" stopOpacity=".7" /></radialGradient>
      <radialGradient id={`hd${id}`} cx="40%" cy="30%" r="80%"><stop offset="0" stopColor="#fff" stopOpacity=".35" /><stop offset=".4" stopColor={head} /><stop offset="1" stopColor="#000" stopOpacity=".75" /></radialGradient></defs>
    <ellipse className="crt-shadow" cx="60" cy="88" rx={queen ? 30 : 24} ry="44" />
    <g className="crt-body">
      <g transform="translate(60 74)"><Legs col={legs} w={queen ? 2.6 : 2.2} /></g>
      <P x={60} y={92 + (queen ? 6 : 0)} c="crt-gaster"><ellipse rx={g[0]} ry={g[1]} fill={`url(#gs${id})`} />
        {[-0.45, -0.1, 0.25, 0.55].map(t => <path key={t} d={`M${-g[0] * 0.92 * Math.sqrt(1 - t * t)} ${t * g[1]} Q0 ${t * g[1] + 4} ${g[0] * 0.92 * Math.sqrt(1 - t * t)} ${t * g[1]}`} stroke="#000" strokeOpacity=".35" strokeWidth="1.1" fill="none" />)}
        <ellipse cx={-g[0] * 0.3} cy={-g[1] * 0.35} rx={g[0] * 0.25} ry={g[1] * 0.2} fill="#fff" opacity=".22" /></P>
      <ellipse cx="60" cy={68 + (queen ? 2 : 0)} rx="4.5" ry="4" fill={thorax} />
      <ellipse cx="60" cy="56" rx={queen ? 11 : 8} ry={queen ? 16 : 14} fill={`url(#th${id})`} />
      {queen ? <g className="crt-wings" style={{ '--wc': wc }}>{[-1, 1].map(s => [0, 1].map(j => <P key={`${s}${j}`} x={60 + s * 5} y={50 + j * 6} r={s * (12 + j * 10)} c={`crt-wing ${s < 0 ? 'is-l' : 'is-r'} w${j}`}>
        <path d={`M0 0 C${s * 10} 14 ${s * 12} ${44 - j * 8} ${s * 3} ${58 - j * 10} C${s * -4} ${46 - j * 8} ${s * -3} 14 0 0 Z`} fill={wc} fillOpacity=".34" stroke={wc} strokeOpacity=".8" strokeWidth=".7" />
        <path d={`M0 2 L${s * 4} ${50 - j * 10} M${s * 1} 14 L${s * 8} 30 M${s * 2} 26 L${s * -1} ${42 - j * 6}`} stroke={wc} strokeOpacity=".7" strokeWidth=".5" fill="none" /></P>))}</g> : null}
      <g className="crt-headg"><Antennae col={legs} y={26} len={queen ? 1.05 : 1} />
        <path d="M60 18 C70 18 73 28 71 36 C69 42 64 45 60 45 C56 45 51 42 49 36 C47 28 50 18 60 18 Z" fill={`url(#hd${id})`} transform="translate(0 -2)" />
        <ellipse cx="50.5" cy="31" rx="2.6" ry="3.6" fill="#0c0c0c" /><ellipse cx="69.5" cy="31" rx="2.6" ry="3.6" fill="#0c0c0c" /><circle cx="50" cy="30" r=".9" fill="#fff" opacity=".7" /><circle cx="69" cy="30" r=".9" fill="#fff" opacity=".7" />
        <P x={60} y={16} c="crt-mand"><path d="M-3 0 C-9 -3 -9 -9 -3 -10 M3 0 C9 -3 9 -9 3 -10" stroke={legs} strokeWidth="2.2" fill="none" strokeLinecap="round" /></P>
        {carry ? <P x={60} y={4} c="crt-coin"><circle r="7" fill="#f5c542" stroke="#8a6410" strokeWidth="1.2" /><text y="3" textAnchor="middle" fontSize="8" fontWeight="900" fill="#5a3e06">F</text></P> : null}
        {queen ? <P x={60} y={22} c="crt-crown"><path d="M-7 3 L-7 -3 L-3.5 0 L0 -5 L3.5 0 L7 -3 L7 3 Z" fill="#f5c542" stroke="#8a6410" strokeWidth=".7" /><circle cy="-5" r="1.1" fill="#ff5dbb" /></P> : null}
      </g>
    </g>
  </svg>;
}

// 🪰 a big worker fly, top-down: red compound eyes (faceted), striped thorax, metallic abdomen, two veined wings, halteres. 120×140 box.
export function Fly({ type = 'house', wing = 'clear', className = '' }) {
  const [, , thorax, stripe, abdomen, eye] = FLIES.find(f => f[0] === type) || FLIES[0];
  const wc = (WINGS.find(w => w[0] === wing) || WINGS[0])[2]; const id = gid(useId()); const banded = type === 'hover';
  return <svg className={`crt-svg crt-fly-svg ${className}`} viewBox="0 0 120 140" aria-hidden="true">
    <defs><radialGradient id={`ab${id}`} cx="38%" cy="30%" r="80%"><stop offset="0" stopColor="#fff" stopOpacity=".55" /><stop offset=".35" stopColor={abdomen} /><stop offset="1" stopColor="#000" stopOpacity=".85" /></radialGradient>
      <radialGradient id={`ey${id}`} cx="35%" cy="30%" r="80%"><stop offset="0" stopColor="#fff" stopOpacity=".5" /><stop offset=".3" stopColor={eye} /><stop offset="1" stopColor="#000" stopOpacity=".6" /></radialGradient>
      <pattern id={`fc${id}`} width="2.4" height="2.4" patternUnits="userSpaceOnUse"><circle cx="1.2" cy="1.2" r=".75" fill="#000" fillOpacity=".25" /></pattern></defs>
    <ellipse className="crt-shadow" cx="60" cy="80" rx="30" ry="40" />
    <g className="crt-body">
      <g transform="translate(60 58)"><Legs col="#4a3e30" y={[-2, 6, 14]} spread={1.3} w={2} /></g>
      <P x={60} y={92} c="crt-gaster"><ellipse rx="16" ry="22" fill={`url(#ab${id})`} />
        {[-12, -2, 8].map(t => <path key={t} d={`M-15 ${t} Q0 ${t + 5} 15 ${t}`} stroke={banded ? '#1a1208' : '#000'} strokeOpacity={banded ? '.95' : '.3'} strokeWidth={banded ? 4 : 1} fill="none" />)}
        <ellipse cx="-5" cy="-8" rx="4" ry="6" fill="#fff" opacity=".25" /></P>
      <ellipse cx="60" cy="62" rx="15" ry="14" fill={thorax} />
      {[-6, -2, 2, 6].map(x => <rect key={x} x={60 + x - 0.9} y="51" width="1.8" height="20" rx=".9" fill={stripe} />)}
      {[[-10, 56], [10, 56], [-11, 66], [11, 66], [-6, 72], [6, 72]].map(([x, y]) => <circle key={`${x}${y}`} cx={60 + x} cy={y} r=".7" fill="#000" />)}
      <circle cx="49" cy="74" r="1.6" fill="#e8d9a8" /><circle cx="71" cy="74" r="1.6" fill="#e8d9a8" />
      <g className="crt-wings" style={{ '--wc': wc }}>{[-1, 1].map(s => <P key={s} x={60 + s * 8} y={58} r={s * 36} c={`crt-wing ${s < 0 ? 'is-l' : 'is-r'}`}>
        <path d={`M0 0 C${s * 14} 8 ${s * 18} 38 ${s * 6} 52 C${s * -4} 48 ${s * -5} 20 0 0 Z`} fill={wc} fillOpacity=".3" stroke={wc} strokeOpacity=".85" strokeWidth=".7" />
        <path d={`M0 2 L${s * 8} 48 M${s * 2} 8 L${s * 13} 30 M${s * 5} 22 L${s * 1} 44 M${s * 9} 30 L${s * 7} 46`} stroke={wc} strokeOpacity=".75" strokeWidth=".5" fill="none" /></P>)}</g>
      <g className="crt-headg"><ellipse cx="60" cy="42" rx="13" ry="8" fill={thorax} />
        {[-1, 1].map(s => <g key={s}><ellipse cx={60 + s * 9} cy="38" rx="9" ry="10" fill={`url(#ey${id})`} /><ellipse cx={60 + s * 9} cy="38" rx="9" ry="10" fill={`url(#fc${id})`} />
          <ellipse cx={60 + s * 7} cy="34" rx="2.4" ry="1.6" fill="#fff" opacity=".55" /></g>)}
        <circle cx="60" cy="30" r="1.2" fill="#2a2a28" /><path d="M58 28 L56 24 M62 28 L64 24" stroke="#1a1612" strokeWidth="1.2" strokeLinecap="round" />
      </g>
    </g>
  </svg>;
}

// the body an agent wears — Panther stays with CatLook; this draws the rest
export function AgentCritter({ agent, gesture = null, size = 220, className = '' }) {
  const a = cleanAgent(agent); const fl = (FLUTTER.find(f => f[0] === a.flutter) || FLUTTER[1])[2];
  const cls = `crt-stage is-${a.species}${gesture ? ` do-${gesture}` : ''} ${className}`;
  return <span className={cls} style={{ '--fl': fl, '--sz': `${size}px` }} data-testid={`crt-${a.species}`}>
    {a.species === 'fly' ? <Fly type={a.fly} wing={a.wing} />
      : a.species === 'ants' ? <><Ant type={a.ant} className="crt-w1" carry={gesture === 'carry'} /><Ant type={a.ant} className="crt-w2" /></>
        : <Ant type={a.ant} queen wing={a.wing} />}
  </span>;
}
