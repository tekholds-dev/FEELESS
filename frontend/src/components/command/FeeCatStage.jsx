import React from 'react';
import { Panther } from '../Panther';
import { useLeaderProfile } from '../../lib/feeLeader';
import { FollowFee } from './FeeCatProfile';
import { FeeOwnerBar, feeLook, AURA_HEX } from './FeeOwnerBar';
import '../../styles/feecatStage.css';

// 🐆 FEECAT STAGE (owner, 2026-10-21: "FeeCat terminal tabs + degen styling never got done"): Fee on a violet night stage under a spotlight,
// her gesture follows her state (hunting → think / pounce, napping → sleep, a green day → celebrate), live meter tiles from her own profile
// (balance vs start, realized, win ring, open trades, nine lives) + Follow. The FeeCat shell's nav switches pages (2026-10-23 redo: the stage's
// own rail was a second nav on the same screen).
export const gestureOf = (c, disc) => (disc?.pause || c?.status === 'paused' ? 'sleep' : (c?.realizedPnlSol || 0) > 0 ? 'celebrate' : (c?.positions || []).length ? 'pounce' : 'think');
export const ringDash = pct => `${Math.max(0, Math.min(100, Number(pct) || 0)) * 1.2566} 125.66`;   // r = 20 → circumference 125.66

export function FeeCatStage() {
  const d = useLeaderProfile();
  const c = d?.cat || {}; const disc = d?.discipline || {}; const st = d?.stats || {};
  const start = Number(c.startingBalanceSol) || 25; const bal = Number(c.balanceSol ?? start); const real = Number(c.realizedPnlSol) || 0;
  const open = (c.positions || []).length; const wr = c.winRate; const lives = disc.lives ?? 9;
  const nap = disc.pause || c.status === 'paused';
  const look = feeLook(c);   // 🎨 the creator's look for Fee (every viewer sees it; set from 🎨 STYLE FEE)
  return <section className={`fcs ${nap ? 'is-nap' : 'is-hunt'}`} data-testid="feecat-stage">
    <div className="fcs-sky" aria-hidden="true"><i className="fcs-aur a1" /><i className="fcs-aur a2" />{Array.from({ length: 14 }, (_, i) => <i key={i} className="fcs-spark" style={{ '--i': i }} />)}</div>
    <div className="fcs-hero">
      <div className="fcs-cat" style={{ '--fcs-aura': AURA_HEX[look.aura] || AURA_HEX.royal }}><i className="fcs-spot" aria-hidden="true" /><i className="fcs-ring" aria-hidden="true" />
        <Panther size={150} coat={look.coat} pattern={look.pattern} gear={look.gear} eyes={look.eyes} gesture={d ? gestureOf(c, disc) : 'idle'} auto={!d} label={`${look.name}, the leader of the FEELESS cats`} /></div>
      <div className="fcs-copy">
        <span className={`fcs-status ${nap ? 'nap' : 'hunt'}`}><i />{nap ? 'NAPPING' : open ? `HUNTING · ${open} OPEN` : 'HUNTING'}</span>
        <h1>{look.name} <em>{look.title || 'The Leader of the FEELESS Cats'}</em></h1>
        <p>{disc.why && disc.why !== 'normal size' ? disc.why : nap ? 'Paused — she waits for the market to come back to her.' : 'Reading every live pair the agents and 🔮 FeeCat AI back — she only enters on a germ floor, a higher low or a held breakout.'}</p>
        <div className="fcs-lives" aria-label={`${lives} of 9 lives`}>{Array.from({ length: 9 }, (_, i) => <i key={i} className={i < lives ? 'on' : ''} style={{ '--i': i }} />)}<small>{lives}/9 lives</small></div>
        <FollowFee />
        <FeeOwnerBar cat={d?.cat} />
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
  </section>;
}
