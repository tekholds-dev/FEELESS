import React, { useState } from 'react';
import { useMarket } from '../hooks/useMarket';
import { DataStatus, MarketError } from './terminal/MarketPrimitives';
import { matchesPad } from '../lib/launchpads';
import TokenCard from './TokenCard';
export default function TopCoins({ ecosystem }) {
  const [tab, setTab] = useState('trending');
  const { data, error, loading, reload } = useMarket(`/feed?kind=${tab}&chain=${ecosystem?.chainId || 'solana'}`);
  const pairs = (data?.pairs || []).filter(p => !ecosystem?.isLaunchpad || matchesPad(p, ecosystem.id));
  return <div className="top-coins"><div className="section-title"><h2>Coin radar</h2><DataStatus data={data} id="globe-coins-status" /></div><div className="segmented">{['trending', 'new'].map(t => <button key={t} data-testid={`globe-coins-${t}`} onClick={() => setTab(t)} className={tab === t ? 'active' : ''}>{t === 'trending' ? 'Top coins' : 'New coins'}</button>)}</div>{error && <MarketError error={error} reload={reload} id="globe-coins-error" />}<div className="top-coins-list custom-scroll">{loading && <p data-testid="globe-coins-loading" className="empty-table">Loading live coins…</p>}{!loading && !pairs.length && <p data-testid="globe-coins-empty" className="empty-table">No matching coins in this provider feed.</p>}{pairs.slice(0, 10).map(p => <TokenCard key={p.pairAddress} pair={p} />)}</div><small className="provider-note">GeckoTerminal · Live indexed coin markets, not every launch.</small></div>;
}