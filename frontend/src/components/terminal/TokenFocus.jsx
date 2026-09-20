import React, { useState } from 'react';
import { Copy, ExternalLink, Rocket, Star, BarChart3, ArrowUpRight, Volume2 } from 'lucide-react';
import { toast } from 'sonner';
import { PriceChart } from './PriceChart';
import { ChartBoundary } from './ChartBoundary';
import { useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../hooks/useWorkspace';
import { Change, Metric, TokenAvatar, DataStatus, MarketError } from './MarketPrimitives';
import { dexUrl, shortAddress, formatAge } from '../../lib/dexscreener';
import { useMarket } from '../../hooks/useMarket';

export const TokenFocus = ({ pair, has, toggle, defaultInterval = '1h' }) => {
  const [interval, setInterval] = useState(defaultInterval);
  const nav = useNavigate(); const { selectPair } = useWorkspace();
  const [volume, setVolume] = useState(true);
  const live = useMarket(pair ? `/pair/${pair.chainId}/${pair.pairAddress}` : null, 60000);
  const current = live.data?.pairs?.[0] || pair;
  if (!current) return <section className="empty-focus" data-testid="token-focus-empty"><BarChart3 size={32} /><p>Select a market to open its chart.</p></section>;
  const address = current.baseToken?.address;
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <section className="token-focus" data-testid="token-focus">
    <div className="focus-header"><TokenAvatar pair={current} size={46} /><div className="token-heading"><h2 data-testid="selected-token-symbol">{current.baseToken?.symbol}<span>/ {current.quoteToken?.symbol || 'USD'}</span></h2><div className="token-sub"><span data-testid="selected-token-chain">{current.chainId}</span><span>·</span><span data-testid="selected-token-dex">{current.dexId}</span><button onClick={copy} title="Copy contract address" data-testid="copy-selected-contract">{shortAddress(address)}<Copy size={11} /></button></div></div><button title={has(current) ? 'Remove from watchlist' : 'Add to watchlist'} onClick={() => toggle(current)} className={`icon-btn ${has(current) ? 'is-saved' : ''}`} data-testid="selected-token-watchlist"><Star size={17} fill={has(current) ? 'currentColor' : 'none'} /></button></div>
    {live.error && <MarketError error={`${live.error} Showing the discovery snapshot.`} reload={live.reload} id="token-refresh-error" />}
    <div className="token-metrics"><Metric label="Price USD" value={current.priceUsd} id="selected-token-price" /><div className="metric"><small>24h change</small><Change value={current.priceChange?.h24} id="selected-token-change" /></div><Metric label={current.marketCap != null ? 'Market cap' : 'FDV'} value={current.marketCap ?? current.fdv} id="selected-token-mcap" /><Metric label="24h volume" value={current.volume?.h24} id="selected-token-volume" /><Metric label="Liquidity" value={current.liquidity?.usd} id="selected-token-liquidity" /></div>
    <div className="chart-toolbar"><div className="timeframes">{['5m', '15m', '1h', '4h', '1d'].map(t => <button className={t === interval ? 'active' : ''} data-testid={`chart-interval-${t}`} key={t} onClick={() => setInterval(t)}>{t.toUpperCase()}</button>)}</div><button className={`volume-control ${volume ? 'positive' : ''}`} title="Toggle volume bars" data-testid="chart-volume-toggle" onClick={() => setVolume(v => !v)}><Volume2 size={13} /><span>Volume</span></button><a title="Open advanced chart" data-testid="chart-advanced-link" href={dexUrl(current)} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a></div>
    <ChartBoundary key={`${current.chainId}-${current.pairAddress}-${interval}`} pair={current}><PriceChart pair={current} interval={interval} showVolume={volume} /></ChartBoundary>
    <div className="focus-meta"><span data-testid="selected-token-age">Pool age {formatAge(current.pairCreatedAt)}</span><DataStatus data={live.data} id="token-data-status" /></div>
    <div className="token-actions"><button className="primary-action" data-testid="selected-token-trade-inapp" onClick={() => { selectPair(current); nav('/terminal/trade'); }}><ArrowUpRight size={19} /><span>Trade in FEELESS<small>{current.chainId === 'solana' ? 'Jupiter execution' : 'Network status'}</small></span><ArrowUpRight size={14} /></button><a href={dexUrl(current)} target="_blank" rel="noreferrer" data-testid="selected-token-dex-link"><BarChart3 size={19} /><span>View on DEX<small>Chart & transactions</small></span><ArrowUpRight size={14} /></a></div>
  </section>;
};