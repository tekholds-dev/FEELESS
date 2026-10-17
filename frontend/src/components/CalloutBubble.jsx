import React, { useEffect, useRef, useState } from 'react';
import { useLivePrices } from '../lib/livePrices';
import { calloutLive, xWord, capWord } from '../lib/callout';
import '../styles/callout.css';

// 📣 one callout bubble, Pump style: who called it, the cap they called it at, the cap now, × since + P&L, the thesis. Live from the shared
// price poller (no fetch of its own); the number flashes when it moves; a 2×+ call lights up. `kind` ai = an OSSY / G4 call on the chart.
export function CalloutBubble({ who, sym, pair, calledMc, why, at, kind = 'user', compact = false, onOpen }) {
  const prices = useLivePrices(pair ? [pair] : []);
  const now = (pair && prices.get(pair)?.mc) || 0;
  const l = calloutLive(calledMc, now);
  const prev = useRef(l.pct); const [flash, setFlash] = useState('');
  useEffect(() => { if (l.pct != null && prev.current != null && Math.abs(l.pct - prev.current) >= 0.5) { setFlash(l.pct > prev.current ? 'is-tick-up' : 'is-tick-dn'); const t = setTimeout(() => setFlash(''), 650); prev.current = l.pct; return () => clearTimeout(t); } prev.current = l.pct; return undefined; }, [l.pct]);
  const ago = at ? Math.max(0, Math.round((Date.now() / 1000 - Number(at)) / 60)) : null;
  return <div className={`clo is-${l.tone} is-${kind} ${compact ? 'is-compact' : ''} ${l.x >= 2 ? 'is-hot' : ''} ${flash}`} data-testid="callout-bubble" role={onOpen ? 'button' : undefined} tabIndex={onOpen ? 0 : undefined}
    onClick={onOpen} onKeyDown={e => { if (onOpen && (e.key === 'Enter' || e.key === ' ')) onOpen(); }}>
    <p className="clo-top"><b>📣 {who || 'someone'}</b><span>called <em>${sym}</em> at <u>{capWord(calledMc)}</u></span>{ago != null ? <small>{ago < 60 ? `${ago}m` : `${Math.round(ago / 60)}h`} ago</small> : null}</p>
    <p className="clo-live"><strong className="clo-x">{xWord(l.x)}</strong><span className="clo-pct">{l.pct == null ? 'reading…' : `${l.pct >= 0 ? '+' : ''}${l.pct.toFixed(1)}%`}</span>
      <span className="clo-bar" aria-hidden="true"><i style={{ transform: `scaleX(${l.fill.toFixed(3)})` }} /></span><small>now {capWord(now)}</small></p>
    {why && !compact ? <p className="clo-why">{why}</p> : null}
  </div>;
}
