// The trench chart: one component for every place a coin is charted (trenches, globe war room, …).
// Toolbar (metric, timeframes, volume, calls/fee markers, fullscreen, alert, advanced), your live P&L badge,
// your own buys/sells pinned on the candles, and the trade side stack (Quick trade, Dip/Rip, rug shield).
import React, { useMemo, useEffect, useRef, useState } from 'react';
import { ArrowLeftRight, BarChart3, ExternalLink } from 'lucide-react';
import { dexUrl } from '../../lib/dexscreener';
import { ShieldBadge } from '../Shield';
import { ChartMetaButtons, useChartMarkers } from './ChartMeta';
import { PriceChart } from './PriceChart';
import { ChartBgPicker } from './ChartBg';
import { openMiniChart } from '../MiniChart';
import { ChartBoundary } from './ChartBoundary';
import { PriceAlertButton } from './PriceAlertButton';
import { DipRipTool } from './DipRipTool';
import { QuickTrade } from './QuickTrade';
import { TradeTape } from './TradeTape';
import { useTabTitle, chartTitle } from '../../lib/tabTitle';
import { useLiveFuse } from '../../lib/liveFuse';
import { useMyPosition, PnlBadge } from './ChartPnl';
import { useAdmin } from '../../lib/adminCall';
import { toast } from 'sonner';

import { tiny } from '../../lib/num';
const METRIC_LABEL = { price: 'Price', marketCap: 'Market cap', fdv: 'FDV' };

