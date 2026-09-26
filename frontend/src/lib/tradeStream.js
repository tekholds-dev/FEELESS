import { useEffect, useRef, useState } from 'react';
import { apiUrl } from './api';

// Live swaps for a pool. `fresh` = real buys/sells that landed after the last DexScreener
// snapshot (reset whenever the snapshot's counts change), so window counters tick per trade.
export function useTradeStream(pair) {
  const [trades, setTrades] = useState([]);
  const [fresh, setFresh] = useState({ buys: 0, sells: 0, buyUsd: 0, sellUsd: 0 });
  const seen = useRef(new Set());
  const baseline = useRef(null);
  const snapKey = JSON.stringify(pair?.txns?.m5 || null);
  useEffect(() => { baseline.current = Date.now(); setFresh({ buys: 0, sells: 0, buyUsd: 0, sellUsd: 0 }); }, [snapKey]);
  useEffect(() => {
    if (!pair?.pairAddress || !pair?.chainId) return undefined;
    let alive = true;
    seen.current = new Set();
    const load = async () => {
      if (document.hidden) return;
      try {
        const res = await fetch(apiUrl(`/api/candles/trades/${pair.chainId}/${pair.pairAddress}`));
        const body = await res.json();
        const list = body?.trades || [];
        if (!alive || !list.length) return;
        const first = seen.current.size === 0;
        const add = { buys: 0, sells: 0, buyUsd: 0, sellUsd: 0 };
        list.forEach(t => {
          if (seen.current.has(t.tx)) return;
          seen.current.add(t.tx);
          if (first || !baseline.current || Date.parse(t.ts) < baseline.current - 2000) return;
          if (t.kind === 'buy') { add.buys += 1; add.buyUsd += t.usd; } else { add.sells += 1; add.sellUsd += t.usd; }
        });
        if (add.buys || add.sells) setFresh(f => ({ buys: f.buys + add.buys, sells: f.sells + add.sells, buyUsd: f.buyUsd + add.buyUsd, sellUsd: f.sellUsd + add.sellUsd }));
        setTrades(list.slice(0, 40));
      } catch {
        // keep last tape
      }
    };
    load();
    const t = setInterval(load, 4000);
    return () => { alive = false; clearInterval(t); };
  }, [pair?.chainId, pair?.pairAddress]);
  return { trades, fresh };
}
