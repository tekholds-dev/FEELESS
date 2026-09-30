import { useEffect, useRef, useState } from 'react';
import { apiUrl } from './api';

// Live swaps for a pool. `fresh` = real buys/sells that landed after the last DexScreener
// snapshot (reset whenever the snapshot's counts change), so window counters tick per trade.
export function useTradeStream(pair) {
  const [trades, setTrades] = useState([]);
  const [fresh, setFresh] = useState({ buys: 0, sells: 0, buyUsd: 0, sellUsd: 0 });
  const seen = useRef(new Set());
  const mine = useRef([]);   // your confirmed trades on this coin, shown at once (the public feed can lag a minute)
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
        const inFeed = new Set(list.map(t => t.tx));
        mine.current = mine.current.filter(t => !inFeed.has(t.tx) && Date.now() - Date.parse(t.ts) < 5 * 60000);
        setTrades([...mine.current, ...list].slice(0, 40));
      } catch {
        // keep last tape
      }
    };
    load();
    const t = setInterval(load, 4000);
    // Your own FEELESS trade on this coin lands on the tape the moment it confirms.
    const base = pair?.baseToken?.address;
    const onTrade = e => {
      const d = e.detail || {};
      if (!d.signature || !base || (d.mint && d.mint !== base)) return;
      const row = { tx: d.signature, kind: d.side === 'sell' ? 'sell' : 'buy', usd: Number(d.usd) || 0, price: Number(pair?.priceUsd) || 0, wallet: d.wallet || '', ts: new Date().toISOString(), mine: true };
      mine.current = [row, ...mine.current.filter(x => x.tx !== row.tx)];
      setTrades(list => [row, ...list.filter(x => x.tx !== row.tx)].slice(0, 40));
      setTimeout(load, 5000);
    };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [pair?.chainId, pair?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  return { trades, fresh };
}
