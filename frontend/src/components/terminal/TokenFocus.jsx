import { QuickTrade } from './QuickTrade';
import { EdgeScore } from './EdgeScore';
import { LivePrice, LiveChange24, LiveMarketCap } from './LiveCells';
import React, { useEffect, useRef, useState } from 'react';
import { ChartMetaButtons, useChartMarkers } from './ChartMeta';
import { LaunchForensics } from './LaunchForensics';
import { Copy, ExternalLink, Rocket, Star, BarChart3, ArrowUpRight, ArrowLeftRight } from 'lucide-react';
import { toast } from 'sonner';
import { PriceChart } from './PriceChart';
import { ChartBoundary } from './ChartBoundary';
import { useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../hooks/useWorkspace';
import { Change, Metric, TokenAvatar, DataStatus, MarketAvailabilityNotice, MarketError, TokenContextMeta, CreatorProfile } from './MarketPrimitives';
import { dexUrl, shortAddress, formatAge } from '../../lib/dexscreener';
import { useMarket } from '../../hooks/useMarket';

export const TokenFocus = ({ pair, has, toggle, defaultInterval = '1h', onExpand, expanded }) => {
  const [interval, setInterval] = useState(defaultInterval);
  const [metric, setMetric] = useState('price');
  const nav = useNavigate(); const { selectPair } = useWorkspace();
  const [volume, setVolume] = useState(true);
  const [showCalls, setShowCalls] = useState(false);
  const [showFee, setShowFee] = useState(false);
  const chartWrap = useRef(null);
  const live = useMarket(pair ? `/pair/${pair.chainId}/${pair.pairAddress}` : null, 3000);
  const livePair = live.data?.pairs?.[0];
  const current = livePair ? {
    ...pair,
    ...livePair,
    signals: { ...(pair?.signals || {}), ...(livePair.signals || {}) },
    rankingContext: { ...(pair?.rankingContext || {}), ...(livePair.rankingContext || {}) },
  } : pair;
  useEffect(() => { setMetric('price'); }, [current?.chainId, current?.pairAddress]);
  const markers = useChartMarkers(current, { calls: showCalls, fee: showFee });
  if (!current) return <section className="empty-focus" data-testid="token-focus-empty"><BarChart3 size={32} /><p>Select a market to open its chart.</p></section>;
  const address = current.baseToken?.address;
  const metricValue = id => id === 'marketCap' ? current.marketCap : current.fdv;
  const metricAvailable = id => metricValue(id) !== null && metricValue(id) !== undefined && metricValue(id) !== '' && Number.isFinite(Number(metricValue(id)));
  const METRIC_LABEL = { price: 'Price', marketCap: 'Market cap', fdv: 'FDV' };
  const availableMetrics = ['price', 'marketCap', 'fdv'].filter(id => id === 'price' || metricAvailable(id));
  const cycleMetric = () => {
    const idx = availableMetrics.indexOf(metric);
    setMetric(availableMetrics[(idx + 1) % availableMetrics.length]);
  };
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <section className="token-focus" data-testid="token-focus">
     <div className="focus-header"><TokenAvatar pair={current} size={46} /><div className="token-heading"><h2 data-testid="selected-token-symbol">{current.baseToken?.symbol}<span>/ {current.quoteToken?.symbol || 'USD'}</span></h2><div className="token-sub"><span data-testid="selected-token-chain">{current.chainId}</span><span>·</span><span data-testid="selected-token-dex">{current.dexId}</span><button onClick={copy} title="Copy contract address" data-testid="copy-selected-contract">{shortAddress(address)}<Copy size={11} /></button></div><TokenContextMeta pair={current} /></div><button title={has(current) ? 'Remove from watchlist' : 'Add to watchlist'} onClick={() => toggle(current)} className={`icon-btn ${has(current) ? 'is-saved' : ''}`} data-testid="selected-token-watchlist"><Star size={17} fill={has(current) ? 'currentColor' : 'none'} /></button></div>
    <MarketAvailabilityNotice data={live.data} error={live.error} errorStatus={live.errorStatus} errorProvider={live.errorProvider} id="token-market-availability" />
    {live.error && <MarketError error={`${live.error} Showing the discovery snapshot.`} reload={live.reload} id="token-refresh-error" />}
    <div className="token-metrics"><div className="metric"><small>Price USD</small><strong className="mono"><LivePrice pair={current} precise id="selected-token-price" /></strong></div><div className="metric"><small>24h change</small><LiveChange24 pair={current} id="selected-token-change" /></div><div className="metric"><small>{current.marketCap != null ? 'Market cap' : 'FDV'}</small><strong className="mono"><LiveMarketCap pair={current} id="selected-token-mcap" /></strong></div><Metric label="24h volume" value={current.volume?.h24} id="selected-token-volume" /><Metric label="Liquidity" value={current.liquidity?.usd} id="selected-token-liquidity" /></div>
     <div className="chart-toolbar"><button type="button" className="chart-metric-switch" title={`Showing ${METRIC_LABEL[metric]} · click to switch (${availableMetrics.map(id => METRIC_LABEL[id]).join(' → ')})`} data-testid="chart-metric-switch" onClick={cycleMetric} disabled={availableMetrics.length < 2}><ArrowLeftRight size={13} /><span data-testid="chart-metric-active">{METRIC_LABEL[metric]}</span></button><div className="timeframes">{['1m', '5m', '15m', '1h', '4h', '1d'].map(t => <button className={t === interval ? 'active' : ''} data-testid={`chart-interval-${t}`} key={t} onClick={() => setInterval(t)}>{t.toUpperCase()}</button>)}</div><button className={`volume-control ${volume ? 'positive' : ''}`} title="Toggle volume bars" data-testid="chart-volume-toggle" onClick={() => setVolume(v => !v)}><BarChart3 size={13} /><span>Volume</span></button><ChartMetaButtons pair={current} calls={showCalls} setCalls={setShowCalls} fee={showFee} setFee={setShowFee} fullscreenRef={chartWrap} onExpand={onExpand} expanded={expanded} count={{ calls: markers.filter(m => m.color === '#e9bd65').length, fee: markers.filter(m => m.text?.startsWith('Fee')).length }} /><a title="Open advanced chart" data-testid="chart-advanced-link" href={dexUrl(current)} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a></div>
     <div className="chart-with-trade"><div className="chart-fullscreen-wrap" ref={chartWrap}><ChartBoundary key={`${current.chainId}-${current.pairAddress}-${interval}-${metric}`} pair={current}><PriceChart pair={current} interval={interval} metric={metric} showVolume={volume} markers={markers} /></ChartBoundary></div><QuickTrade pair={current} /></div>
     <div className="focus-meta"><span data-testid="selected-token-age">Pool age {formatAge(current.pairCreatedAt)}</span><CreatorProfile pair={current} /><DataStatus data={live.data} id="token-data-status" /></div>
     <EdgeScore pair={current} />
     <LaunchForensics pair={current} />
    <div className="token-actions"><button className="primary-action" data-testid="selected-token-trade-inapp" onClick={() => { selectPair(current); nav('/terminal/trade'); }}><ArrowUpRight size={19} /><span>Trade in FEELESS<small>{current.chainId === 'solana' ? 'Jupiter execution' : 'Network status'}</small></span><ArrowUpRight size={14} /></button>{current.chainId === 'solana' && /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address || '') && <a href={`https://pump.fun/coin/${address}`} target="_blank" rel="noopener noreferrer" data-testid="selected-token-pump-link"><Rocket size={19} /><span>View on Pump<small>External token page</small></span><ArrowUpRight size={14} /></a>}<a href={dexUrl(current)} target="_blank" rel="noreferrer" data-testid="selected-token-dex-link"><BarChart3 size={19} /><span>View on DEX<small>Chart & transactions</small></span><ArrowUpRight size={14} /></a></div>
  </section>;
};