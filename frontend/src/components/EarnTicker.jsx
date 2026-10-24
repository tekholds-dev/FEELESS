import React, { useEffect, useState } from 'react';
import '../styles/earnTicker.css';

// 💸 EARNING NOW — real money ticking: `usd` at `apy` % a year (or `perYear` $ directly), counted up every second since the panel opened
// (2 s under fx-lite, paused off-screen). True simple-rate math before gas — the same number the desks quote, alive.
export const perSecond = (usd, apy) => ((Number(usd) || 0) * (Number(apy) || 0) / 100) / (365 * 24 * 3600);
export function EarnTicker({ usd, apy, perYear = null, label = 'EARNING NOW', tip, testid }) {
  const lite = typeof document !== 'undefined' && document.body.classList.contains('fx-lite');
  const [t0] = useState(() => Date.now()); const [now, setNow] = useState(() => Date.now());
  useEffect(() => { const t = setInterval(() => { if (!document.hidden) setNow(Date.now()); }, lite ? 2000 : 1000); return () => clearInterval(t); }, [lite]);
  const ps = perYear != null ? (Number(perYear) || 0) / (365 * 24 * 3600) : perSecond(usd, apy);
  const v = ps * (now - t0) / 1000; const day = ps * 86400;
  return <span className={`etk ${ps > 0 ? 'is-on' : ''}`} data-tip={tip || 'What this money earns while you look, at today\'s live rate — before gas'} data-testid={testid}>
    <em>{label}</em><b className="m-num" key={Math.floor((now - t0) / 1000)}>+${v.toFixed(v < 0.0001 ? 8 : v < 0.01 ? 6 : 4)}</b><small className="m-num">${day >= 1 ? day.toFixed(2) : day.toFixed(4)} a day</small></span>;
}
