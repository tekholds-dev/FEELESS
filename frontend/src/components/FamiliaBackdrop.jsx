import React from 'react';
import '../styles/familiaBackdrop.css';

// 🎬 LA FAMILIA'S OWN WORLD BEHIND THE WHOLE PAGE (owner, 2026-10-22: "familia full bg needs to be custom and all tabs … all specific"): the
// Leaderboard's generic green frame is gone on Familia — every tab gets its own drawn scene behind the page, in noir + gold:
//   home   · FEE CITY HARBOR  — the skyline over black water, two searchlights crossing, harbor fog, gold dust
//   family · THE MANSION      — velvet + gold: a chandelier that breathes, drapes, cigar smoke curling up, gold motes
//   wars   · THE WAR ROOM     — a red siren sweep over a burning skyline, embers rising, smoke rolling
//   board  · THE PODIUM       — three gold spotlights swaying over a stage, confetti glinting down
//   feed   · THE WIRE         — a radar sweep with blips, scanlines, a teletype glow
// Behind every click (pointer-events none), transform / opacity only, still in fx-lite + reduced motion.
const N = n => Array.from({ length: n }, (_, i) => i);
export const SCENES = {
  home: ['FEE CITY HARBOR', 'capital of the trenches'], family: ['THE MANSION', 'the family table'], wars: ['THE WAR ROOM', 'settled on verified trades'],
  board: ['THE PODIUM', 'weekly crowns'], feed: ['THE WIRE', 'everything the families do, live'],
};

function Skyline({ k = 'far' }) {
  return <div className={`fbd-sky fbd-sky-${k}`}>{N(k === 'far' ? 26 : 18).map(i => <i key={i} style={{ '--i': i, '--h': `${(k === 'far' ? 18 : 26) + ((i * 37) % (k === 'far' ? 30 : 44))}%`, '--w': `${3 + ((i * 13) % 4)}%` }} />)}</div>;
}

export function FamiliaBackdrop({ scene = 'home' }) {
  const s = SCENES[scene] ? scene : 'home';
  return <div className={`fbd s-${s}`} aria-hidden="true" data-testid="familia-backdrop">
    <i className="fbd-base" />
    {s === 'home' && <><i className="fbd-moon" /><Skyline k="far" /><Skyline k="near" /><i className="fbd-water" />
      <span className="fbd-search a" /><span className="fbd-search b" /><i className="fbd-fog" /><span className="fbd-dust">{N(16).map(i => <i key={i} style={{ '--i': i, left: `${(i * 61) % 100}%` }} />)}</span></>}
    {s === 'family' && <><i className="fbd-chand" /><i className="fbd-drape l" /><i className="fbd-drape r" /><i className="fbd-floor" />
      <span className="fbd-smoke">{N(5).map(i => <i key={i} style={{ '--i': i, left: `${12 + i * 19}%` }} />)}</span><span className="fbd-dust is-gold">{N(14).map(i => <i key={i} style={{ '--i': i, left: `${(i * 47) % 100}%` }} />)}</span></>}
    {s === 'wars' && <><Skyline k="far" /><i className="fbd-fire" /><Skyline k="near" /><span className="fbd-siren" />
      <span className="fbd-embers">{N(22).map(i => <i key={i} style={{ '--i': i, left: `${(i * 43) % 100}%` }} />)}</span><span className="fbd-smoke is-war">{N(4).map(i => <i key={i} style={{ '--i': i, left: `${i * 27}%` }} />)}</span></>}
    {s === 'board' && <><span className="fbd-spot">{N(3).map(i => <i key={i} style={{ '--i': i }} />)}</span><i className="fbd-stage" />
      <span className="fbd-confetti">{N(24).map(i => <i key={i} style={{ '--i': i, left: `${(i * 37) % 100}%` }} />)}</span></>}
    {s === 'feed' && <><i className="fbd-grid" /><span className="fbd-radar"><i /><b /><b /><b /></span><i className="fbd-scan" />
      <span className="fbd-blips">{N(9).map(i => <i key={i} style={{ '--i': i, left: `${8 + ((i * 29) % 84)}%`, top: `${10 + ((i * 41) % 70)}%` }} />)}</span></>}
    <i className="fbd-grain" /><i className="fbd-vignette" />
  </div>;
}
