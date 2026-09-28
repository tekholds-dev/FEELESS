import { ShareGifButton } from '../ShareGif';
import { Explain } from '../Explain';
import { SentimentMeter } from './SentimentMeter';
import { RugProof } from '../RugProof';
import { QuickTrade } from './QuickTrade';
import { EdgeScore } from './EdgeScore';
import { LivePrice, LiveChange24, LiveMarketCap } from './LiveCells';
import { CoinAura } from '../CoinAura';
import { useCoinColor } from '../../lib/coinColor';
import { ShieldBadge } from '../Shield';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useWallet } from '../../hooks/useWallet';
import { apiUrl } from '../../lib/api';
import { ChartMetaButtons, useChartMarkers } from './ChartMeta';
import { LaunchForensics } from './LaunchForensics';
import { Copy, ExternalLink, Rocket, Star, BarChart3, ArrowUpRight, ArrowLeftRight } from 'lucide-react';
import { toast } from 'sonner';
import { PriceChart } from './PriceChart';
import { ChartBoundary } from './ChartBoundary';
import { useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../hooks/useWorkspace';
import { Metric, TokenAvatar, DataStatus, MarketAvailabilityNotice, MarketError, TokenContextMeta, CreatorProfile } from './MarketPrimitives';
import { dexUrl, shortAddress, formatAge } from '../../lib/dexscreener';
import { PriceAlertButton } from './PriceAlertButton';
import { DipRipTool } from './DipRipTool';
import { useMarket } from '../../hooks/useMarket';

export const TokenFocus = ({ pair, has, toggle, defaultInterval = '1m', onExpand, expanded }) => {
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
  const [myPos, tradeFlash] = useMyPosition(current);
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
  return <section className="token-focus has-aura" data-testid="token-focus">
    <FocusAura pair={current} />
     <div className="focus-header"><TokenAvatar pair={current} size={46} /><div className="token-heading"><h2 data-testid="selected-token-symbol">{current.baseToken?.symbol}<span>/ {current.quoteToken?.symbol || 'USD'}</span></h2>{current.chainId === 'solana' && <RugProof mint={current.baseToken?.address} />}<div className="token-sub"><span data-testid="selected-token-chain">{current.chainId}</span><span>·</span><span data-testid="selected-token-dex">{current.dexId}</span><button onClick={copy} title="Copy contract address" data-testid="copy-selected-contract">{shortAddress(address)}<Copy size={11} /></button></div><TokenContextMeta pair={current} /><SentimentMeter pair={current} /></div><button title={has(current) ? 'Remove from watchlist' : 'Add to watchlist'} onClick={() => toggle(current)} className={`icon-btn ${has(current) ? 'is-saved' : ''}`} data-testid="selected-token-watchlist"><Star size={17} fill={has(current) ? 'currentColor' : 'none'} /></button></div>
    <MarketAvailabilityNotice data={live.data} error={live.error} errorStatus={live.errorStatus} errorProvider={live.errorProvider} id="token-market-availability" />
    {live.error && <MarketError error={`${live.error} Showing the discovery snapshot.`} reload={live.reload} id="token-refresh-error" />}
    <div className="token-metrics"><div className="metric"><small>Price USD</small><strong className="mono"><LivePrice pair={current} precise id="selected-token-price" /></strong></div><div className="metric"><small>24h change</small><LiveChange24 pair={current} id="selected-token-change" /></div><div className="metric"><small>{current.marketCap != null ? 'Market cap' : 'FDV'}</small><strong className="mono"><LiveMarketCap pair={current} id="selected-token-mcap" /></strong></div><Metric label="24h volume" value={current.volume?.h24} id="selected-token-volume" /><Metric label="Liquidity" value={current.liquidity?.usd} id="selected-token-liquidity" /></div>
     <div className="chart-toolbar"><button type="button" className="chart-metric-switch" title={`Showing ${METRIC_LABEL[metric]} · click to switch (${availableMetrics.map(id => METRIC_LABEL[id]).join(' → ')})`} data-testid="chart-metric-switch" onClick={cycleMetric} disabled={availableMetrics.length < 2}><ArrowLeftRight size={13} /><span data-testid="chart-metric-active">{METRIC_LABEL[metric]}</span></button><div className="timeframes">{['1m', '5m', '15m', '1h', '4h', '1d'].map(t => <button className={t === interval ? 'active' : ''} data-testid={`chart-interval-${t}`} key={t} onClick={() => setInterval(t)}>{t.toUpperCase()}</button>)}</div><button className={`volume-control ${volume ? 'positive' : ''}`} title="Toggle volume bars" data-testid="chart-volume-toggle" onClick={() => setVolume(v => !v)}><BarChart3 size={13} /><span>Volume</span></button><ChartMetaButtons pair={current} calls={showCalls} setCalls={setShowCalls} fee={showFee} setFee={setShowFee} fullscreenRef={chartWrap} onExpand={onExpand} expanded={expanded} count={{ calls: markers.filter(m => m.color === '#e9bd65').length, fee: markers.filter(m => m.text?.startsWith('Fee')).length }} /><PriceAlertButton pair={current} /><a title="Open advanced chart" data-testid="chart-advanced-link" href={dexUrl(current)} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a></div>
     <div className="chart-with-trade"><div className="chart-fullscreen-wrap" ref={chartWrap}><PnlBadge pos={myPos} price={Number(current.priceUsd)} flash={tradeFlash} symbol={current.baseToken?.symbol} imageUrl={current.info?.imageUrl} /><ChartBoundary key={`${current.chainId}-${current.pairAddress}-${interval}-${metric}`} pair={current}><PriceChart userEntry={myPos?.avgEntry} pair={current} interval={interval} metric={metric} showVolume={volume} markers={markers} feeLive={showFee} /></ChartBoundary></div><div className="chart-side-stack"><QuickTrade pair={current} /><DipRipTool pair={current} />{current.chainId === 'solana' && <ShieldBadge mint={current.baseToken?.address} />}</div></div>
     <div className="focus-meta"><span data-testid="selected-token-age">Pool age {formatAge(current.pairCreatedAt)}</span><CreatorProfile pair={current} /><DataStatus data={live.data} id="token-data-status" /></div>
     <details className="td-edge edge-collapse"><summary>FEELESS Edge score <Explain>One grade for how tradeable this coin looks right now: buy/sell order flow, liquidity depth, the creator's track record, and how many snipers or bundled wallets got in early. Every reason behind the grade is listed when you open this.</Explain></summary><EdgeScore pair={current} /></details>
     <LaunchForensics pair={current} />
    <div className="token-actions"><button className="primary-action" data-testid="selected-token-trade-inapp" onClick={() => { selectPair(current); nav('/terminal/trade'); }}><ArrowUpRight size={19} /><span>Trade in FEELESS<small>{current.chainId === 'solana' ? 'Jupiter execution' : 'Network status'}</small></span><ArrowUpRight size={14} /></button>{current.chainId === 'solana' && /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address || '') && <a href={`https://pump.fun/coin/${address}`} target="_blank" rel="noopener noreferrer" data-testid="selected-token-pump-link"><Rocket size={19} /><span>View on Pump<small>External token page</small></span><ArrowUpRight size={14} /></a>}<a href={dexUrl(current)} target="_blank" rel="noreferrer" data-testid="selected-token-dex-link"><BarChart3 size={19} /><span>View on DEX<small>Chart & transactions</small></span><ArrowUpRight size={14} /></a></div>
  </section>;
};
// The viewer's live position in this coin: average entry from their real swaps, P&L against the
// live price (updates with every tick), and a flash the moment one of their trades confirms.
function useMyPosition(pair) {
  const { wallet } = useWallet() || {};
  const [pos, setPos] = useState(null); const [flash, setFlash] = useState(0);
  const token = pair?.baseToken?.address; const address = wallet?.address;
  const load = useCallback(() => {
    if (!address || !token || typeof fetch !== 'function') { setPos(null); return; }
    fetch(apiUrl(`/api/reputation/position/${address}/${token}`)).then(r => r.json()).then(d => setPos(d.position)).catch(() => {});
  }, [address, token]);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const onTrade = e => { if (!e.detail?.mint || e.detail.mint === token) { setFlash(Date.now()); setTimeout(load, 2500); setTimeout(load, 8000); } };
    window.addEventListener('feeless:trade-confirmed', onTrade);
    return () => window.removeEventListener('feeless:trade-confirmed', onTrade);
  }, [token, load]);
  return [pos, flash];
}

