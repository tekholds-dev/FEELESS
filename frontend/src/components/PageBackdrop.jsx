import React from 'react';
import '../styles/pageBackdrop.css';

// 🌌 A live backdrop per major page (owner, 2026-10-21: "no dull dead green — glass, real backdrops"): home = graphite aurora + a perspective
// grid floor with drifting light streaks · feecat = violet night with the cat's eyes in the dark and rising embers · launch = amber dusk
// with rocket trails. Behind the page, never under a click; transform / opacity only; still in fx-lite / reduced motion.
export const BACKDROP_OF = page => (page === '' || page === 'fee' ? 'home' : String(page || '').startsWith('feecat') ? 'feecat' : page === 'launch' ? 'launch' : null);
export const PAGE_CLASS = { home: 'pg-home', feecat: 'pg-feecat', launch: 'pg-launch' };
const KIND_CLASS = { home: 'pgb-home', feecat: 'pgb-feecat', launch: 'pgb-launch' };
const N = Array.from({ length: 8 }, (_, i) => i);

export function PageBackdrop({ kind }) {
  if (!kind) return null;
  return <div className={`pgb ${KIND_CLASS[kind]}`} aria-hidden="true">
    <i className="pgb-glow g1" /><i className="pgb-glow g2" /><i className="pgb-glow g3" />
    <i className="pgb-floor" />
    <div className="pgb-bits">{N.map(i => <i key={i} style={{ '--i': i, left: `${(i * 37 + 7) % 96}%` }} />)}</div>
    {kind === 'feecat' ? <i className="pgb-eyes"><b /><b /></i> : null}
    <i className="pgb-vignette" />
  </div>;
}
