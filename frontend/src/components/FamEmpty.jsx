import React from 'react';
import '../styles/famEmpty.css';

// 🌹 an EMPTY Familia room is drawn, never a bare line (owner G: "no dead text"): a small noir-gold scene of what would be here (an empty
// billboard, a quiet crew, a raid board, a launch pad, a search over the pools), a headline, the one line that says how to fill it, and
// the action when there is one. transform / opacity only; still under fx-lite + reduced motion.
const ART = {
  crew: <g><circle cx="30" cy="22" r="7" /><path d="M18 46 C18 34 42 34 42 46" /><circle cx="56" cy="20" r="8" className="hi" /><path d="M42 46 C42 32 70 32 70 46" className="hi" />
    <circle cx="82" cy="22" r="7" /><path d="M70 46 C70 34 94 34 94 46" /><path d="M56 6 v6 M53 9 h6" className="plus" /></g>,
  billboard: <g><rect x="14" y="6" width="84" height="32" rx="3" /><path d="M36 38 v12 M76 38 v12" /><text x="56" y="27" textAnchor="middle" className="blink">YOUR AD</text></g>,
  raid: <g><path d="M22 44 L62 8 M62 8 l-8 1 M62 8 l-1 8" /><path d="M90 44 L50 8 M50 8 l8 1 M50 8 l1 8" /><circle cx="56" cy="30" r="12" className="tgt" /><circle cx="56" cy="30" r="5" className="tgt" /></g>,
  launch: <g><path d="M56 6 C64 14 64 30 60 36 L52 36 C48 30 48 14 56 6 Z" className="hi" /><path d="M52 30 L44 40 L52 36 M60 30 L68 40 L60 36" /><rect x="34" y="44" width="44" height="5" rx="2" /><path d="M54 37 L56 43 L58 37" className="flame" /></g>,
  tower: <g><path d="M40 50 V22 H72 V50" /><path d="M46 22 L56 8 L66 22" className="hi" /><path d="M46 30 h20 M46 38 h20 M46 46 h20" className="plus" /><path d="M20 50 h72" /></g>,
  search: <g><circle cx="48" cy="22" r="13" /><path d="M58 32 L72 46" /><path d="M10 48 q8 -6 16 0 t16 0 t16 0 t16 0 t16 0 t16 0" className="wave" /></g>,
};
export function FamEmpty({ art = 'crew', title, note, children = null, testid }) {
  return <div className={`fem a-${art}`} data-testid={testid || `fam-empty-${art}`}>
    <svg viewBox="0 0 112 54" className="fem-art" aria-hidden="true">{ART[art] || ART.crew}</svg>
    <span className="fem-txt"><b>{title}</b><small>{note}</small></span>{children}
  </div>;
}
