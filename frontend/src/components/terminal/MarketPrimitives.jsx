import React from 'react';
import { AlertTriangle, RefreshCw, UserRound } from 'lucide-react';
import { formatPct, formatUSD, formatTime, shortAddress } from '../../lib/dexscreener';

export const TokenAvatar = ({ pair, size = 34 }) => <span className="token-avatar" style={{ width: size, height: size }}>
  <span>{pair?.baseToken?.symbol?.slice(0, 2) || '?'}</span>
  {pair?.info?.imageUrl && <img src={pair.info.imageUrl} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} />}
</span>;

export function getCreatorProfile(pair) {
  const creator = pair?.info?.creator || pair?.creator || pair?.baseToken?.creator;
  if (!creator) return null;
  if (typeof creator === 'string') return { name: creator, address: creator };
  return {
    name: creator.name || creator.handle || creator.username || creator.address || 'Provider creator',
    address: creator.address || creator.wallet || creator.publicKey || '',
    imageUrl: creator.imageUrl || creator.avatarUrl || creator.image,
    url: creator.url || creator.profileUrl,
  };
}

export const CreatorProfile = ({ pair, compact = false }) => {
  const creator = getCreatorProfile(pair);
  if (!creator) return <span className={`creator-profile unavailable ${compact ? 'compact' : ''}`} data-testid="creator-profile-unavailable"><UserRound size={compact ? 12 : 15} /><span>Creator profile unavailable</span></span>;
  return <span className={`creator-profile ${compact ? 'compact' : ''}`} data-testid="creator-profile"><span className="creator-avatar">{creator.imageUrl ? <img src={creator.imageUrl} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} /> : <UserRound size={compact ? 12 : 15} />}</span><span><b>{creator.name}</b>{creator.address && <small>{shortAddress(creator.address)}</small>}</span>{creator.url && <a href={creator.url} target="_blank" rel="noreferrer">↗</a>}</span>;
};

export const TokenContextMeta = ({ pair }) => <div className="token-context-meta" data-testid="token-context-meta"><span>{pair?.chainId || 'network unavailable'}</span><span>·</span><span>{pair?.baseToken?.name || 'Coin name unavailable'}</span><span>·</span><span>{pair?.info?.imageUrl ? 'image loaded' : 'image unavailable'}</span><CreatorProfile pair={pair} compact /></div>;

export const Change = ({ value, id }) => <span data-testid={id} className={value == null ? 'muted' : Number(value) >= 0 ? 'positive mono' : 'negative mono'}>{formatPct(value)}</span>;

export const DataStatus = ({ data, id = 'data-status' }) => <span data-testid={id} className={`data-status ${data?.stale ? 'stale' : ''}`}>
  <i />{data ? `${data.stale ? 'STALE' : 'LIVE'} · ${formatTime(data.fetched_at)}` : 'CONNECTING'}
</span>;

export const MarketError = ({ error, reload, id = 'market-error', focusable = false, retryLabel = 'Retry' }) => <div className="market-error" role="alert" tabIndex={focusable ? 0 : undefined} data-testid={id}>
  <AlertTriangle size={17} /><span>{error}</span>{reload && <button data-testid={`${id}-retry`} onClick={() => reload()} aria-label={retryLabel} title={retryLabel}><RefreshCw size={15} /></button>}
</div>;

export const Metric = ({ label, value, id }) => <div className="metric"><small>{label}</small><strong data-testid={id} className="mono">{formatUSD(value)}</strong></div>;