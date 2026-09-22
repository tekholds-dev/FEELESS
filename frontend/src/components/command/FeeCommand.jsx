import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowUpRight, Check, Copy, Orbit, RotateCw, ShieldCheck, Radio, Activity, BarChart3 } from 'lucide-react';
import { toast } from 'sonner';
import { FeelessMark } from '../FeelessLogo';
import { useMarket } from '../../hooks/useMarket';
import { formatUSD, formatPct, shortAddress } from '../../lib/dexscreener';
import { useWorkspace } from '../../hooks/useWorkspace';
import { PriceChart } from '../terminal/PriceChart';
import { ChartBoundary } from '../terminal/ChartBoundary';

export const ALLOCATIONS = [
  { amount: 70, name: 'Liquidity & Ecosystem', description: 'Market infrastructure, liquidity provisioning and the connected FEELESS ecosystem.', color: '#00e9a0' },
  { amount: 15, name: 'Marketing & Growth', description: 'Awareness, distribution and responsible ecosystem adoption.', color: '#c3f4de' },
  { amount: 10, name: 'Team & Development', description: 'Engineering, research and ongoing product delivery.', color: '#62a992' },
  { amount: 5, name: 'Community & Airdrops', description: 'Community participation and future published airdrop programs.', color: '#d6bd7a' },
];

export const Tokenomics = ({ compact = false }) => {
  const [active, setActive] = useState(0); const item = ALLOCATIONS[active];
  return <section className={`tokenomics ${compact ? 'compact-tokenomics' : ''}`}><div className="command-section-title"><span><Orbit size={16} />SUPPLY ARCHITECTURE</span><small>APPROVED ALLOCATION / 100%</small></div><div className="allocation-track">{ALLOCATIONS.map((a, i) => <button key={a.name} data-testid={`allocation-segment-${i}`} title={`${a.amount}% ${a.name}`} onClick={() => setActive(i)} className={i === active ? 'selected' : ''} style={{ flex: a.amount, '--allocation-color': a.color }}><span>{a.amount}%</span></button>)}</div><div className="allocation-detail" data-testid="allocation-detail"><strong style={{ color: item.color }}>{item.amount}<small>%</small></strong><div><h2>{item.name}</h2><p>{item.description}</p></div><div className="allocation-switch">{ALLOCATIONS.map((a, i) => <button key={a.name} onClick={() => setActive(i)} data-testid={`allocation-select-${i}`} title={a.name} style={{ background: a.color, opacity: active === i ? 1 : .25 }} />)}</div></div><div className="allocation-policy"><span><Check size={12} />NO PRIVATE SALE</span><span><Check size={12} />FAIR LAUNCH</span><small>Policy, not proof of on-chain allocation.</small></div></section>;
};

