import React from 'react';
import { useMarket } from '../hooks/useMarket';
import { DataStatus, MarketError } from './terminal/MarketPrimitives';
import { matchesPad } from '../lib/launchpads';
import TokenCard from './TokenCard';

function CoinFeed({ id, title, result, ecosystem }) {
  const pairs = (result.data?.pairs || []).filter(pair => !ecosystem?.isLaunchpad || matchesPad(pair, ecosystem.id));
  return <section className="coin-feed-section" data-testid={`globe-coins-${id}`}>
    <div className="coin-feed-heading">
      <h3>{title}</h3>
      <span className="coin-feed-status"><DataStatus data={result.data} id={`globe-coins-${id}-status`} />{result.refreshing && <i data-testid={`globe-coins-${id}-refreshing`}>LIVE</i>}</span>
    </div>
    {result.error && <MarketError error={result.error} reload={result.reload} id={`globe-coins-${id}-error`} />}
    <div className="coin-feed-list custom-scroll">
      {result.loading && <p data-testid={`globe-coins-${id}-loading`} className="empty-table market-coin-loading">Loading live DEX coins…</p>}
      {!result.loading && !pairs.length && <p data-testid={`globe-coins-${id}-empty`} className="empty-table">No matching coins in this provider feed.</p>}
      {pairs.slice(0, 5).map(pair => <TokenCard key={pair.pairAddress} pair={pair} />)}
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
    <CoinFeed id="new" title="New pool deals" result={fresh} ecosystem={ecosystem} />
    <small className="provider-note">GeckoTerminal · Live indexed coin markets, not every launch.</small>
  </div>;
}