// aside: something to sit beside the chart (the war room puts the coin chat there); the trade tools then go below
// the chart in a row instead of a scrolling side column.
export function TrenchChart({ pair: current, defaultInterval = '1m', onExpand, expanded, className = '', aside = null }) {
  const [interval, setInterval] = useState(defaultInterval);
  const [metric, setMetric] = useState('marketCap');
  useTabTitle(chartTitle(current));   // 🏷 the browser tab reads this coin's market cap + price while its chart is open
  const [volume, setVolume] = useState(true);
  const [showCalls, setShowCalls] = useState(false);
  const [showFee, setShowFee] = useState(false);
  const chartWrap = useRef(null);
  useEffect(() => { setMetric(Number(current?.marketCap) > 0 ? 'marketCap' : 'price'); }, [current?.chainId, current?.pairAddress]); // eslint-disable-line react-hooks/exhaustive-deps
  const metaMarkers = useChartMarkers(current, { calls: showCalls, fee: showFee });
  const [myPos, tradeFlash] = useMyPosition(current);
  // Your own buys and sells, pinned on the candle they happened in (gold = you).
  const markers = useMemo(() => [...metaMarkers, ...((myPos?.trades) || []).map(t => ({ time: Math.floor(t.ts), position: Number(t.fillPrice) > 0 ? (t.side === 'buy' ? 'atPriceBottom' : 'atPriceTop') : t.side === 'buy' ? 'belowBar' : 'aboveBar', price: Number(t.fillPrice) || undefined,
    shape: t.side === 'buy' ? 'arrowUp' : 'arrowDown', color: t.side === 'buy' ? '#f5c451' : '#ff8fa3', text: `YOU ${t.side === 'buy' ? 'BUY' : 'SELL'} $${Number(t.usd || 0).toFixed(t.usd >= 100 ? 0 : 2)}${t.pnlUsd != null ? ` ${t.pnlUsd >= 0 ? '+' : '−'}$${Math.abs(t.pnlUsd).toFixed(2)}` : ''} ✓` }))], [metaMarkers, myPos]);
  // ⚛ a coin opened from a Fuse card follows that card LIVE (entry / stop / lock after a rebuy, a dragged level, a new round)
  const lf = useLiveFuse(current?.fuse); const { call: adminCall } = useAdmin(); const [rebuyBusy, setRebuyBusy] = useState(false);
  const lastEntry = useRef(null);
  useEffect(() => { const e = lf.fuse?.entry; if (!e) return; if (lastEntry.current && Math.abs(e / lastEntry.current - 1) > 1e-6 && rebuyBusy) { toast.success(`🔄 Bought back — new entry $${tiny(Number(e), 4)}. Stop and lock count from here.`); setRebuyBusy(false); } lastEntry.current = e; }, [lf.fuse?.entry]);   // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { if (rebuyBusy && lf.state === 'gone') { toast.error('The rebuy did not land — the coin left the card. Its money is back in the card.'); setRebuyBusy(false); } }, [lf.state, rebuyBusy]);
  if (!current) return null;
  const fz = current.fuse ? (lf.fuse || current.fuse) : null;
  const rebuying = rebuyBusy || lf.state === 'rebuying' || lf.state === 'buying';
  const rebuy = () => { const f = fz; if (!f?.tpl || rebuying) return;
    if (!window.confirm(`Rebuy $${f.symbol}? It is sold whole now and bought straight back at today's price: a new entry, so its stop and lock count from here. Two swaps (about 1% in costs).`)) return;
    setRebuyBusy(true); lf.kick();
    adminCall('/admin/arena/prime', { method: 'POST', body: JSON.stringify({ rebuy: { tpl: f.tpl, pairAddress: f.pairAddress } }) })
      .then(() => { toast.success(`🔄 $${f.symbol} sold — buying it back at today's price`); window.dispatchEvent(new Event('feeless:prime')); })
      .catch(e => { toast.error(e.message || 'Rebuy failed'); setRebuyBusy(false); }); };
  const metricValue = id => id === 'marketCap' ? current.marketCap : current.fdv;
  const metricAvailable = id => metricValue(id) !== null && metricValue(id) !== undefined && metricValue(id) !== '' && Number.isFinite(Number(metricValue(id)));
  const availableMetrics = ['price', 'marketCap', 'fdv'].filter(id => id === 'price' || metricAvailable(id));
  const cycleMetric = () => {
    const idx = availableMetrics.indexOf(metric);
    setMetric(availableMetrics[(idx + 1) % availableMetrics.length]);
  };
  const tools = <div className={aside ? 'chart-tools-row' : 'chart-side-stack custom-scroll'} data-testid="chart-tools"><QuickTrade pair={current} /><DipRipTool pair={current} />{current.chainId === 'solana' && <ShieldBadge mint={current.baseToken?.address} />}</div>;
  return <div className={`trench-chart ${className}`} data-testid="trench-chart">
    <div className="chart-toolbar"><button type="button" className="chart-metric-switch" title={`Showing ${METRIC_LABEL[metric]} · click to switch (${availableMetrics.map(id => METRIC_LABEL[id]).join(' → ')})`} data-testid="chart-metric-switch" onClick={cycleMetric} disabled={availableMetrics.length < 2}><ArrowLeftRight size={13} /><span data-testid="chart-metric-active">{METRIC_LABEL[metric]}</span></button><div className="timeframes">{['1m', '5m', '15m', '1h', '4h', '1d'].map(t => <button className={t === interval ? 'active' : ''} data-testid={`chart-interval-${t}`} key={t} onClick={() => setInterval(t)}>{t.toUpperCase()}</button>)}</div><button className={`volume-control ${volume ? 'positive' : ''}`} title="Toggle volume bars" data-testid="chart-volume-toggle" onClick={() => setVolume(v => !v)}><BarChart3 size={13} /><span>Volume</span></button><ChartMetaButtons pair={current} calls={showCalls} setCalls={setShowCalls} fee={showFee} setFee={setShowFee} fullscreenRef={chartWrap} onExpand={onExpand} expanded={expanded} count={{ calls: markers.filter(m => m.color === '#e9bd65').length, fee: markers.filter(m => m.text?.startsWith('Fee')).length }} /><PriceAlertButton pair={current} /><ChartBgPicker /><button type="button" className="chart-mini-btn" onClick={() => openMiniChart(current)} data-testid="chart-mini" aria-label="Mini chart" data-tip="Mini chart: closes this room and keeps the chart floating on every page">📌</button><a title="Open advanced chart" data-testid="chart-advanced-link" href={dexUrl(current)} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a></div>
    {fz?.entry > 0 && <div className={`chart-fuse ${rebuying ? 'is-busy' : ''}`} data-testid="chart-fuse"><b>⚛️ {fz.card || 'Fuse card'}</b><span>entry <em>${tiny(Number(fz.entry), 4)}</em></span>
      {Number(current.priceUsd) > 0 && <span className={Number(current.priceUsd) >= fz.entry ? 'up' : 'down'}>{((Number(current.priceUsd) / fz.entry - 1) * 100).toFixed(1)}% since entry</span>}
      {fz.tpl && <button type="button" className="chart-fuse-btn" data-testid="chart-fuse-rebuy" disabled={rebuying} data-tip="Sell this coin whole and buy it straight back at today's price — a new entry, so its stop and lock count from here. Two swaps. The lines on this chart move to the new entry when it lands."
        onClick={rebuy}>{lf.state === 'rebuying' ? '🔄 sold — buying back…' : lf.state === 'buying' ? '🔄 buying back…' : rebuyBusy ? '🔄 selling…' : "🔄 Rebuy at today's price"}</button>}
      {lf.state === 'gone' && <span className="down" data-testid="chart-fuse-gone">no longer on the card</span>}
      {fz.riding ? <span>❄ riding{fz.trail ? <> · out under <em>${tiny(Number(fz.trail), 4)}</em></> : null}</span> : <>{fz.stop ? <span>🛑 stop <em>${tiny(Number(fz.stop), 4)}</em></span> : null}{fz.lock ? <span>❄ locks <em>${tiny(Number(fz.lock), 4)}</em></span> : null}</>}</div>}
    <div className="chart-with-trade"><div className="chart-fullscreen-wrap" ref={chartWrap}><PnlBadge mcPerPrice={Number(current.marketCap) > 0 && Number(current.priceUsd) > 0 ? Number(current.marketCap) / Number(current.priceUsd) : null} pos={myPos} pair={current} price={Number(current.priceUsd)} flash={tradeFlash} symbol={current.baseToken?.symbol} imageUrl={current.info?.imageUrl} /><ChartBoundary key={`${current.chainId}-${current.pairAddress}-${interval}-${metric}`} pair={current}><PriceChart userEntry={myPos?.tokensHeld > 0 ? (myPos?.fillPrice || myPos?.avgEntry) : null} userTrades={myPos?.trades} pair={current} interval={interval} metric={metric} showVolume={volume} markers={markers} feeLive={showFee} fuse={fz || null} pnl={myPos?.tokensHeld > 0 ? { pos: myPos, tagOnly: true } : false} /></ChartBoundary></div>{aside ? <div className="chart-aside">{aside}</div> : tools}</div>{aside && tools}
    <TradeTape pair={current} />
  </div>;
}
export { useMyPosition };