export const FeeHeartbeat = ({ asset, assets = [], loading }) => {
  const trackedAssets = assets.length ? assets : asset ? [asset] : [];
  const [activeIndex, setActiveIndex] = useState(0);
  const [chartInterval, setChartInterval] = useState('1h');
  const activeAsset = trackedAssets[activeIndex % Math.max(trackedAssets.length, 1)] || asset;
  const { data: metadata } = useMarket(activeAsset?.mint ? `/api/trading/mint/${activeAsset.mint}` : null, 300000);
  const symbol = activeAsset?.label || activeAsset?.id?.toUpperCase() || 'FEE';
  const price = activeAsset?.pair?.priceUsd;
  const chartPair = activeAsset?.pair?.pairAddress ? {
    ...activeAsset.pair,
    chainId: activeAsset.pair.chainId || activeAsset.chain || 'solana',
  } : null;
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(activeAsset.mint);
      toast.success(`$${symbol} mint copied`);
    } catch {
      toast.error('Clipboard unavailable');
    }
  };
  const flipAsset = () => setActiveIndex(index => (index + 1) % Math.max(trackedAssets.length, 1));
  return <section className="fee-heartbeat" data-testid="fee-market-initializing"><div className="heartbeat-top"><span className="fee-name"><FeelessMark size={39} /><span><b>${symbol}</b><small>THE ECOSYSTEM HEARTBEAT</small></span></span><div className="heartbeat-controls"><span className="state-tag amber" data-testid="fee-market-state">{loading ? 'VERIFYING MARKET' : activeAsset?.status === 'provider_unavailable' ? 'PROVIDER UNAVAILABLE' : chartPair ? 'MARKET LIVE' : 'MARKET INITIALIZING'}</span>{trackedAssets.length > 1 && <button className="heartbeat-flip" data-testid="fee-heartbeat-flip" title="Flip through tracked fee assets" onClick={flipAsset}><RotateCw size={13} /><span>Flip price</span></button>}</div></div><div className="heartbeat-visual"><div className="network-orbit orbit-one" /><div className="network-orbit orbit-two" /><div className="network-orbit orbit-three" /><div className="heartbeat-mark"><FeelessMark size={110} /></div><span className="orbit-label label-a"><i />DISCOVERY ONLINE</span><span className="orbit-label label-b"><i />FEE-BACK PLANNED</span><span className="orbit-label label-c"><i />COMMUNITY CONNECTED</span><div className="heartbeat-caption"><h1>The heart of<br /><span>a FeeLess future.</span></h1><p>{chartPair ? `Live ${symbol} market candles from the indexed pool.` : `No invented candles. Awaiting an indexed market for the supplied $${symbol} contract.`}</p></div></div><div className="heartbeat-supply"><span>Mint supply / Solana RPC</span><b data-testid="heartbeat-verified-supply">{metadata?.supply ? `${(Number(metadata.supply) / 10 ** metadata.decimals).toLocaleString('en-US')} ${symbol}` : 'Verification unavailable'}</b></div><div className="heartbeat-market-price" data-testid="heartbeat-market-price"><span>Market price · ${symbol}</span><b>{price ? formatUSD(price) : 'Awaiting provider market'}</b><small>{activeAsset?.pair?.priceChange?.h24 != null ? `${formatPct(activeAsset.pair.priceChange.h24)} · 24h` : 'Provider snapshot unavailable'}</small></div><div className="heartbeat-chart-panel" data-testid="fee-heartbeat-chart"><div className="heartbeat-chart-heading"><span><BarChart3 size={14} />PRICE ACTION / {symbol}</span><div className="heartbeat-chart-timeframes">{['5m', '15m', '1h', '4h', '1d'].map(value => <button type="button" key={value} className={chartInterval === value ? 'active' : ''} data-testid={`fee-chart-interval-${value}`} onClick={() => setChartInterval(value)}>{value.toUpperCase()}</button>)}</div></div>{chartPair ? <ChartBoundary key={`${chartPair.chainId}-${chartPair.pairAddress}-${chartInterval}`} pair={chartPair}><PriceChart pair={chartPair} interval={chartInterval} showVolume /></ChartBoundary> : <div className="heartbeat-chart-empty" data-testid="fee-heartbeat-chart-empty"><BarChart3 size={19} /><span>Chart activates when the provider indexes a market pair for ${symbol}.</span></div>}</div><div className="heartbeat-bottom"><button data-testid="fee-copy-mint" disabled={!activeAsset?.mint} title={`Copy ${symbol} mint`} onClick={copy}><Copy size={12} />{activeAsset?.mint ? shortAddress(activeAsset.mint) : 'Checking contract registry…'}</button><Link data-testid="fee-registry-link" to="/terminal/fee">Inspect ${symbol}<ArrowUpRight size={13} /></Link></div></section>;
};

export const FeeAssetPage = ({ asset, children }) => {
  const { data: metadata, error } = useMarket(asset?.mint ? `/api/trading/mint/${asset.mint}` : null, 300000);
  const supply = metadata?.supply ? (Number(metadata.supply) / 10 ** metadata.decimals).toLocaleString('en-US') : 'Unavailable';
  return <div className="asset-command-page"><div className="command-page-title"><span className="eyebrow">FEELESS / CORE ECOSYSTEM ASSET</span><h1>$FEE is the heartbeat.</h1><p>Platform identity. Ecosystem alignment. A FeeLess future.</p></div>{children}<Tokenomics /><div className="verified-facts"><div><small>TOTAL SUPPLY / RPC</small><strong data-testid="fee-total-supply">{supply}</strong></div><div><small>MINT AUTHORITY</small><strong data-testid="fee-mint-authority">{metadata ? metadata.mint_authority ? 'Present' : 'None reported' : 'Unavailable'}</strong></div><div><small>FREEZE AUTHORITY</small><strong data-testid="fee-freeze-authority">{metadata ? metadata.freeze_authority ? 'Present' : 'None reported' : 'Unavailable'}</strong></div><div><small>PUBLIC PLATFORM TARGET</small><strong>Q2 2027</strong></div></div>{error && <p className="provider-note" data-testid="fee-metadata-unavailable">On-chain mint metadata unavailable. Supply and authorities are not assumed.</p>}<div className="asset-links"><a data-testid="fee-explorer" target="_blank" rel="noreferrer" href={`https://solscan.io/token/${asset?.mint}`}>Inspect contract<ArrowUpRight size={14} /></a><Link to="/terminal/feeback" data-testid="fee-program-link">Fee-Back architecture<ArrowUpRight size={14} /></Link><Link to="/terminal/whitepaper" data-testid="fee-whitepaper-link">Whitepaper<ArrowUpRight size={14} /></Link></div></div>;
};