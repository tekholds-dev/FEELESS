import React from 'react';
import { ExternalLink } from 'lucide-react';
import { formatUSD, formatPct, formatAge } from '../lib/dexscreener';
import { TokenAvatar, withRankingContext } from './terminal/MarketPrimitives';

export default function TokenCard({ pair, compact = false, onSelect, screenerLabel, testId = `coin-${pair?.chainId}-${pair?.pairAddress || pair?.baseToken?.address}` }) {
  if (!pair) return null;
  const safe = pair.url?.startsWith('https://dexscreener.com/');
  const activate = event => { if (event.target.closest('a')) return; onSelect?.(withRankingContext(pair, { label: screenerLabel })); };
  const signals = pair.signals || {};
  const label = signals.score_label || screenerLabel || 'Unavailable';
  const reasons = Array.isArray(signals.score_reasons) ? signals.score_reasons.filter(Boolean).slice(0, 3) : [];
  return <div className={`mini-token-card ${onSelect ? 'is-selectable' : ''}`} data-testid={testId} role={onSelect ? 'button' : undefined} tabIndex={onSelect ? 0 : undefined} onClick={activate} onKeyDown={onSelect ? event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(event); } } : undefined}><div className="mini-token-top"><TokenAvatar pair={pair} /><div><b>{pair.baseToken?.symbol}</b><small>{pair.chainId}</small></div>{safe && <a href={pair.url} target="_blank" rel="noreferrer" title="Open token on DexScreener" data-testid={`${testId}-external`}><ExternalLink size={14} /></a>}</div><div className="mini-token-prices"><span className="mono" data-testid={`${testId}-price`}>{formatUSD(pair.priceUsd)}</span><span data-testid={`${testId}-change`} className={Number(pair.priceChange?.h24) >= 0 ? 'positive' : 'negative'}>{formatPct(pair.priceChange?.h24)}</span></div><div className="mini-token-ranking" data-testid={`${testId}-ranking`}><strong data-testid={`${testId}-score-label`}>{label}</strong>{signals.screener_score != null && <span className="mono" data-testid={`${testId}-score`}>{signals.screener_score}</span>}<small data-testid={`${testId}-score-reasons`}>{reasons.length ? reasons.join(' · ') : 'Observed reasons unavailable'}</small></div>{!compact && <div className="mini-token-stats"><span>Liquidity<b data-testid={`${testId}-liquidity`}>{formatUSD(pair.liquidity?.usd)}</b></span><span>24h volume<b data-testid={`${testId}-volume`}>{formatUSD(pair.volume?.h24)}</b></span><span>Pool age<b data-testid={`${testId}-age`}>{formatAge(pair.pairCreatedAt)}</b></span></div>}</div>;
}