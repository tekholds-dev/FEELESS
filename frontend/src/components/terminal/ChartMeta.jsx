import React, { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Copy, Maximize2, Megaphone, Cat } from 'lucide-react';
import { apiUrl } from '../../lib/api';
import { formatUSD } from '../../lib/dexscreener';

// Chart overlays: Trenches calls and Fee's paper trades on this exact pair, as chart markers.
export function useChartMarkers(pair, { calls, fee }) {
  const [markers, setMarkers] = useState([]);
  useEffect(() => {
    if (!pair?.pairAddress || (!calls && !fee)) { setMarkers([]); return undefined; }
    let alive = true;
    const load = async () => {
      const out = [];
      if (calls) {
        try {
          const d = await (await fetch(apiUrl(`/api/reputation/calls/recent?pair=${pair.pairAddress}&limit=100`))).json();
          (d.calls || []).forEach(c => out.push({ time: Math.floor(c.at), position: 'belowBar', shape: 'arrowUp', color: '#e9bd65', text: `${c.caller} @ ${formatUSD(c.mcAtCall)}` }));
        } catch { /* no calls overlay */ }
      }
      if (fee) {
        try {
          const d = await (await fetch(`/api/cats/trades?pairAddress=${encodeURIComponent(pair.pairAddress)}`)).json();
          (d.trades || []).forEach(t => out.push({ time: Math.floor(t.ts / 1000), position: t.type === 'BUY' ? 'belowBar' : 'aboveBar', shape: t.type === 'BUY' ? 'arrowUp' : 'arrowDown', color: t.type === 'BUY' ? '#00e9a0' : '#fa708c', text: `Fee ${t.type === 'BUY' ? 'buy' : 'sell'}` }));
        } catch { /* no fee overlay */ }
      }
      if (alive) setMarkers(out);
    };
    load();
    const t = setInterval(load, 30000);
    return () => { alive = false; clearInterval(t); };
  }, [pair?.pairAddress, calls, fee]);
  return markers;
}

export function ChartMetaButtons({ pair, calls, setCalls, fee, setFee, fullscreenRef, count }) {
  const mint = pair?.baseToken?.address;
  const full = () => {
    const el = fullscreenRef?.current;
    if (!el) return;
    if (document.fullscreenElement) document.exitFullscreen?.();
    else el.requestFullscreen?.().catch(() => toast.error('Fullscreen is blocked in this browser.'));
  };
  const copy = async () => { try { await navigator.clipboard.writeText(mint); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <div className="chart-meta-buttons" role="group" aria-label="Chart overlays">
    <button type="button" className={calls ? 'active calls' : ''} onClick={() => setCalls(v => !v)} title="Show every Trenches call on this coin" data-testid="chart-meta-calls"><Megaphone size={12} />Calls{calls && count?.calls ? ` ${count.calls}` : ''}</button>
    {pair?.chainId === 'solana' && <button type="button" className={fee ? 'active fee' : ''} onClick={() => setFee(v => !v)} title="Show Fee's paper buys and sells on this coin" data-testid="chart-meta-fee"><Cat size={12} />Fee{fee && count?.fee ? ` ${count.fee}` : ''}</button>}
    <button type="button" onClick={full} title="Fullscreen chart" data-testid="chart-meta-fullscreen"><Maximize2 size={12} /></button>
    {mint && <button type="button" onClick={copy} title="Copy contract address" data-testid="chart-meta-copy"><Copy size={12} /></button>}
  </div>;
}
