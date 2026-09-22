import React from 'react';
import { useMarket } from '../hooks/useMarket';
import { DataStatus, MarketError } from './terminal/MarketPrimitives';
import { matchesPad } from '../lib/launchpads';
import TokenCard from './TokenCard';

function CoinFeed({ id, title, result, ecosystem }) {
  const pairs = (result.data?.pairs || []).filter(pair => !ecosystem?.isLaunchpad || matchesPad(pair, ecosystem.id));
  const ecosystemName = ecosystem?.name || 'selected ecosystem';
  return <section className="coin-feed-section" data-testid={`globe-coins-${id}`}>
    <div className="coin-feed-heading">
      <h3>{title}</h3>
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
      {!result.loading && pairs.slice(0, 5).map(pair => <TokenCard key={pair.pairAddress} pair={pair} />)}
    </div>
  </section>;
}

export default function TopCoins({ ecosystem }) {
  const chain = ecosystem?.chainId || 'solana';
  const top = useMarket(`/feed?kind=trending&chain=${chain}`);
  const fresh = useMarket(`/feed?kind=new&chain=${chain}`);
  return <div className="top-coins" data-testid="globe-coin-radar">
    <div className="section-title"><h2>Coin radar</h2><span className="provider-note">Live provider feed</span></div>
    <CoinFeed id="trending" title="Top coins" result={top} ecosystem={ecosystem} />
    <CoinFeed id="new" title="New coins" result={fresh} ecosystem={ecosystem} />
    <small className="provider-note">GeckoTerminal · Live indexed coin markets, not every launch.</small>
  </div>;
}