import React, { useMemo } from 'react';
import { STAKES, setStake, useStake, cash } from '../lib/earnStake';
import { useGlide } from '../lib/useGlide';
import '../styles/earnStake.css';

// 💸 WHAT YOUR MONEY DOES HERE (owner, 2026-10-23: "pools + perps must earn … what $5 / $100 earns, live"):
// · StakeSeg — the one stake picker ($5 · $100 · $1K) every Pool Hall row + the Perps desk quote at.
// · PerpsEarn — the Perps desk's money read for the picked market at your stake × leverage: the position, $ per 1 % move, the funding that
//   pays one side every day, the move that liquidates it, and a drawn P&L fan (−10 % … +10 %) with the wipe-out zone marked. Math only — the
//   venue (Kraken Pro / Coinbase for US traders) runs the order; FEELESS never holds the margin.
export function StakeSeg({ label = 'IF YOU PUT IN' }) {
  const v = useStake();
  return <span className="es-seg" data-testid="stake-seg"><em>{label}</em><span className="m-seg" role="radiogroup" aria-label="Stake">{STAKES.map(s => <button key={s} type="button" role="radio"
    aria-checked={v === s} className={v === s ? 'active' : ''} onClick={() => setStake(s)} data-tip={`Quote every earning on this page at $${s.toLocaleString('en-US')}`} data-testid={`stake-${s}`}>${s >= 1000 ? `${s / 1000}K` : s}</button>)}</span></span>;
}

const MOVES = [-10, -5, -2, -1, 1, 2, 5, 10];
// pure: one perps market at a stake × leverage → position, $ per 1 % move, funding a day (who earns it), the liquidation move, the P&L fan
export function perpsMath(stake, lev, row) {
  const pos = stake * lev; const fund = Number(row?.fundApr) || 0; const fundDay = (pos * Math.abs(fund)) / 100 / 365;
  return { pos, per1: pos / 100, fundDay, fundYear: fundDay * 365, earner: fund > 0 ? 'SHORTS' : fund < 0 ? 'LONGS' : null, liq: 100 / lev,
    fan: MOVES.map(m => { const pnl = (pos * m) / 100; return { m, pnl: Math.max(-stake, pnl), wiped: pnl <= -stake }; }) };
}

function Glide({ v, sign = false }) { const g = useGlide(Math.round(v * 10000) / 10000); return <b className="m-num" key={Math.round(v * 100)}>{sign && g > 0 ? '+' : ''}{cash(g)}</b>; }

export function PerpsEarn({ row, lev }) {
  const stake = useStake();
  const m = useMemo(() => perpsMath(stake, lev, row), [stake, lev, row]);
  if (!row) return null;
  const top = Math.max(...m.fan.map(f => Math.abs(f.pnl)), 0.01);
  return <div className="es-perps" data-testid="perps-earn">
    <header><span><em>YOUR MONEY ON</em><b>{row.coin} PERP</b><small>${stake.toLocaleString('en-US')} × {lev}× = {cash(m.pos)} position</small></span><StakeSeg label="MARGIN" /></header>
    <div className="es-tiles">
      <span className="es-tile is-up" style={{ '--i': 0 }} data-tip={`Every 1% ${row.coin} moves your way pays this; the other way costs it`}><em>PER 1% MOVE</em><Glide v={m.per1} /><small>long up · short down</small></span>
      <span className={`es-tile ${m.earner ? 'is-gold' : ''}`} style={{ '--i': 1 }} data-tip={`Funding at ${row.fundApr > 0 ? '+' : ''}${row.fundApr}% a year: ${m.earner ? `${m.earner.toLowerCase()} collect it from the other side every day they hold` : 'flat right now'}`}>
        <em>FUNDING / DAY</em><Glide v={m.fundDay} /><small>{m.earner ? `${m.earner} EARN · ${cash(m.fundYear)} / yr` : 'flat'}</small></span>
      <span className="es-tile is-down" style={{ '--i': 2 }} data-tip="How far the price can go against you before the venue closes the position (before fees)"><em>WIPED AT</em><b className="m-num">{m.liq.toFixed(1)}%</b><small>against you · lose {cash(stake)}</small></span>
    </div>
    <svg className="es-fan" viewBox="0 0 320 120" aria-label={`A long's result at ${lev}× for moves from −10% to +10%`}>
      <line x1="10" x2="310" y1="60" y2="60" className="es-zero" />
      {m.fan.map((f, i) => { const h = (Math.abs(f.pnl) / top) * 48; const x = 14 + i * 37; const up = f.pnl >= 0;
        return <g key={f.m} className={`es-bar ${up ? 'is-up' : f.wiped ? 'is-wiped' : 'is-down'}`} style={{ '--i': i }}>
          <rect x={x} y={up ? 60 - h : 60} width="26" height={Math.max(1.5, h)} rx="3" />
          <text x={x + 13} y={up ? 60 - h - 4 : 60 + h + 10} textAnchor="middle" className="es-val">{f.wiped ? 'WIPED' : `${up ? '+' : '−'}${cash(Math.abs(f.pnl))}`}</text>
          <text x={x + 13} y={up ? 74 : 52} textAnchor="middle" className="es-mv">{`${f.m > 0 ? '+' : ''}${f.m}%`}</text></g>; })}
    </svg>
    <p className="es-foot">A long at {lev}×: every bar is the move → your result. {m.earner ? `Right now ${m.earner.toLowerCase()} are paid ${cash(m.fundDay)} a day to hold ${cash(m.pos)}.` : ''} The venue runs the order — FEELESS never holds your margin.</p>
  </div>;
}
