import { useEffect, useState } from 'react';
import { fetchFeelessCandles, cacheCandles } from './candles';

// 👁 The LIVE 1-minute candles of one pool — the same request (and in-flight sharing) the war room chart makes, re-read every `everyMs`.
// For surfaces that cannot host the chart component itself (the 3D room's wall screen draws them on a canvas).
export function useLiveCandles(pair, mint, everyMs = 10000, keep = 60) {
  const [live, setLive] = useState(null);
  useEffect(() => {
    setLive(null);
    if (!pair) return undefined;
    let alive = true;
    const read = () => fetchFeelessCandles('solana', pair, '1m', undefined, mint)
      .then(res => { if (!alive) return; cacheCandles('solana', pair, '1m', res); const rows = (res?.candles || []).slice(-keep); if (rows.length) setLive({ pair, rows, at: Date.now(), provider: res.provider }); })
      .catch(() => {});
    read();
    const t = setInterval(() => { if (!document.hidden) read(); }, everyMs);
    return () => { alive = false; clearInterval(t); };
  }, [pair, mint, everyMs, keep]);
  return live && live.pair === pair ? live : null;
}
