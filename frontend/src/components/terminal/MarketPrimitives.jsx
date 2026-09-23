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

const firstDefined = values => values.find(value => value !== null && value !== undefined && value !== '');

export const getRankingContext = (pair, fallback = {}) => {
  const signals = pair?.signals || {};
  const persisted = pair?.rankingContext || {};
  const reasonSource = firstDefined([
    signals.score_reasons,
    persisted.reasons,
    pair?.score_reasons,
    fallback.reasons,
  ]);
  return {
    label: firstDefined([
      signals.score_label,
      persisted.label,
      pair?.screener_label,
      pair?.screenerLabel,
      fallback.label,
    ]) || null,
    score: firstDefined([
      signals.screener_score,
      persisted.score,
      pair?.screener_score,
      fallback.score,
    ]) ?? null,
    reasons: Array.isArray(reasonSource) ? reasonSource.filter(Boolean).slice(0, 3) : [],
    screener: firstDefined([signals.screener, persisted.screener, pair?.screener, fallback.screener]) || null,
    provider: firstDefined([persisted.provider, pair?.provider, fallback.provider]) || null,
    sourceLabel: firstDefined([persisted.sourceLabel, pair?.source_label, fallback.sourceLabel]) || null,
    sourceUrl: firstDefined([persisted.sourceUrl, pair?.source_url, fallback.sourceUrl]) || null,
    stale: firstDefined([persisted.stale, pair?.stale, fallback.stale]) ?? null,
    fetchedAt: firstDefined([persisted.fetchedAt, pair?.fetched_at, fallback.fetchedAt]) || null,
  };
};

export const withRankingContext = (pair, fallback = {}) => {
  if (!pair) return pair;
  return { ...pair, rankingContext: { ...(pair.rankingContext || {}), ...getRankingContext(pair, fallback) } };
};

export const TokenAvatar = ({ pair, size = 34, onExhausted, maxAttempts }) => {
  const sources = tokenImageUrls(pair);
  const [imageIndex, setImageIndex] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [exhausted, setExhausted] = useState(false);
  const sourceKey = sources.join('|');
  useEffect(() => {
    setImageIndex(0);
    setAttempts(0);
    setExhausted(false);
  }, [sourceKey]);
  useEffect(() => {
    if (onExhausted && maxAttempts && !sources.length && !exhausted) {
      setExhausted(true);
      onExhausted(pair);
    }
  }, [exhausted, maxAttempts, onExhausted, pair, sources.length]);
  const imageUrl = sources[imageIndex];
  const symbol = pair?.baseToken?.symbol || 'token';
  return <span className="token-avatar" style={{ width: size, height: size }} aria-label={`${symbol} token logo`}>
    {(!imageUrl || exhausted) && <span className="token-avatar-fallback" aria-hidden="true"><Coins size={Math.round(size * 0.42)} /></span>}
    {imageUrl && !exhausted && <img
      key={`${imageUrl}-${attempts}`}
      src={imageUrl}
      alt=""
      onError={() => {
        const nextAttempts = attempts + 1;
        setAttempts(nextAttempts);
        if (onExhausted && maxAttempts && nextAttempts >= maxAttempts) {
          setExhausted(true);
          onExhausted(pair);
          return;
        }
        setImageIndex(index => {
          if (index + 1 < sources.length) return index + 1;
          return onExhausted && maxAttempts ? 0 : sources.length;
        });
      }}
    />}
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

export function getMarketAvailability({ data, error, errorStatus, errorProvider } = {}) {
  const text = [
    typeof error === 'string' ? error : '',
    data?.error,
    data?.fallback_reason,
    data?.fallbackReason,
    data?.provider_warning?.provider,
  ].filter(Boolean).join(' ');
  const status = Number(data?.provider_status || data?.providerStatus || errorStatus || data?.provider_warning?.status);
  const rateLimited = data?.rate_limited === true
    || data?.provider_warning?.rate_limited === true
    || status === 429
    || /HTTP\s*429|rate[\s-]?limit|throttl/i.test(text);
  const unavailable = Boolean(error)
    || data?.status === 'provider_unavailable'
    || data?.status === 'unavailable'
    || Boolean(data?.provider_warning)
    || /provider.*unavailable|temporarily unavailable|unavailable from/i.test(text);
  if (!rateLimited && !unavailable) return null;
  return {
    rateLimited,
    provider: data?.provider_warning?.provider
      || data?.primary_provider
      || data?.provider
      || errorProvider
      || 'market provider',
  };
}

export const MarketAvailabilityNotice = ({ data, error, errorStatus, errorProvider, id = 'market-availability' }) => {
  const availability = getMarketAvailability({ data, error, errorStatus, errorProvider });
  if (!availability) return null;
  const provider = availability.provider === 'Public providers' ? 'public providers' : availability.provider;
  const message = availability.rateLimited
    ? `Market data is temporarily rate limited by ${provider}. Existing fallback data remains visible when available and may recover on the next refresh. This is not a trading failure.`
    : `Market data is temporarily unavailable from ${provider}. Existing fallback data remains visible when available and may recover on the next refresh. This is not a trading failure.`;
  return <div className="market-availability" role="status" aria-live="polite" data-testid={id}>
    <AlertTriangle size={15} /><span>{message}</span>
  </div>;
};

export const MarketError = ({ error, reload, id = 'market-error', focusable = false, retryLabel = 'Retry', description }) => <div className="market-error" role="alert" tabIndex={focusable ? 0 : undefined} data-testid={id}>
  <AlertTriangle size={17} /><span className="market-error-copy"><span>{error}</span>{description && <small data-testid={`${id}-description`}>{description}</small>}</span>{reload && <button type="button" data-testid={`${id}-retry`} onClick={() => reload()} aria-label={retryLabel} title={retryLabel}><RefreshCw size={15} /></button>}
</div>;

export const Metric = ({ label, value, id }) => <div className="metric"><small>{label}</small><strong data-testid={id} className="mono">{formatUSD(value)}</strong></div>;