import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';

// FeeCat HQ: her live state in one strip — running / napping (and why), 9 lives, size mode, edge, open positions.
// Same /profile data as the rest of her page; refreshes every 20s while visible.
const sol = v => (v == null ? '—' : `${v >= 0 ? '+' : ''}${Number(v).toFixed(Math.abs(v) >= 1 ? 2 : 4)} SOL`);

export function livesRow(lives = 9, max = 9) {
  return Array.from({ length: max }, (_, i) => i < lives);
}

export function FeeCatHQ({ catId = 'leader' }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => fetch(apiUrl(`/api/cats/${catId}/profile`)).then(r => (r.ok ? r.json() : null)).then(x => alive && x && setD(x)).catch(() => {});
    load(); const t = setInterval(() => !document.hidden && load(), 20000);
    return () => { alive = false; clearInterval(t); };
  }, [catId]);
  if (!d) return null;
  const c = d.cat || {}; const disc = d.discipline || {};
  const napping = disc.pause || c.status === 'paused';
  const mode = disc.sizeMult === 0 ? 'no new trades' : disc.sizeMult < 1 ? `${disc.sizeMult}× size` : disc.sizeMult > 1 ? `${disc.sizeMult}× size · edge` : 'normal size';
  return <section className="m-card m-live feecat-hq" data-testid="feecat-hq">
    <div className="fhq-top"><span className={`m-chip ${napping ? 'warn' : 'ok'}`}>{napping ? '😴 napping' : '🟢 hunting'}</span>
      <b className="fhq-why">{disc.why || (napping ? 'Paused by the team.' : 'Reading every live pair — waits for real buy pressure.')}</b></div>
    <div className="fhq-lives" aria-label={`${disc.lives ?? 9} of ${disc.maxLives ?? 9} lives`} data-testid="feecat-lives">
      {livesRow(disc.lives ?? 9, disc.maxLives ?? 9).map((on, i) => <i key={i} className={on ? 'on' : ''}>🐾</i>)}<small>{disc.lives ?? 9}/9 lives · a loss costs one, a win gives one back · 0 = nap</small></div>
    <div className="m-row fhq-kpis">
      <div className="m-stat"><small>BALANCE</small><b className="m-num sm">{Number(c.balanceSol || 0).toFixed(3)} SOL</b></div>
      <div className="m-stat"><small>REALIZED</small><b className={`m-num sm ${c.realizedPnlSol >= 0 ? 'm-pos' : 'm-neg'}`}>{sol(c.realizedPnlSol)}</b></div>
      <div className="m-stat"><small>WIN RATE · LAST {disc.trades || 0}</small><b className="m-num sm">{disc.winRate ?? c.winRate ?? 0}%</b></div>
      <div className="m-stat"><small>EDGE / TRADE</small><b className={`m-num sm ${disc.expectancySol >= 0 ? 'm-pos' : 'm-neg'}`}>{sol(disc.expectancySol)}</b></div>
      <div className="m-stat"><small>SIZE MODE</small><b className="m-num sm">{mode}</b></div>
      <div className="m-stat"><small>OPEN</small><b className="m-num sm">{(c.positions || []).length}</b></div>
    </div>
  </section>;
}
