import React, { useState } from 'react';
import { useMarket } from '../hooks/useMarket';
import { useWorkspace } from '../hooks/useWorkspace';
import { DataStatus, MarketAvailabilityNotice, MarketError } from './terminal/MarketPrimitives';
import { hasProviderImage } from '../lib/dexscreener';
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

function CoinFeed({ id, title, result, ecosystem, onSelect, screener }) {
  const pairs = (result.data?.pairs || []).filter(pair => (
    (!ecosystem?.isLaunchpad || matchesPad(pair, ecosystem.id))
    && (id !== 'new' || hasProviderImage(pair))
  ));
  const ecosystemName = ecosystem?.name || 'selected ecosystem';
  const modeMatches = !result.data?.screener || result.data.screener === screener;
  const waitingForMode = !modeMatches && !result.error;
  return <section className="coin-feed-section" data-testid={`globe-coins-${id}`}>
     <div className="coin-feed-heading">
       <div><h3>{title}</h3><small className="coin-feed-source">{result.data?.label || 'Public indexed markets'}{(result.data?.sourceUrl || result.data?.source_url) && <> · <a href={result.data.sourceUrl || result.data.source_url} target="_blank" rel="noreferrer">Source ↗</a></>}</small></div>
       <span className="coin-feed-status"><DataStatus data={result.data} id={`globe-coins-${id}-status`} />{result.refreshing && <i data-testid={`globe-coins-${id}-refreshing`}>LIVE</i>}</span>
    </div>
    <MarketAvailabilityNotice
      data={result.data}
      error={result.error}
      errorStatus={result.errorStatus}
      errorProvider={result.errorProvider}
      id={`globe-coins-${id}-availability`}
    />
    {result.error && <MarketError
      error={`Unable to load ${title.toLowerCase()} for ${ecosystemName}. ${result.error}`}
      reload={result.reload}
      focusable
      retryLabel={`Retry ${title.toLowerCase()} for ${ecosystemName}`}
      id={`globe-coins-${id}-error`}
    />}
    <div className="coin-feed-list custom-scroll">
       {!result.error && (result.loading || waitingForMode) && <p role="status" aria-live="polite" data-testid={`globe-coins-${id}-loading`} className="empty-table market-coin-loading">Loading {title.toLowerCase()} for {ecosystemName}…</p>}
       {!result.loading && !waitingForMode && !result.error && !pairs.length && <p role="status" aria-live="polite" tabIndex="0" data-testid={`globe-coins-${id}-empty`} className="empty-table">No {title.toLowerCase()} available for {ecosystemName} in this provider feed.</p>}
       {!result.loading && !waitingForMode && pairs.slice(0, 5).map(pair => <TokenCard key={pair.pairAddress} pair={pair} screenerLabel={result.data?.screener_label} onSelect={onSelect} />)}
    </div>
  </section>;
}

export default function TopCoins({ ecosystem }) {
  const workspace = useWorkspace() || {};
  const selectPair = workspace.selectPair || (() => {});
  const chain = ecosystem?.chainId || 'solana';
  const [screen, setScreen] = useState('quality');
  const topScreenParam = screen === 'quality' ? '' : `&screen=${screen}`;
  const freshScreenParam = screen === 'new' || screen === 'quality' ? '' : `&screen=${screen}`;
  const freshScreener = screen === 'quality' ? 'new' : screen;
  const top = useMarket(`/feed?kind=trending&chain=${chain}${topScreenParam}`);
  const fresh = useMarket(`/feed?kind=new&chain=${chain}${freshScreenParam}`);
  const providers = [...new Set([top.data?.provider, fresh.data?.provider].filter(Boolean))];
  const onSelect = pair => {
    selectPair(pair);
    window.history.pushState({}, '', '/terminal/chat');
    window.dispatchEvent(new PopStateEvent('popstate'));
  };
  return <div className="top-coins" data-testid="globe-coin-radar">
     <div className="section-title"><h2>Coin radar</h2><label className="coin-screener"><span>SCREEN</span><select aria-label="Coin screener" data-testid="coin-screener" value={screen} onChange={event => setScreen(event.target.value)}><option value="quality">Best observed</option><option value="momentum">Momentum</option><option value="volume">Volume leaders</option><option value="new">Fresh</option></select></label></div>
      <CoinFeed id="trending" title="Top coins" result={top} ecosystem={ecosystem} screener={screen} onSelect={onSelect} />
      <CoinFeed id="new" title="New coins" result={fresh} ecosystem={ecosystem} screener={freshScreener} onSelect={onSelect} />
     <small className="provider-note">{providers.length ? providers.join(' + ') : 'Public provider'} · {top.data?.screener_disclosure || 'Provider-ranked indexed coin markets, not every launch.'} <a href={top.data?.sourceUrl || top.data?.source_url || fresh.data?.sourceUrl || fresh.data?.source_url || 'https://dexscreener.com'} target="_blank" rel="noreferrer">Open source boundary ↗</a></small>
  </div>;
}