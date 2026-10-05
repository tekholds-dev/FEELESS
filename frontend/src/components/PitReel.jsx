import React, { useEffect, useState } from 'react';
import '../styles/pitReel.css';

// 🎬 The Pit reel: the empty middle of every fight plays a looping cycle of battle scenes between the two fighters.
// Each scene reads the live numbers (who leads, by how much) — the leader's colour wins the clash. Transform/opacity
// only, one keyframe set (`pr*`), static VS under fx-lite / reduced motion, paused off-screen by fxPause (.bf-arena).
export const REEL_SCENES = [
  ['clash', '⚔ BLADE CLASH'],
  ['bolt', '⚡ LIGHTNING DUEL'],
  ['beam', '🔥 BEAM STRUGGLE'],
  ['punch', '🥊 HAYMAKER'],
  ['shield', '🛡 BLOCKED'],
  ['meteor', '☄ METEOR DROP'],
];
export const REEL_MS = 3400;

export function reelLine(scene, p) {
  const d = (p?.a?.now || 0) - (p?.b?.now || 0); const lead = d >= 0 ? p?.a : p?.b; const gap = Math.abs(d);
  if (gap < 0.3) return 'dead even — nobody gives an inch';
  const who = `${lead?.emoji || '🃏'} ${lead?.name || 'Leader'}`;
  return { clash: `${who} wins the clash · +${gap.toFixed(1)}`, bolt: `${who} strikes first · +${gap.toFixed(1)}`, beam: `${who} pushes the beam · +${gap.toFixed(1)}`,
    punch: `${who} lands it · −${gap.toFixed(1)} HP to the other side`, shield: `${who} holds the line · +${gap.toFixed(1)}`, meteor: `${who} calls it down · +${gap.toFixed(1)}` }[scene];
}

export function PitReel({ p, still = false }) {
  const [n, setN] = useState(0);
  useEffect(() => {
    if (still || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const t = setInterval(() => setN(x => x + 1), REEL_MS); return () => clearInterval(t);
  }, [still]);
  const [key, label] = REEL_SCENES[n % REEL_SCENES.length];
  const d = (p?.a?.now || 0) - (p?.b?.now || 0); const side = d > 0.05 ? 'a' : d < -0.05 ? 'b' : 'even';
  // beam meeting point / punch direction lean toward the trailing side, harder the bigger the lead (≤ 34%)
  const lean = Math.round(Math.max(-34, Math.min(34, d * 4)) * 10) / 10;
  return <div className={`pr prs-${key} lead-${side}`} style={{ '--lean': `${lean}%` }} data-testid="pit-reel" data-scene={key}>
    <div className="pr-stage" key={n} aria-hidden="true">
      <span className="pr-f a">{p?.a?.emoji || '🃏'}</span><span className="pr-f b">{p?.b?.emoji || '🃏'}</span>
      {key === 'clash' && <><i className="pr-blade a" /><i className="pr-blade b" /><i className="pr-ring" /><i className="pr-ring r2" />{[0, 1, 2, 3, 4, 5].map(k => <i key={k} className="pr-spark" style={{ '--i': k }} />)}</>}
      {key === 'bolt' && <><i className="pr-bolt a" /><i className="pr-bolt b" /><i className="pr-flash" /></>}
      {key === 'beam' && <><i className="pr-beam a" /><i className="pr-beam b" /><i className="pr-core" /></>}
      {key === 'punch' && <><i className="pr-fist" /><i className="pr-pow" /><i className="pr-ring" /></>}
      {key === 'shield' && <><i className="pr-shield" /><i className="pr-ring" /><i className="pr-ring r2" /></>}
      {key === 'meteor' && <><i className="pr-meteor" /><i className="pr-crater" />{[0, 1, 2, 3, 4, 5].map(k => <i key={k} className="pr-spark" style={{ '--i': k }} />)}</>}
    </div>
    <span className="bf-vs pr-vs" aria-hidden="true"><i className="bf-clash" />VS</span>
    <small className="pr-cap" key={`c${n}`} aria-live="off"><b>{label}</b> {reelLine(key, p)}</small>
  </div>;
}