function PnlBadge({ pos, price, flash, symbol, imageUrl }) {
  if (!pos || !(pos.tokensHeld > 0) || !(price > 0)) return null;
  const pct = (price / pos.avgEntry - 1) * 100; const usd = (price - pos.avgEntry) * pos.tokensHeld;
  return <div key={flash} className={`my-pnl ${pct >= 0 ? 'up' : 'down'} ${flash ? 'just-traded' : ''}`} data-testid="my-pnl">
    <small>Your position</small><b>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</b><span>{usd >= 0 ? '+' : '−'}${Math.abs(usd).toLocaleString(undefined, { maximumFractionDigits: 2 })}</span><em>avg ${pos.avgEntry < 0.01 ? pos.avgEntry.toPrecision(4) : pos.avgEntry.toFixed(4)}</em>
    <ShareGifButton className="my-pnl-share" label="🎞 Share" card={{ kicker: 'LIVE POSITION · FEELESS TRENCHES', title: `$${symbol}`, imageUrl, tone: pct >= 0 ? 'up' : 'down', bigValue: Math.abs(pct), bigPrefix: pct >= 0 ? '+' : '−', bigSuffix: '%', bigDigits: 1, lines: [`${usd >= 0 ? '+' : '−'}$${Math.abs(usd).toLocaleString(undefined, { maximumFractionDigits: 2 })} unrealized`, `avg entry $${pos.avgEntry.toPrecision(4)} · now $${price.toPrecision(4)}`] }} />
    <button type="button" className="my-pnl-exit" onClick={() => window.dispatchEvent(new CustomEvent('feeless:quick-exit', { detail: { pct: 100 } }))}>Exit position</button>
  </div>;
}

function FocusAura({ pair }) {
  const color = useCoinColor(pair?.info?.imageUrl || pair?.baseToken?.imageUrl || pair?.imageUrl, pair?.baseToken?.address);
  return <CoinAura color={color} change24h={pair?.priceChange?.h24} />;
}
