import React, { useEffect, useState } from 'react';
import { AlertTriangle, Coins, RefreshCw, UserRound } from 'lucide-react';
import { formatPct, formatUSD, formatTime, shortAddress } from '../../lib/dexscreener';

const isImageSource = value => typeof value === 'string' && (/^https?:\/\//i.test(value) || /^data:image\//i.test(value));

export const tokenImageUrls = pair => {
  const address = pair?.baseToken?.address;
  const chainId = pair?.chainId;
  const candidates = [
    pair?.info?.imageUrl,
    pair?.info?.image,
    pair?.imageUrl,
    pair?.image,
    pair?.logoUrl,
    pair?.logoURI,
    pair?.baseToken?.imageUrl,
    pair?.baseToken?.image,
    pair?.baseToken?.logoURI,
    pair?.baseToken?.logoUrl,
    pair?.baseToken?.logo,
  ].filter(isImageSource);
  if (chainId && address) {
    candidates.push(`https://dd.dexscreener.com/ds-data/tokens/${encodeURIComponent(chainId)}/${encodeURIComponent(address)}.png`);
  }
  return [...new Set(candidates)];
};

export const TokenAvatar = ({ pair, size = 34 }) => {
  const sources = tokenImageUrls(pair);
  const [imageIndex, setImageIndex] = useState(0);
  const sourceKey = sources.join('|');
  useEffect(() => { setImageIndex(0); }, [sourceKey]);
  const imageUrl = sources[imageIndex];
  const symbol = pair?.baseToken?.symbol || 'token';
  return <span className="token-avatar" style={{ width: size, height: size }} aria-label={`${symbol} token logo`}>
    {!imageUrl && <span className="token-avatar-fallback" aria-hidden="true"><Coins size={Math.round(size * 0.42)} /></span>}
    {imageUrl && <img key={imageUrl} src={imageUrl} alt="" onError={() => setImageIndex(index => index + 1)} />}
  </span>;
};

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
  <i />{data ? `${data.error ? 'UNAVAILABLE' : data.stale ? 'STALE' : 'LIVE'} · ${formatTime(data.fetched_at)}` : 'CONNECTING'}
</span>;

export const MarketError = ({ error, reload, id = 'market-error', focusable = false, retryLabel = 'Retry', description }) => <div className="market-error" role="alert" tabIndex={focusable ? 0 : undefined} data-testid={id}>
  <AlertTriangle size={17} /><span className="market-error-copy"><span>{error}</span>{description && <small data-testid={`${id}-description`}>{description}</small>}</span>{reload && <button type="button" data-testid={`${id}-retry`} onClick={() => reload()} aria-label={retryLabel} title={retryLabel}><RefreshCw size={15} /></button>}
</div>;

export const Metric = ({ label, value, id }) => <div className="metric"><small>{label}</small><strong data-testid={id} className="mono">{formatUSD(value)}</strong></div>;