import React, { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';
import '../styles/strategyPicks.css';

// 🎯 3 strategies for a card's round length — 🛡 Steady · 🧠 Engine pick · 🔥 Hunt — from the background sims on REAL recorded prices
// (fees in, re-run ~15 min). One tap applies the exits (TP / SL · ❄ freeze + peak trail · round patience · swap-only-below).
// Shared by HQ tier cards (Edit Fuse) and traders' cards (My cards). It never promises a result: the proof line is what the sims did.
const cache = new Map();   // one fetch per clock per minute, however many cards show it
export function loadStrategies(hours) {
  const k = String(Math.round((hours || 1) * 60));
  const hit = cache.get(k);
  if (hit && Date.now() - hit.at < 60000) return hit.p;
  const p = fetch(apiUrl(`/api/reputation/fuses/strategies?hours=${hours || 1}`)).then(r => r.json()).catch(() => ({ strategies: [] }));
  cache.set(k, { at: Date.now(), p });
  return p;
}
// sim setting → the tier engine's own config keys
// `selection` (real cards): 🎯 Sniper also sets WHAT is bought — record-backed coins only, in a pool at least that deep
export const stratPatch = (cfg, selection) => ({ rideAt: Number(cfg.rideAt), rideTrail: Number(cfg.trail), rotateMinDrop: Number(cfg.minDrop), rotateConfirm: Number(cfg.confirm), tp: Number(cfg.tp), sl: Number(cfg.sl),
  ...(selection && cfg.pool != null ? { runnerMinLiqK: Number(cfg.pool), edgeGate: Number(cfg.edge) > 0 } : {}) });
const sgn = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(1)}%`);
const isOn = (cfg, cur, sel) => !!cur && Number(cur.rideAt) === Number(cfg.rideAt) && Number(cur.rideTrail) === Number(cfg.trail)
  && (!sel || cfg.pool == null || Number(cur.runnerMinLiqK || 0) === Number(cfg.pool));

export function StrategyPicks({ hours, current, onApply, busy, selection, testid = 'strats' }) {
  const [d, setD] = useState(null);
  useEffect(() => { let alive = true; loadStrategies(hours).then(x => alive && setD(x)); return () => { alive = false; }; }, [hours]);
  if (!d) return <div className="sp is-ghost" />;
  if (!d.strategies?.length) return <small className="m-dim sp-empty">{d.note || 'Strategies appear once the sims have run.'}</small>;
  const clk = m => (m >= 60 ? `${m / 60}h` : `${m}m`);
  return <div className="sp" data-testid={testid}><span className="m-label">🎯 {d.strategies.length} STRATEGIES · {clk(d.clock)} ROUNDS</span>
    <div className="sp-row">{d.strategies.map((s, i) => { const on = isOn(s.cfg, current, selection); const sn = s.key === 'sniper'; return <article key={s.key} className={`sp-card s-${s.key} ${on ? 'is-on' : ''}`} style={{ '--i': i }} data-testid={`${testid}-${s.key}`}>
      <b>{s.name}</b><small className="m-dim">{s.why}</small>
      <span className="sp-cfg"><i>TP +{s.cfg.tp}%</i><i>SL −{s.cfg.sl}%</i><i>{Number(s.cfg.rideAt) ? `❄ +${s.cfg.rideAt}% → −${s.cfg.trail}% off peak` : '❄ no freeze'}</i><i>⏳ {s.cfg.confirm} rnd · below −{s.cfg.minDrop}%</i>{sn && <i>🏊 pool ≥ ${s.cfg.pool}K · {s.cfg.age}h+ old{Number(s.cfg.edge) ? ' · 🧠 record-backed' : ''}</i>}</span>
      <em className={`m-num ${(s.medPct || 0) >= 0 ? 'm-pos' : 'm-neg'}`} data-tip={sn ? `This WHOLE setup replayed on the last ${s.hours}h of real prices, ${s.n} cards over ${s.windows} time windows it was not tuned on: typical card ${sgn(s.medPct)}, ${s.windowsUp} of ${s.windows} windows ended up, worst card ${sgn(s.worstPct)}, about ${s.trades} buys a card (it waits in cash when nothing qualifies). ${s.profitable ? 'It ended up on the replay.' : 'It did NOT end up on this round length.'} About two days of data — evidence, not a forecast.` : `What each of these settings' own sim cards did on ${clk(d.clock)} rounds (typical card, ≥ ${s.n} sims each). ${s.upPct}% ended up. A replay of real prices, not a forecast.`}>{sgn(s.medPct)} <small>{sn ? (s.profitable ? `checked · ${s.windowsUp}/${s.windows} windows up` : 'not proven on this clock') : 'typical sim'}</small></em>
      <button type="button" className={`m-btn ${on ? 'is-on' : 'primary m-go'}`} disabled={busy || on} onClick={() => onApply(s)} data-testid={`${testid}-apply-${s.key}`}>{on ? '✓ On this card' : 'Use this'}</button></article>; })}</div>
    {d.note && <small className="m-dim">{d.note}</small>}</div>;
}
