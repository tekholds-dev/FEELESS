import React from 'react';
import { usePrime, TIER } from './ArenaPrime';
import { heroCard } from './FuseLanding';

/* ⚡ Home: the best Fuse card on the board right now — one tap opens it. Live numbers from /fuses/prime (one poll a minute),
   labelled 📄 paper or 💵 real; a reading of right now, never a promise. */
const HREF = '/terminal/fuse?tab=arena&zone=prime';

export function BestFuseTile({ onOpen }) {
  const d = usePrime(60000);
  const c = heroCard(d?.cards, null);
  if (!c) return null;
  const t = TIER[c.tier] || TIER.gold; const p = Number(c.pnlPct || 0);
  return <a href={HREF} onClick={e => { if (onOpen) { e.preventDefault(); onOpen(HREF); } }} className="bft m-card" data-testid="best-fuse-tile" style={{ '--bft': t.look?.accent || '#15d16a' }}
    data-tip={`Best Fuse card right now: ${c.label} (${c.real ? 'real money' : 'paper'}). Tap to open it in the Arena.`}>
    <span className="m-label">⚡ BEST FUSE CARD NOW · {c.real ? '💵 REAL' : '📄 PAPER'}</span>
    <b className="bft-name">{c.label}</b>
    <em className={`m-num ${p >= 0 ? 'm-pos' : 'm-neg'}`}>{p >= 0 ? '+' : ''}{p.toFixed(1)}%</em>
    <span className="bft-coins">{c.legs.slice(0, 6).map(l => <i key={l.pairAddress} className={(l.livePct || 0) >= 0 ? 'm-pos' : 'm-neg'}>${l.symbol}</i>)}</span>
    <u>Open →</u></a>;
}
