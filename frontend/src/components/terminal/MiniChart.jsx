import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';

// Mini 5m chart for a card's back: one request when shown (server caches candles 20s), closes as a sparkline.
export function sparkPath(closes, w = 200, h = 70) {
  const v = closes.filter(x => x > 0); if (v.length < 2) return '';
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || hi || 1;
  return v.map((c, i) => `${i ? 'L' : 'M'}${((i / (v.length - 1)) * w).toFixed(1)},${(h - ((c - lo) / span) * (h - 6) - 3).toFixed(1)}`).join(' ');
}

export function MiniChart({ pair }) {
  const [closes, setCloses] = useState(null);
  useEffect(() => {
    let alive = true;
    fetch(apiUrl(`/api/candles/${pair.chainId}/${pair.pairAddress}?interval=5m`)).then(r => (r.ok ? r.json() : null))
      .then(d => alive && setCloses((d?.candles || []).slice(-48).map(c => Number(c[4])))).catch(() => alive && setCloses([]));
    return () => { alive = false; };
  }, [pair.chainId, pair.pairAddress]);
  if (!closes) return <div className="mini-chart is-loading"><span className="loader" /></div>;
  const d = sparkPath(closes); const up = closes.length > 1 && closes[closes.length - 1] >= closes[0];
  const chg = closes.length > 1 && closes[0] > 0 ? ((closes[closes.length - 1] / closes[0] - 1) * 100) : null;
  return <div className={`mini-chart ${up ? 'up' : 'down'}`} data-testid="mini-chart">
    {d ? <svg viewBox="0 0 200 70" preserveAspectRatio="none" aria-label="Last 4 hours, 5 minute candles"><path d={`${d} L200,70 L0,70 Z`} className="mc-area" /><path d={d} className="mc-line" /></svg> : <small className="m-dim">No candles yet</small>}
    <small className="m-mono">4h · 5m{chg != null ? ` · ${chg >= 0 ? '+' : ''}${chg.toFixed(1)}%` : ''}</small></div>;
}
