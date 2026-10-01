import React from 'react';
import { useNavigate } from 'react-router-dom';

// Pump radar + Discover in one tab: two lenses, one live stage. Particles float IN FRONT of the cards (pointer-events
// off, transform/opacity only, 16 dots total) and stop under fx-lite / reduced motion.
const DOTS = Array.from({ length: 16 }, (_, i) => i);

export function PumpHub({ lens, radar, discover }) {
  const nav = useNavigate();
  return <section className="pump-hub m-live" data-testid="pump-hub">
    <div className="pump-particles" aria-hidden="true">{DOTS.map(i => <i key={i} style={{ left: `${(i * 37) % 100}%`, animationDelay: `${(i * 0.9) % 7}s`, animationDuration: `${7 + (i % 5) * 1.6}s` }} />)}</div>
    <div className="radar-head"><div><span className="m-label">PUMP RADAR</span><h1>{lens === 'discover' ? 'What the meta is doing.' : 'Catch it before the chart does.'}</h1></div>
      <div className="m-seg" role="tablist" aria-label="Pump radar view">
        <button type="button" role="tab" aria-selected={lens === 'radar'} className={lens === 'radar' ? 'active' : ''} data-testid="pump-lens-radar" onClick={() => nav('/terminal/pump')}>🚀 Radar</button>
        <button type="button" role="tab" aria-selected={lens === 'discover'} className={lens === 'discover' ? 'active' : ''} data-testid="pump-lens-discover" onClick={() => nav('/terminal/pump?view=discover')}>🧭 Discover</button>
      </div></div>
    <div className="pump-stage">{lens === 'discover' ? discover : radar}</div>
  </section>;
}
