import { LivePrice } from './terminal/LiveCells';
import React from 'react';
import { ExternalLink } from 'lucide-react';
import { formatUSD, formatPct, formatAge } from '../lib/dexscreener';
import { TokenAvatar, withRankingContext } from './terminal/MarketPrimitives';

// When the screener has no score, describe the coin from its own live stats (never invented).
function observedReasons(pair) {
  const out = [];
  const t = pair.txns?.h1 || {}; const b = Number(t.buys) || 0; const sl = Number(t.sells) || 0;
  if (b + sl >= 20) out.push(`${Math.round((b / (b + sl)) * 100)}% buys 1h`);
  const h1 = Number(pair.priceChange?.h1);
  if (Number.isFinite(h1) && pair.priceChange?.h1 != null) out.push(`${h1 >= 0 ? '+' : ''}${h1.toFixed(1)}% 1h`);
  const liq = Number(pair.liquidity?.usd); const vol = Number(pair.volume?.h24);
  if (liq > 0 && vol > 0) out.push(`${(vol / liq).toFixed(1)}× vol/liq`);
  return out;
}
function observedLabel(pair) {
  const t = pair.txns?.h1 || {}; const b = Number(t.buys) || 0; const sl = Number(t.sells) || 0;
  const h1 = Number(pair.priceChange?.h1); const age = Date.now() - Number(pair.pairCreatedAt);
  if (Number.isFinite(age) && age > 0 && age < 6 * 3600e3) return 'Fresh pool';
  if (h1 >= 10 && b > sl) return 'Heating up';
  if (h1 <= -10) return 'Cooling off';
  if (b + sl >= 20 && b / (b + sl) >= 0.6) return 'Buy pressure';
  return null;
}

export default function TokenCard({ pair, compact = false, onSelect, screenerLabel, testId = `coin-${pair?.chainId}-${pair?.pairAddress || pair?.baseToken?.address}` }) {
  if (!pair) return null;
  const safe = pair.url?.startsWith('https://dexscreener.com/');
  const activate = event => { if (event.target.closest('a')) return; onSelect?.(withRankingContext(pair, { label: screenerLabel })); };
  const signals = pair.signals || {};
  const label = signals.score_label || screenerLabel || observedLabel(pair) || 'Unavailable';
  const listed = Array.isArray(signals.score_reasons) ? signals.score_reasons.filter(Boolean).slice(0, 3) : [];
  const reasons = listed.length ? listed : observedReasons(pair);
  return <div className={`mini-token-card ${onSelect ? 'is-selectable' : ''}`} data-testid={testId} role={onSelect ? 'button' : undefined} tabIndex={onSelect ? 0 : undefined} onClick={activate} onKeyDown={onSelect ? event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(event); } } : undefined}><div className="mini-token-top"><TokenAvatar pair={pair} /><div><b>{pair.baseToken?.symbol}</b><small>{pair.chainId}</small></div>{safe && <a href={pair.url} target="_blank" rel="noreferrer" title="Open token on DexScreener" data-testid={`${testId}-external`}><ExternalLink size={14} /></a>}</div><div className="mini-token-prices"><span className="mono" data-testid={`${testId}-price`}><LivePrice pair={pair} precise /></span><span data-testid={`${testId}-change`} className={Number(pair.priceChange?.h24) >= 0 ? 'positive' : 'negative'}>{formatPct(pair.priceChange?.h24)}</span></div><div className="mini-token-ranking" data-testid={`${testId}-ranking`}><strong data-testid={`${testId}-score-label`}>{label}</strong>{signals.screener_score != null && <span className="mono" data-testid={`${testId}-score`}>{signals.screener_score}</span>}<small data-testid={`${testId}-score-reasons`}>{reasons.length ? reasons.join(' · ') : 'Observed reasons unavailable'}</small></div>{!compact && <div className="mini-token-stats"><span>Liquidity<b data-testid={`${testId}-liquidity`}>{formatUSD(pair.liquidity?.usd)}</b></span><span>24h volume<b data-testid={`${testId}-volume`}>{formatUSD(pair.volume?.h24)}</b></span><span>Pool age<b data-testid={`${testId}-age`}>{formatAge(pair.pairCreatedAt)}</b></span></div>}</div>;
}