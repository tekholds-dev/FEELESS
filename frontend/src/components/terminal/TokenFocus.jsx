import { Explain } from '../Explain';
import { SentimentMeter } from './SentimentMeter';
import { RugProof } from '../RugProof';
import { EdgeScore } from './EdgeScore';
import { LivePrice, LiveChange24, LiveMarketCap } from './LiveCells';
import { CoinAura } from '../CoinAura';
import { useCoinColor } from '../../lib/coinColor';
import { CoinPassport } from '../CoinPassport';
import React from 'react';
import { TrenchChart } from './TrenchChart';
import { LaunchForensics } from './LaunchForensics';
import { Copy, Rocket, Star, BarChart3, ArrowUpRight } from 'lucide-react';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useWorkspace } from '../../hooks/useWorkspace';
import { Metric, TokenAvatar, DataStatus, MarketAvailabilityNotice, MarketError, TokenContextMeta, CreatorProfile } from './MarketPrimitives';
import { dexUrl, shortAddress, formatAge } from '../../lib/dexscreener';
import { useMarket } from '../../hooks/useMarket';

export const TokenFocus = ({ pair, has, toggle, defaultInterval = '1m', onExpand, expanded }) => {
  const nav = useNavigate(); const { selectPair } = useWorkspace();
  const live = useMarket(pair ? `/pair/${pair.chainId}/${pair.pairAddress}` : null, 3000);
  const livePair = live.data?.pairs?.[0];
  const current = livePair ? {
    ...pair,
    ...livePair,
    signals: { ...(pair?.signals || {}), ...(livePair.signals || {}) },
    rankingContext: { ...(pair?.rankingContext || {}), ...(livePair.rankingContext || {}) },
  } : pair;
  if (!current) return <section className="empty-focus" data-testid="token-focus-empty"><BarChart3 size={32} /><p>Select a market to open its chart.</p></section>;
  const address = current.baseToken?.address;
  const copy = async () => { try { await navigator.clipboard.writeText(address); toast.success('Contract address copied'); } catch { toast.error('Clipboard unavailable'); } };
  return <section className="token-focus has-aura m-live" data-testid="token-focus">
    <FocusAura pair={current} />
     <div className="focus-header"><TokenAvatar pair={current} size={46} /><div className="token-heading"><h2 data-testid="selected-token-symbol">{current.baseToken?.symbol}<span>/ {current.quoteToken?.symbol || 'USD'}</span></h2>{current.chainId === 'solana' && <RugProof mint={current.baseToken?.address} />}<div className="token-sub"><span data-testid="selected-token-chain">{current.chainId}</span><span>·</span><span data-testid="selected-token-dex">{current.dexId}</span><button onClick={copy} title="Copy contract address" data-testid="copy-selected-contract">{shortAddress(address)}<Copy size={11} /></button></div><TokenContextMeta pair={current} /><SentimentMeter pair={current} /></div><button title={has(current) ? 'Remove from watchlist' : 'Add to watchlist'} onClick={() => toggle(current)} className={`icon-btn ${has(current) ? 'is-saved' : ''}`} data-testid="selected-token-watchlist"><Star size={17} fill={has(current) ? 'currentColor' : 'none'} /></button></div>
    <MarketAvailabilityNotice data={live.data} error={live.error} errorStatus={live.errorStatus} errorProvider={live.errorProvider} id="token-market-availability" />
    {live.error && <MarketError error={`${live.error} Showing the discovery snapshot.`} reload={live.reload} id="token-refresh-error" />}
    <div className="token-metrics"><div className="metric"><small>Price USD</small><strong className="mono"><LivePrice pair={current} precise id="selected-token-price" /></strong></div><div className="metric"><small>24h change</small><LiveChange24 pair={current} id="selected-token-change" /></div><div className="metric"><small>{current.marketCap != null ? 'Market cap' : 'FDV'}</small><strong className="mono"><LiveMarketCap pair={current} id="selected-token-mcap" /></strong></div><Metric label="24h volume" value={current.volume?.h24} id="selected-token-volume" /><Metric label="Liquidity" value={current.liquidity?.usd} id="selected-token-liquidity" /></div>
     <CoinPassport pair={current} />
     <TrenchChart pair={current} defaultInterval={defaultInterval} onExpand={onExpand} expanded={expanded} />
     <div className="focus-meta"><span data-testid="selected-token-age">Pool age {formatAge(current.pairCreatedAt)}</span><CreatorProfile pair={current} /><DataStatus data={live.data} id="token-data-status" /></div>
     <section className="td-edge edge-static"><div className="edge-static-head">FEELESS Edge score <Explain>One grade for how tradeable this coin looks right now: buy/sell order flow, liquidity depth, the creator's track record, and how many snipers or bundled wallets got in early. Every reason behind the grade is listed below.</Explain></div><EdgeScore pair={current} /></section>
     <LaunchForensics pair={current} />
    <div className="token-actions"><button className="primary-action" data-testid="selected-token-trade-inapp" onClick={() => { selectPair(current); nav('/terminal/trade'); }}><ArrowUpRight size={19} /><span>Trade in FEELESS<small>{current.chainId === 'solana' ? 'Jupiter execution' : 'Network status'}</small></span><ArrowUpRight size={14} /></button>{current.chainId === 'solana' && /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address || '') && <a href={`https://pump.fun/coin/${address}`} target="_blank" rel="noopener noreferrer" data-testid="selected-token-pump-link"><Rocket size={19} /><span>View on Pump<small>External token page</small></span><ArrowUpRight size={14} /></a>}<a href={dexUrl(current)} target="_blank" rel="noreferrer" data-testid="selected-token-dex-link"><BarChart3 size={19} /><span>View on DEX<small>Chart & transactions</small></span><ArrowUpRight size={14} /></a></div>
  </section>;
};
function FocusAura({ pair }) {
  const color = useCoinColor(pair?.info?.imageUrl || pair?.baseToken?.imageUrl || pair?.imageUrl, pair?.baseToken?.address);
  return <CoinAura color={color} change24h={pair?.priceChange?.h24} />;
}
