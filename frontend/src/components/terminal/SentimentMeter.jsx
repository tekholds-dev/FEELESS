import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { Explain } from '../Explain';

// Bulls vs Bears: the coin's community mood from its own chat rooms over the last 24h.
export function SentimentMeter({ pair }) {
  const [d, setD] = useState(null);
  useEffect(() => {
    if (!pair?.chainId || !pair?.pairAddress) return undefined;
    let alive = true;
    const load = () => fetch(apiUrl(`/api/reputation/room-sentiment/${pair.chainId}/${pair.pairAddress}`)).then(r => (r.ok ? r.json() : null)).then(x => alive && setD(x)).catch(() => {});
    load(); const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [pair?.chainId, pair?.pairAddress]);
  if (!d?.bulls || !d?.bears) return null;
  const pct = d.bullPct;
  return <div className="sentiment-meter" data-testid="sentiment-meter">
    <span className="sm-label">🐂 {d.bulls.posts}</span>
    <div className="sm-bar" aria-label={pct == null ? 'No votes yet' : `${pct}% bullish`}><i style={{ width: `${pct ?? 50}%` }} className={pct == null ? 'empty' : ''} /></div>
    <span className="sm-label">{d.bears.posts} 🐻</span>
    <b className={pct == null ? '' : pct >= 50 ? 'positive' : 'negative'}>{pct == null ? 'No mood yet' : `${pct}% bull`}</b>
    <Explain>Community mood from this coin's Bulls and Bears chat rooms in the last 24 hours. Each post counts once and each different wallet counts twice more, so one loud poster can't swing it. Post in Bulls or Bears below to vote with your words.</Explain>
  </div>;
}
