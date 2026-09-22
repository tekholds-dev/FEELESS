import React from 'react';
import { useMarket } from '../hooks/useMarket';
import { useWorkspace } from '../hooks/useWorkspace';
import { DataStatus, MarketError } from './terminal/MarketPrimitives';
import { matchesPad } from '../lib/launchpads';
import TokenCard from './TokenCard';

const FEeless_COIN_IDENTITIES = [
  { id: 'fee', name: 'FEE', symbol: 'FEE', description: 'Core FEELESS identity asset', imageUrl: '/assets/feeless-logo.png' },
  { id: 'feecat', name: 'FeeCat', symbol: 'FEECAT', description: 'Community and Fee-Back culture asset', imageUrl: '/assets/feecat-mark.png' },
  { id: 'rfee', name: 'RFEE', symbol: 'RFEE', description: 'Fee-Back return-path asset', imageUrl: null },
];

export function FeelessCoinCards() {
  return <section className="feeless-coin-cards" data-testid="feeless-coin-cards" aria-label="FEELESS coin identities">
    <div className="feeless-coin-cards-heading"><div><span className="eyebrow">FEELESS ECOSYSTEM</span><h3>Identity assets</h3></div><small>Market data follows provider indexing</small></div>
    <div className="feeless-coin-cards-grid">
      {FEeless_COIN_IDENTITIES.map(coin => <article className="feeless-coin-card" data-testid={`feeless-coin-${coin.id}`} key={coin.id}>
        <span className={`feeless-coin-mark ${coin.id === 'rfee' ? 'text-mark' : ''}`}>{coin.imageUrl ? <img src={coin.imageUrl} alt="" /> : <span>RF</span>}</span>
        <div className="feeless-coin-copy"><strong>{coin.name}</strong><span>{coin.symbol}</span><small>{coin.description}</small></div>
        <div className="feeless-coin-state"><i />NOT INDEXED</div>
        <p>No approved public market pair is attached yet. Price, liquidity, and volume are intentionally unavailable.</p>
      </article>)}
    </div>
  </section>;
}

function CoinFeed({ id, title, result, ecosystem, onSelect }) {
  const pairs = (result.data?.pairs || []).filter(pair => !ecosystem?.isLaunchpad || matchesPad(pair, ecosystem.id));
  const ecosystemName = ecosystem?.name || 'selected ecosystem';
  return <section className="coin-feed-section" data-testid={`globe-coins-${id}`}>
     <div className="coin-feed-heading">
       <div><h3>{title}</h3><small className="coin-feed-source">{result.data?.label || 'Public indexed markets'}{(result.data?.sourceUrl || result.data?.source_url) && <> · <a href={result.data.sourceUrl || result.data.source_url} target="_blank" rel="noreferrer">Source ↗</a></>}</small></div>
       <span className="coin-feed-status"><DataStatus data={result.data} id={`globe-coins-${id}-status`} />{result.refreshing && <i data-testid={`globe-coins-${id}-refreshing`}>LIVE</i>}</span>
    </div>
    {result.error && <MarketError
      error={`Unable to load ${title.toLowerCase()} for ${ecosystemName}. ${result.error}`}
      reload={result.reload}
      focusable
      retryLabel={`Retry ${title.toLowerCase()} for ${ecosystemName}`}
      id={`globe-coins-${id}-error`}
    />}
    <div className="coin-feed-list custom-scroll">
      {!result.error && result.loading && <p role="status" aria-live="polite" data-testid={`globe-coins-${id}-loading`} className="empty-table market-coin-loading">Loading {title.toLowerCase()} for {ecosystemName}…</p>}
       {!result.loading && !result.error && !pairs.length && <p role="status" aria-live="polite" tabIndex="0" data-testid={`globe-coins-${id}-empty`} className="empty-table">No {title.toLowerCase()} available for {ecosystemName} in this provider feed.</p>}
      {!result.loading && pairs.slice(0, 5).map(pair => <TokenCard key={pair.pairAddress} pair={pair} onSelect={onSelect} />)}
    </div>
  </section>;
}

export default function TopCoins({ ecosystem }) {
  const workspace = useWorkspace() || {};
  const selectPair = workspace.selectPair || (() => {});
  const chain = ecosystem?.chainId || 'solana';
  const top = useMarket(`/feed?kind=trending&chain=${chain}`);
  const fresh = useMarket(`/feed?kind=new&chain=${chain}`);
  const providers = [...new Set([top.data?.provider, fresh.data?.provider].filter(Boolean))];
  const onSelect = pair => {
    selectPair(pair);
    window.history.pushState({}, '', '/terminal/chat');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };
  return <div className="top-coins" data-testid="globe-coin-radar">
     <div className="section-title"><h2>Coin radar</h2><span className="provider-note">Public indexed markets</span></div>
     <CoinFeed id="trending" title="Top coins" result={top} ecosystem={ecosystem} onSelect={onSelect} />
     <CoinFeed id="new" title="New coins" result={fresh} ecosystem={ecosystem} onSelect={onSelect} />
     <small className="provider-note">{providers.length ? providers.join(' + ') : 'Public provider'} · Live indexed coin markets, not every launch. <a href={top.data?.sourceUrl || top.data?.source_url || fresh.data?.sourceUrl || fresh.data?.source_url || 'https://dexscreener.com'} target="_blank" rel="noreferrer">Open source boundary ↗</a></small>
  </div>;
}