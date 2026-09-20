import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { formatPct, formatUSD, formatTime } from '../../lib/dexscreener';

export const TokenAvatar = ({ pair, size = 34 }) => <span className="token-avatar" style={{ width: size, height: size }}>
  <span>{pair?.baseToken?.symbol?.slice(0, 2) || '?'}</span>
  {pair?.info?.imageUrl && <img src={pair.info.imageUrl} alt="" onError={e => { e.currentTarget.style.display = 'none'; }} />}
</span>;

export const Change = ({ value, id }) => <span data-testid={id} className={value == null ? 'muted' : Number(value) >= 0 ? 'positive mono' : 'negative mono'}>{formatPct(value)}</span>;

export const DataStatus = ({ data, id = 'data-status' }) => <span data-testid={id} className={`data-status ${data?.stale ? 'stale' : ''}`}>
  <i />{data ? `${data.stale ? 'STALE' : 'LIVE'} · ${formatTime(data.fetched_at)}` : 'CONNECTING'}
</span>;

export const MarketError = ({ error, reload, id = 'market-error' }) => <div className="market-error" role="alert" data-testid={id}>
  <AlertTriangle size={17} /><span>{error}</span>{reload && <button data-testid={`${id}-retry`} onClick={() => reload()} title="Retry"><RefreshCw size={15} /></button>}
</div>;

export const Metric = ({ label, value, id }) => <div className="metric"><small>{label}</small><strong data-testid={id} className="mono">{formatUSD(value)}</strong></div>;