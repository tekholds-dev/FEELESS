import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Panther } from '../Panther';
import '../../styles/feecatStage.css';

// 🐆 FEECAT STAGE (owner, 2026-10-21: "FeeCat terminal tabs + degen styling never got done"): Fee on a violet night stage under a spotlight,
// her gesture follows her state (hunting → think / pounce, napping → sleep, a green day → celebrate), live meter tiles from her own profile
// (balance vs start, realized, win ring, open trades, nine lives), and the three tabs as a neon rail with a sliding indicator.
export const gestureOf = (c, disc) => (disc?.pause || c?.status === 'paused' ? 'sleep' : (c?.realizedPnlSol || 0) > 0 ? 'celebrate' : (c?.positions || []).length ? 'pounce' : 'think');
export const ringDash = pct => `${Math.max(0, Math.min(100, Number(pct) || 0)) * 1.2566} 125.66`;   // r = 20 → circumference 125.66

export function FeeCatStage({ tabs, view, onView }) {
  const [d, setD] = useState(null);
  useEffect(() => { let on = true; const load = () => fetch(apiUrl('/api/cats/leader/profile')).then(r => (r.ok ? r.json() : null)).then(x => on && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => { if (!document.hidden) load(); }, 15000); return () => { on = false; clearInterval(t); }; }, []);
  const c = d?.cat || {}; const disc = d?.discipline || {}; const st = d?.stats || {};
  const start = Number(c.startingBalanceSol) || 25; const bal = Number(c.balanceSol ?? start); const real = Number(c.realizedPnlSol) || 0;
  const open = (c.positions || []).length; const wr = c.winRate; const lives = disc.lives ?? 9;
  const nap = disc.pause || c.status === 'paused';
  const idx = Math.max(0, tabs.findIndex(t => t[0] === view));
  return <section className={`fcs ${nap ? 'is-nap' : 'is-hunt'}`} data-testid="feecat-stage">
    <div className="fcs-sky" aria-hidden="true"><i className="fcs-aur a1" /><i className="fcs-aur a2" />{Array.from({ length: 14 }, (_, i) => <i key={i} className="fcs-spark" style={{ '--i': i }} />)}</div>
    <div className="fcs-hero">
      <div className="fcs-cat"><i className="fcs-spot" aria-hidden="true" /><i className="fcs-ring" aria-hidden="true" /><Panther size={150} gesture={d ? gestureOf(c, disc) : 'idle'} auto={!d} /></div>
      <div className="fcs-copy">
        <span className={`fcs-status ${nap ? 'nap' : 'hunt'}`}><i />{nap ? 'NAPPING' : open ? `HUNTING · ${open} OPEN` : 'HUNTING'}</span>
        <h1>Fee <em>{c.title || 'The Leader of the FEELESS Cats'}</em></h1>
        <p>{disc.why && disc.why !== 'normal size' ? disc.why : nap ? 'Paused — she waits for the market to come back to her.' : 'Reading every live pair the agents and OSSY / G4 back — she only enters on a germ floor, a higher low or a held breakout.'}</p>
        <div className="fcs-lives" aria-label={`${lives} of 9 lives`}>{Array.from({ length: 9 }, (_, i) => <i key={i} className={i < lives ? 'on' : ''} style={{ '--i': i }} />)}<small>{lives}/9 lives</small></div>
      </div>
      <div className="fcs-tiles">
        <div className="fcs-tile" data-tip="Her paper balance against what she started with"><em>BALANCE</em><b key={bal}>{bal.toFixed(3)}<small> SOL</small></b>
          <u><s style={{ transform: `scaleX(${Math.max(0.02, Math.min(1, bal / (start * 1.5)))})` }} /></u></div>
        <div className={`fcs-tile ${real > 0 ? 'up' : real < 0 ? 'dn' : ''}`} data-tip="Realized from closed trades — price moves only, fees apart"><em>REALIZED</em><b key={real}>{real >= 0 ? '+' : ''}{real.toFixed(4)}<small> SOL</small></b><small>{st.trades || 0} trades · ROI {st.roiPct ?? 0}%</small></div>
        <div className="fcs-tile fcs-ringtile" data-tip="Share of her closed trades that won"><svg viewBox="0 0 50 50" aria-hidden="true"><circle cx="25" cy="25" r="20" className="bg" /><circle cx="25" cy="25" r="20" className="fg" style={{ strokeDasharray: ringDash(wr) }} /></svg>
          <span><em>WIN RATE</em><b>{wr == null ? '—' : `${wr}%`}</b></span></div>
        <div className="fcs-tile" data-tip="Trades she holds right now"><em>OPEN</em><b key={open}>{open}</b><small>{disc.sizeMult != null ? `size ×${disc.sizeMult}` : ''}</small></div>
      </div>
    </div>
    <nav className="fcs-rail" role="tablist" aria-label="FeeCat" style={{ '--n': tabs.length, '--x': idx }}>
      <i className="fcs-slide" aria-hidden="true" />
      {tabs.map(([k, l, why]) => <button key={k} type="button" role="tab" aria-selected={view === k} className={view === k ? 'active' : ''} onClick={() => onView(k)} data-testid={`fc-tab-${k}`} data-tip={why}>
        <b>{l}</b><small>{why}</small></button>)}
    </nav>
  </section>;
}
