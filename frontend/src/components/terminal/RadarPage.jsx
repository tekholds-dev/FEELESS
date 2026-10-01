import React from 'react';
import { useNavigate } from 'react-router-dom';

// Radar = Watchlist + Signal alerts in one place: what you watch and what's firing, one tap apart.
// /terminal/alerts and ?view=signals open the Signals side, so every old link still lands right.
export function RadarPage({ view, signals, watching, watchCount = 0 }) {
  const nav = useNavigate();
  return <section className="radar-page" data-testid="radar-page">
    <div className="radar-head"><div><span className="m-label">RADAR</span><h1>Watch it. Get pinged.</h1></div>
      <div className="m-seg" role="tablist" aria-label="Radar view">
        <button type="button" role="tab" aria-selected={view === 'signals'} className={view === 'signals' ? 'active' : ''} data-testid="radar-signals" onClick={() => nav('/terminal/watchlist?view=signals')}>⚡ Signals</button>
        <button type="button" role="tab" aria-selected={view === 'watching'} className={view === 'watching' ? 'active' : ''} data-testid="radar-watching" onClick={() => nav('/terminal/watchlist')}>★ Watching {watchCount}</button>
      </div></div>
    {view === 'signals' ? signals : watching}
  </section>;
}
