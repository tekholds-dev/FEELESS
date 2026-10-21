import React from 'react';
import '../styles/mobScene.css';

// 🌃 The family's city at night (owner, 2026-10-20: "amazing mob live realtime backdrop"): three skyline layers, lit windows that come and go,
// rain, a street lamp, a neon FAMIGLIA sign that flickers, headlights sweeping the street and cigar smoke. `heat` (0–1, the family's live
// activity) brightens the windows and speeds the rain. transform / opacity only; still in fx-lite / reduced motion.
const WIN = Array.from({ length: 18 }, (_, i) => i);
const RAIN = Array.from({ length: 26 }, (_, i) => i);
export function MobScene({ heat = 0.3, sign = 'FAMIGLIA' }) {
  const h = Math.max(0, Math.min(1, Number(heat) || 0));
  return (
    <div className="mob" aria-hidden="true" style={{ '--mob-heat': h.toFixed(2), '--mob-rain': `${(1.6 - h * 0.8).toFixed(2)}s` }}>
      <div className="mob-sky" />
      <div className="mob-moon" />
      <div className="mob-city mob-far" />
      <div className="mob-city mob-mid" />
      <div className="mob-wins">{WIN.map(i => <i key={i} style={{ '--i': i, left: `${(i * 53) % 96 + 2}%`, bottom: `${36 + ((i * 37) % 26)}%` }} />)}</div>
      <div className="mob-city mob-near" />
      <div className="mob-sign"><span>{sign}</span></div>
      <div className="mob-lamp"><i /></div>
      <div className="mob-street"><span className="mob-car" /><span className="mob-car is-back" /></div>
      <div className="mob-rain">{RAIN.map(i => <i key={i} style={{ '--i': i, left: `${(i * 41) % 100}%` }} />)}</div>
      <div className="mob-smoke"><i /><i /><i /></div>
      <div className="mob-vignette" />
    </div>
  );
}
