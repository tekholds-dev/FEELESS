import React, { useState } from 'react';
import { toast } from 'sonner';
import { Sparkles, Flame, Copy, ExternalLink, RefreshCw } from 'lucide-react';
import { useMarket } from '../hooks/useMarket';
import { matchesPad } from '../lib/launchpads';
import { MarketAvailabilityNotice, TokenAvatar } from './terminal/MarketPrimitives';
import { formatUSD, formatPct, formatAge, hasProviderImage } from '../lib/dexscreener';

// Social "new stuff" stream — fresh + trending coins on the ecosystem. No pools / liquidity tables.
export default function NewStuffFeed({ ecosystem }) {
  const [tab, setTab] = useState('new');
  const chain = ecosystem?.chainId || 'solana';
  const screen = tab === 'new' ? 'new' : 'quality';
  const scope = ecosystem?.isLaunchpad ? `&scope=${encodeURIComponent(ecosystem.id)}` : '';
  const { data, loading, refreshing, error, errorStatus, errorProvider, reload } = useMarket(`/feed?kind=${tab}&chain=${chain}&screen=${screen}${scope}`, 15000);
  const chainTop = useMarket(`/feed?kind=trending&chain=${chain}&screen=quality`, 30000);
  const scoped = (data?.pairs || [])
    .filter(p => !ecosystem?.isLaunchpad || matchesPad(p, ecosystem.id))
    .filter(p => tab !== 'new' || hasProviderImage(p));
  const fallback = !loading && !scoped.length ? (chainTop.data?.pairs || []) : [];
  const pairs = (scoped.length ? scoped : fallback).slice(0, 6);

  const copyCA = async (addr) => {
    if (!addr) return;
    try { await navigator.clipboard.writeText(addr); toast.success('Contract copied'); }
    catch { toast.error('Copy failed'); }
  };

  return <section className="new-stuff" data-testid="new-stuff-feed">
    <div className="new-stuff-head">
      <div className="new-stuff-tabs">
        <button data-testid="new-stuff-tab-new" className={tab === 'new' ? 'active' : ''} onClick={() => setTab('new')}><Sparkles size={13} />Fresh</button>
        <button data-testid="new-stuff-tab-trending" className={tab === 'trending' ? 'active' : ''} onClick={() => setTab('trending')}><Flame size={13} />Trending</button>
      </div>
      <button className={`new-stuff-refresh ${refreshing ? 'is-refreshing' : ''}`} data-testid="new-stuff-refresh" title="Refresh feed" onClick={() => reload()}><RefreshCw size={13} /></button>
    </div>
    <MarketAvailabilityNotice data={data} error={error} errorStatus={errorStatus} errorProvider={errorProvider} id="new-stuff-market-availability" />
    <div className="new-stuff-list custom-scroll">
      {loading && !pairs.length && <div className="new-stuff-empty" data-testid="new-stuff-loading"><span className="loader" />Scanning the chain…</div>}
      {!loading && !scoped.length && pairs.length > 0 && <div className="new-stuff-note" data-testid="new-stuff-fallback">No {tab === 'new' ? 'fresh' : 'trending'} {ecosystem?.name || ''} coins indexed right now — showing today's top {chain} coins.</div>}
      {!loading && !pairs.length && <div className="new-stuff-empty" data-testid="new-stuff-empty">Nothing indexed here yet. Provider coverage is partial — check back soon.</div>}
      {pairs.map(p => {
        const addr = p.baseToken?.address;
        const change = tab === 'new' ? p.priceChange?.h1 : p.priceChange?.h24;
        return <div className="new-stuff-item" key={`${p.chainId}-${p.pairAddress}`} data-testid={`new-stuff-item-${addr}`}>
          <TokenAvatar pair={p} size={48} />
          <div className="new-stuff-meta">
            <b>{p.baseToken?.symbol || '—'}</b>
            <small>{p.baseToken?.name || p.dexId}</small>
          </div>
          <div className="new-stuff-stats">
            <span className="mono">{formatUSD(p.marketCap)}</span>
            <small>mcap · {formatUSD(p.liquidity?.usd)} liq</small>
            <span className={Number(change) >= 0 ? 'positive mono' : 'negative mono'}>{formatPct(change)}</span>
            <em>{tab === 'new' ? `${formatAge(p.pairCreatedAt)} old` : `${formatUSD(p.volume?.h24)} vol`}</em>
          </div>
          <div className="new-stuff-actions">
            <button title="Copy contract" data-testid={`new-stuff-copy-${addr}`} onClick={() => copyCA(addr)}><Copy size={13} /></button>
            {p.url?.startsWith('https://dexscreener.com/') && <a title="Open chart" data-testid={`new-stuff-open-${addr}`} href={p.url} target="_blank" rel="noreferrer"><ExternalLink size={13} /></a>}
          </div>
        </div>;
      })}
    </div>
    <small className="new-stuff-note">{data?.provider || 'Public provider'} · {data?.screener_label || 'Provider snapshot'} · indexed markets, not every launch. Verify every contract yourself.</small>
  </section>;
}
