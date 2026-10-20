import React, { useEffect, useState } from 'react';

// 🌌 THE WAR ROOM SKY (owner, 2026-10-19: "war room backdrop way better with live animation, degen addicting look"): a layer BEHIND the room —
// a synth grid floor rolling toward you, a horizon glow, a scan sweep and particles — and it follows the weather over the coin on screen
// (DegenWeather fires `feeless:war-weather`): ☀️ hot = gold embers rising · 🌤 warm = green sparks rising · ⛅ crab = slow dust drifting ·
// 🌧 rain = pink rain falling · ⛈ storm = rain + lightning. transform / opacity only; still in lite mode / reduced motion; paused off-screen.
const N = 22;
export const SKY_TONES = ['hot', 'warm', 'crab', 'rain', 'storm'];
export default function WarSky() {
  const [tone, setTone] = useState('crab');
  useEffect(() => { const on = e => SKY_TONES.includes(e.detail) && setTone(e.detail); window.addEventListener('feeless:war-weather', on); return () => window.removeEventListener('feeless:war-weather', on); }, []);
  return <div className={`wsky t-${tone}`} aria-hidden="true" data-testid="war-sky" data-tone={tone}>
    <i className="wsky-glow" /><i className="wsky-sun" />
    <div className="wsky-floor"><i className="wsky-grid" /></div>
    <i className="wsky-scan" />
    {Array.from({ length: N }, (_, i) => <b key={i} className="wsky-p" style={{ '--i': i, left: `${((i * 37) % 97) + 1.5}%`, '--d': `${4 + (i * 7) % 6}s`, '--o': `${(i * 13) % 9}s` }} />)}
    <i className="wsky-bolt" />
  </div>;
}
