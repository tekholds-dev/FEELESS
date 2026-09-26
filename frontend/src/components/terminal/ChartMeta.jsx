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

export function ChartMetaButtons({ pair, calls, setCalls, fee, setFee, fullscreenRef, count, onExpand, expanded }) {
  const mint = pair?.baseToken?.address;
  const full = () => {
    if (onExpand) { onExpand(); return; }
    const el = fullscreenRef?.current;
    if (!el) return;
    if (document.fullscreenElement) { document.exitFullscreen?.(); return; }
    if (el.classList.contains('chart-pseudo-full')) { el.classList.remove('chart-pseudo-full'); document.body.classList.remove('has-pseudo-full'); window.dispatchEvent(new Event('resize')); return; }
    const fallback = () => { el.classList.add('chart-pseudo-full'); document.body.classList.add('has-pseudo-full'); window.dispatchEvent(new Event('resize')); toast('Press Esc or the expand button again to exit.'); };
    if (el.requestFullscreen) el.requestFullscreen().catch(fallback); else fallback();
  };
  React.useEffect(() => {
    const onKey = e => { if (e.key === 'Escape') { document.querySelectorAll('.chart-pseudo-full').forEach(n => n.classList.remove('chart-pseudo-full')); document.body.classList.remove('has-pseudo-full'); window.dispatchEvent(new Event('resize')); } };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);
  const prevCounts = React.useRef({});
  React.useEffect(() => {
    // Tell the user when an overlay is on but there is genuinely nothing to plot yet.
    const t = setTimeout(() => {
      if (calls && count?.calls === 0 && !prevCounts.current.callsWarned) { toast('No Trenches calls on this coin yet — post its CA to start the ledger.'); prevCounts.current.callsWarned = true; }
      if (fee && count?.fee === 0 && !prevCounts.current.feeWarned) { toast('🐱 Fee is reading this chart live — no trades on this coin yet.'); prevCounts.current.feeWarned = true; }
    }, 2500);
    if (!calls) prevCounts.current.callsWarned = false;
    if (!fee) prevCounts.current.feeWarned = false;
    return () => clearTimeout(t);
  }, [calls, fee, count?.calls, count?.fee]);
  const copy = async () => { try { await navigator.clipboard.writeText(mint); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <div className="chart-meta-buttons" role="group" aria-label="Chart overlays">
    <button type="button" className={calls ? 'active calls' : ''} onClick={() => setCalls(v => !v)} title="Show every Trenches call on this coin" data-testid="chart-meta-calls"><Megaphone size={12} />Calls{calls && count?.calls ? ` ${count.calls}` : ''}</button>
    {pair?.chainId === 'solana' && <button type="button" className={fee ? 'active fee' : ''} onClick={() => setFee(v => !v)} title="Fee live mode: levels, liquidity, live read and Fee's trades" data-testid="chart-meta-fee"><Cat size={12} />Fee{fee && count?.fee ? ` ${count.fee}` : ''}</button>}
    <button type="button" className={expanded ? 'active expand' : ''} onClick={full} title={onExpand ? (expanded ? 'Back to chart + chat side by side' : 'Wide chart — chat moves below') : 'Fullscreen chart'} data-testid="chart-meta-fullscreen"><Maximize2 size={12} />{onExpand ? (expanded ? 'Wide on' : 'Wide') : ''}</button>
    {mint && <button type="button" onClick={copy} title="Copy contract address" data-testid="chart-meta-copy"><Copy size={12} /></button>}
  </div>;
}
