import { useEffect, useState } from 'react';
import { apiUrl } from '../lib/api';

// Total value of the connected wallet (SOL + tokens, USD), refreshed every 60s and after any trade.
export function useWalletTotal(address) {
  const [total, setTotal] = useState(null);
  useEffect(() => {
    if (!address) { setTotal(null); return undefined; }
    let alive = true;
    const load = fresh => fetch(apiUrl(`/api/reputation/portfolio/${address}${fresh === true ? '?fresh=1' : ''}`)).then(r => (r.ok ? r.json() : null)).then(d => { if (alive && d && d.totalUsd != null) setTotal(Number(d.totalUsd)); }).catch(() => {});
    load(); const t = setInterval(load, 60000);
    const onTrade = () => { setTimeout(() => load(true), 2500); setTimeout(() => load(true), 9000); };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => { alive = false; clearInterval(t); window.removeEventListener('feeless:trade-confirmed', onTrade); };
  }, [address]);
  return total;
}
export const fmtTotal = v => (v == null ? '' : v >= 1e6 ? `$${(v / 1e6).toFixed(2)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${v.toFixed(2)}`);
