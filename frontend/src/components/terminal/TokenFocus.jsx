import React, { useEffect, useState } from 'react';
import { Copy, ExternalLink, Rocket, Star, BarChart3, ArrowUpRight, Volume2 } from 'lucide-react';
import { toast } from 'sonner';
import { PriceChart } from './PriceChart';
import { ChartBoundary } from './ChartBoundary';
import { useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../hooks/useWorkspace';
import { Change, Metric, TokenAvatar, DataStatus, MarketError, TokenContextMeta, CreatorProfile, getRankingContext } from './MarketPrimitives';
import { dexUrl, shortAddress, formatAge } from '../../lib/dexscreener';
import { useMarket } from '../../hooks/useMarket';

export const TokenFocus = ({ pair, has, toggle, defaultInterval = '1h' }) => {
  const [interval, setInterval] = useState(defaultInterval);
  const [metric, setMetric] = useState('price');
  const nav = useNavigate(); const { selectPair } = useWorkspace();
  const [volume, setVolume] = useState(true);
  const live = useMarket(pair ? `/pair/${pair.chainId}/${pair.pairAddress}` : null, 60000);
  const livePair = live.data?.pairs?.[0];
  const current = livePair ? {
    ...pair,
    ...livePair,
    signals: { ...(pair?.signals || {}), ...(livePair.signals || {}) },
    rankingContext: { ...(pair?.rankingContext || {}), ...(livePair.rankingContext || {}) },
  } : pair;
  useEffect(() => { setMetric('price'); }, [current?.chainId, current?.pairAddress]);
  if (!current) return <section className="empty-focus" data-testid="token-focus-empty"><BarChart3 size={32} /><p>Select a market to open its chart.</p></section>;
  const address = current.baseToken?.address;
  const metricValue = id => id === 'marketCap' ? current.marketCap : current.fdv;
  const metricAvailable = id => metricValue(id) !== null && metricValue(id) !== undefined && metricValue(id) !== '' && Number.isFinite(Number(metricValue(id)));
  const ranking = getRankingContext(current, {
    provider: live.data?.provider,
    sourceLabel: live.data?.source_label,
    stale: live.data?.stale,
    fetchedAt: live.data?.fetched_at,
  });
  const rankingProvider = ranking.provider || ranking.sourceLabel || 'Provider unavailable';
  const rankingStatus = ranking.stale === true ? 'STALE SNAPSHOT' : ranking.stale === false ? 'LIVE SNAPSHOT' : 'STATUS UNAVAILABLE';
  const providerAnalytics = [
    ['snipers', 'Snipers'],
    ['bundlers', 'Bundlers'],
    ['holderConcentration', 'Holder concentration'],
  ];
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <section className="token-focus" data-testid="token-focus">
     <div className="focus-header"><TokenAvatar pair={current} size={46} /><div className="token-heading"><h2 data-testid="selected-token-symbol">{current.baseToken?.symbol}<span>/ {current.quoteToken?.symbol || 'USD'}</span></h2><div className="token-sub"><span data-testid="selected-token-chain">{current.chainId}</span><span>·</span><span data-testid="selected-token-dex">{current.dexId}</span><button onClick={copy} title="Copy contract address" data-testid="copy-selected-contract">{shortAddress(address)}<Copy size={11} /></button></div><TokenContextMeta pair={current} /></div><button title={has(current) ? 'Remove from watchlist' : 'Add to watchlist'} onClick={() => toggle(current)} className={`icon-btn ${has(current) ? 'is-saved' : ''}`} data-testid="selected-token-watchlist"><Star size={17} fill={has(current) ? 'currentColor' : 'none'} /></button></div>
    {live.error && <MarketError error={`${live.error} Showing the discovery snapshot.`} reload={live.reload} id="token-refresh-error" />}
    <div className="token-metrics"><Metric label="Price USD" value={current.priceUsd} id="selected-token-price" /><div className="metric"><small>24h change</small><Change value={current.priceChange?.h24} id="selected-token-change" /></div><Metric label={current.marketCap != null ? 'Market cap' : 'FDV'} value={current.marketCap ?? current.fdv} id="selected-token-mcap" /><Metric label="24h volume" value={current.volume?.h24} id="selected-token-volume" /><Metric label="Liquidity" value={current.liquidity?.usd} id="selected-token-liquidity" /></div>
     <div className="chart-toolbar"><div className="chart-metrics" role="group" aria-label="Chart metric" data-testid="chart-metric-selector">{[['price', 'Price'], ['marketCap', 'Market cap'], ['fdv', 'FDV']].map(([id, label]) => <button key={id} className={metric === id ? 'active' : ''} disabled={id !== 'price' && !metricAvailable(id)} title={id === 'price' || metricAvailable(id) ? `Show ${label}` : `${label} unavailable from provider`} data-testid={`chart-metric-${id}`} onClick={() => setMetric(id)}>{label}{id !== 'price' && !metricAvailable(id) ? ' · unavailable' : ''}</button>)}</div><div className="timeframes">{['5m', '15m', '1h', '4h', '1d'].map(t => <button className={t === interval ? 'active' : ''} data-testid={`chart-interval-${t}`} key={t} onClick={() => setInterval(t)}>{t.toUpperCase()}</button>)}</div><button className={`volume-control ${volume ? 'positive' : ''}`} title="Toggle volume bars" data-testid="chart-volume-toggle" onClick={() => setVolume(v => !v)}><Volume2 size={13} /><span>Volume</span></button><a title="Open advanced chart" data-testid="chart-advanced-link" href={dexUrl(current)} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a></div>
     <ChartBoundary key={`${current.chainId}-${current.pairAddress}-${interval}-${metric}`} pair={current}><PriceChart pair={current} interval={interval} metric={metric} showVolume={volume} /></ChartBoundary>
     <div className="focus-meta"><span data-testid="selected-token-age">Pool age {formatAge(current.pairCreatedAt)}</span><CreatorProfile pair={current} /><DataStatus data={live.data} id="token-data-status" /></div>
     <section className="token-ranking-context" data-testid="token-ranking-context"><div className="token-analytics-heading"><strong>Ranking context</strong><span>Provider-reported · not a recommendation</span></div><div className="token-ranking-summary"><div className={ranking.label ? 'is-available' : 'is-unavailable'}><small>SCREENER LABEL</small><strong data-testid="selected-token-screener-label">{ranking.label || 'Unavailable'}</strong></div><div className={ranking.score !== null ? 'is-available' : 'is-unavailable'}><small>OBSERVED SCORE</small><strong data-testid="selected-token-screener-score">{ranking.score !== null ? String(ranking.score) : 'Unavailable'}</strong></div></div><div className="token-ranking-reasons"><small>PROVIDER-REPORTED REASONS</small>{ranking.reasons.length ? <ol data-testid="selected-token-screener-reasons">{ranking.reasons.map((reason, index) => <li key={`${reason}-${index}`}>{reason}</li>)}</ol> : <span data-testid="selected-token-screener-reasons">Observed reasons unavailable</span>}</div><div className="token-ranking-disclosure"><span data-testid="selected-token-ranking-provider">{rankingProvider}</span><span data-testid="selected-token-ranking-status">{rankingStatus}</span><small data-testid="selected-token-ranking-disclosure">Provider coverage and freshness can change. This ranking context is not a recommendation.</small></div></section>
     <section className="token-analytics" data-testid="token-analytics"><div className="token-analytics-heading"><strong>Provider intelligence</strong><span>Observed only · no estimates</span></div><div className="token-analytics-grid">{providerAnalytics.map(([id, label]) => { const value = current.signals?.[id] ?? current.analytics?.[id] ?? current.info?.analytics?.[id]; const available = value !== null && value !== undefined && value !== ''; return <div className={`token-analytics-item ${available ? 'is-available' : 'is-unavailable'}`} data-testid={`token-analytics-${id}`} key={id}><b>{label}</b><strong>{available ? String(value) : 'Unavailable'}</strong><small>{available ? 'Provider-backed observation' : 'No connected provider response'}</small></div>; })}</div></section>
    <div className="token-actions"><button className="primary-action" data-testid="selected-token-trade-inapp" onClick={() => { selectPair(current); nav('/terminal/trade'); }}><ArrowUpRight size={19} /><span>Trade in FEELESS<small>{current.chainId === 'solana' ? 'Jupiter execution' : 'Network status'}</small></span><ArrowUpRight size={14} /></button><a href={dexUrl(current)} target="_blank" rel="noreferrer" data-testid="selected-token-dex-link"><BarChart3 size={19} /><span>View on DEX<small>Chart & transactions</small></span><ArrowUpRight size={14} /></a></div>
  </section>;
};