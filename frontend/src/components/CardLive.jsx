import React, { useEffect, useRef, useState } from 'react';
import { cardActivity } from '../lib/cardActivity';
import '../styles/cardLive.css';

// 🫀 CARD LIVE — every Fuse card breathes with its own coins (owner: "live animations and effects based on card activity, no lag").
// Two overlay layers inside `.fcd` (never the card's own DOM): BACK = an edge ring that beats faster the harder its coins move, tinted by
// direction (green up · pink down · violet flat · ice when every coin is locked); FRONT = sparks rising (or falling) with the heat, a
// one-shot sweep each time the card's value changes, a scan line while a coin is being bought, and ONE chip naming the hottest coin.
// transform + opacity only; `.clv` is an fxPause surface (paused off-screen); lite mode / reduced motion keep only the still tint.
export function CardLive({ legs, pnlPct, value }) {
  const a = cardActivity(legs, pnlPct);
  const last = useRef(value); const [tick, setTick] = useState(null);
  useEffect(() => {
    const v = Number(value); const p = Number(last.current);
    if (Number.isFinite(v) && Number.isFinite(p) && Math.abs(v - p) >= 0.005) setTick({ k: `${v.toFixed(2)}-${Date.now()}`, up: v > p });
    last.current = value;
  }, [value]);
  const tone = a.locked ? 'ice' : a.dir;
  const cls = `clv ${{ up: 'is-up', down: 'is-down', ice: 'is-ice' }[tone] || 'is-flat'} ${['h0', 'h1', 'h2', 'h3'][a.heat]}${a.buying ? ' is-buying' : ''}`;   // literal class names (cssHygiene reads them)
  return <>
    <span className={`${cls} clv-back`} aria-hidden="true" style={{ '--beat': `${a.beat}s` }} data-testid="card-live" data-heat={a.word} data-dir={tone}><i className="clv-ring" /><i className="clv-glow" /></span>
    <span className={`${cls} clv-front`} aria-hidden="true">
      {Array.from({ length: a.sparks }, (_, i) => <i key={i} className="clv-spark" style={{ '--i': i, left: `${(i * 37 + 9) % 100}%` }} />)}
      {a.buying && <i className="clv-scan" />}
      {tick && <i key={tick.k} className={`clv-tick ${tick.up ? 'up' : 'down'}`} />}
      {a.top && <b className={`clv-chip ${a.top.m5 >= 0 ? 'up' : 'down'}`} key={a.top.symbol}>{a.heat >= 3 ? '🔥' : '⚡'} ${a.top.symbol} {a.top.m5 >= 0 ? '+' : ''}{Math.abs(a.top.m5) >= 100 ? Math.round(a.top.m5) : a.top.m5.toFixed(1)}% <small>5m</small></b>}
    </span>
  </>;
}

export default CardLive;
