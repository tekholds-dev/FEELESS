import React from 'react';
import { useLivePrice } from '../../lib/livePriceHub';
import { AnimatedNumber } from './AnimatedNumber';
import { formatUSD, formatPct } from '../../lib/dexscreener';
import { formatLivePrice } from '../../lib/livePrice';

export function LivePrice({ pair, precise = false, id }) {
  const { usd } = useLivePrice(pair);
  return <span data-testid={id} className="mono live-cell">{usd == null ? '—' : <AnimatedNumber value={usd} format={precise ? formatLivePrice : formatUSD} />}</span>;
}

export function LiveChange24({ pair, id }) {
  const { change24h } = useLivePrice(pair);
  const hot = change24h != null && Math.abs(change24h) >= 20;
  const cls = change24h == null ? 'muted' : `${change24h >= 0 ? 'positive' : 'negative'} mono${hot ? (change24h >= 0 ? ' hot-move' : ' cold-move') : ''}`;
  return <span data-testid={id} className={cls}>{change24h == null ? '—' : <AnimatedNumber value={change24h} format={formatPct} />}</span>;
}

export function LiveMarketCap({ pair, id }) {
  const { scale } = useLivePrice(pair);
  const base = Number(pair?.marketCap || pair?.fdv);
  return <span data-testid={id} className="mono">{Number.isFinite(base) && base > 0 ? <AnimatedNumber value={base * scale} format={formatUSD} /> : '—'}</span>;
}
