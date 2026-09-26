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
  return <span data-testid={id} className={change24h == null ? 'muted' : change24h >= 0 ? 'positive mono' : 'negative mono'}>{change24h == null ? '—' : <AnimatedNumber value={change24h} format={formatPct} />}</span>;
}

export function LiveMarketCap({ pair, id }) {
  const { scale } = useLivePrice(pair);
  const base = Number(pair?.marketCap || pair?.fdv);
  return <span data-testid={id} className="mono">{Number.isFinite(base) && base > 0 ? <AnimatedNumber value={base * scale} format={formatUSD} /> : '—'}</span>;
}
