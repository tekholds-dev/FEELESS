import React, { useState } from 'react';
import { MetaCard } from './cards/MetaCard';
import '../styles/fuseLab.css';
import { tokenImageUrls } from './terminal/MarketPrimitives';
import { legTarget } from '../lib/fuseGo';

// A Fuse champion as a collectible card: drag to tilt, ⟲ to flip. Front = grade crest + the fused pools;
// back = every number behind its score. Grade sets rarity, strategy sets the design.
const RARITY = { A: 'legendary', B: 'epic', C: 'rare', D: 'common', F: 'common' };
const DESIGN = { yield: 'aurora', momentum: 'ember', steady: 'obsidian', degen: 'glitch' };
const ACCENT = { yield: ['#19f58f', '#6ad7ff'], momentum: ['#ff8a3d', '#f5c451'], steady: ['#19f58f', '#f5c451'], degen: ['#ff5ad1', '#00e5ff'] };
// The crest shows the basket's top-weighted coin, through the sitewide logo chain (DexScreener → CDN → FEELESS cache).
export const legPair = l => { const t = legTarget(l) || {}; return { chainId: l.chainId || 'solana', baseToken: { address: t.mint || l.baseAddress, symbol: t.symbol }, info: { imageUrl: t.mint === l.baseAddress ? l.logo : null } }; };
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);

// The back's money math for a budget: each leg's $ slice and what its last-24h move did to it, then the basket total
// minus the estimated network-fee drag. A replay of the last 24h, not a forecast.
export function cardMath(c, budget = 20) {
  const total = c.legs.reduce((a, l) => a + (Number(l.weight) || 0), 0) || 1;
  const legs = c.legs.map(l => { const usd = budget * (Number(l.weight) || 0) / total; const move = Number(l.change24h) || 0; return { ...l, usd, move, pnl: usd * move / 100 }; });
  const gross = legs.reduce((a, l) => a + l.pnl, 0); const fees = budget * (Number(c.parts?.feeDragPct) || 0) / 100;
  return { legs, gross, fees, net: gross - fees, end: budget + gross - fees };
}
const sgn = v => `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(Math.abs(v) < 1 ? 2 : 2)}`;

export function FuseCard({ c, style = 'yield', rank = 0, budget = 20, aura = '' }) {
  const [flipped, setFlipped] = useState(false);
  const [a, b] = ACCENT[style] || ACCENT.yield;
  const p = c.parts || {};
  const card = { key: c.pools.join(), kind: 'fuse', title: c.legs.slice(0, 3).map(l => l.symbol).join(' · ') + (c.legs.length > 3 ? ` +${c.legs.length - 3}` : ''),
    subtitle: `${['🥇', '🥈', '🥉'][rank] || ''} ${style.toUpperCase()} · FIT ${c.fitness}`, rarity: RARITY[p.grade] || 'rare', design: DESIGN[style] || 'holo',
    accent: a, accent2: b, glyph: p.grade || '✦', art: tokenImageUrls(legPair([...c.legs].sort((x, y) => (y.weight || 0) - (x.weight || 0))[0] || {})), motion: rank === 0 ? 'alive' : 'still', aura, holders: c.legs.length, edition: `GEN ${String(c.bornGen ?? 0).padStart(2, '0')}` };
  const m = cardMath(c, budget);
  const back = <div className="fcd-back">
    <div className="mc-top"><span>${budget} IN · LAST 24H</span><span>{p.grade}</span></div>
    <ul>{m.legs.map(l => <li key={l.pairAddress}><b>{l.symbol}</b><span>{Math.round(l.weight)}% · ${l.usd.toFixed(2)}</span><em className={l.pnl >= 0 ? 'up' : 'down'}>{l.move >= 0 ? '+' : ''}{l.move.toFixed(1)}% {sgn(l.pnl)}</em></li>)}</ul>
    <dl><dt>Moves</dt><dd className={m.gross >= 0 ? 'up' : 'down'}>{sgn(m.gross)}</dd><dt>Fee drag</dt><dd className="down">−${m.fees.toFixed(2)}</dd>
      <dt>${budget} → </dt><dd className={m.net >= 0 ? 'up' : 'down'}><b>${m.end.toFixed(2)}</b></dd><dt>Calm · APR</dt><dd>{p.calm} · {p.aprScore}</dd></dl>
    <small className="fcd-note">Replay of the last 24h, not a promise. APR = pool fee rate (busy-ness), not paid to holders.</small>
  </div>;
  return <div className="fcd" data-testid={`fuse-card-${rank}`}>
    <MetaCard card={card} size="md" interactive flipped={flipped} onFlip={setFlipped} back={back} className="fcd-card" />
    <button type="button" className="fcd-flip" aria-label={flipped ? 'Show front' : 'Show details'} onClick={() => setFlipped(f => !f)} data-testid={`fuse-card-flip-${rank}`}>⟲</button>
  </div>;
}

// An OWNED Fuse card (a real position from /fuses/pnl): front = the same card, back = live money per leg — what you put in,
// what you still hold at today's price, what you've already taken out, and the P&L. Never preview numbers.
const m$ = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0).toFixed(2)}`;
export function LiveFuseCard({ r, aura = '' }) {
  const [flipped, setFlipped] = useState(false);
  const legs = [...r.legs].sort((a, b) => (b.usd || 0) - (a.usd || 0));
  const up = r.pnlUsd >= 0;
  const g = r.closed ? 'C' : r.pnlPct >= 25 ? 'A' : r.pnlPct >= 0 ? 'B' : r.pnlPct >= -15 ? 'C' : 'D';
  const card = { key: r.id, kind: 'fuse', title: legs.slice(0, 3).map(l => l.symbol).join(' · ') + (legs.length > 3 ? ` +${legs.length - 3}` : ''),
    subtitle: `${r.name || 'MY FUSE'} · ${up ? '+' : ''}${r.pnlPct.toFixed(1)}%`, rarity: RARITY[g], design: up ? 'aurora' : 'ember', accent: up ? '#19f58f' : '#ff8fa3', accent2: '#f5c451',
    glyph: g, motion: up && !r.closed ? 'alive' : 'still', holders: legs.length, edition: r.closed ? 'CLOSED' : 'LIVE', aura,
    art: tokenImageUrls(legPair(legs[0] || {})) };
  const back = <div className="fcd-back fcd-live">
    <div className="mc-top"><span>{r.closed ? 'WITHDRAWN' : 'LIVE · YOUR MONEY'}</span><span>{m$(r.valueUsd)}</span></div>
    <ul>{legs.map(l => <li key={l.pairAddress + (l.sig || '')} className={l.soldUsd != null ? 'is-out' : ''}><b>{l.role === 'runner' ? '🏃 ' : ''}{l.symbol}</b><span>in {m$(l.usd)} → {m$(l.valueUsd)}</span>
      <em className={l.pnlUsd >= 0 ? 'up' : 'down'}>{l.pnlPct >= 0 ? '+' : ''}{l.pnlPct.toFixed(1)}% {m$(l.pnlUsd)}{l.soldUsd != null ? ' · sold' : (l.realizedUsd || 0) > 0 ? ` · took ${m$(l.realizedUsd)}` : ''}{!l.priced && l.soldUsd == null ? ' · no price' : ''}</em></li>)}</ul>
    <dl><dt>Put in</dt><dd>{m$(r.costUsd)}</dd><dt>Taken out</dt><dd className="up">{m$(r.realizedUsd || 0)}</dd><dt>Still held</dt><dd>{m$(r.valueUsd - (r.realizedUsd || 0))}</dd>
      <dt>P&L</dt><dd className={up ? 'up' : 'down'}><b>{m$(r.pnlUsd)} ({up ? '+' : ''}{r.pnlPct.toFixed(1)}%)</b></dd></dl>
    <small className="fcd-note">Live prices · exact fills from chain · updates every 30s.</small>
  </div>;
  return <div className="fcd" data-testid={`live-card-${r.id}`}>
    <MetaCard card={card} size="md" interactive flipped={flipped} onFlip={setFlipped} back={back} className="fcd-card" />
    <button type="button" className="fcd-flip" aria-label={flipped ? 'Show front' : 'Show live money'} onClick={() => setFlipped(f => !f)} data-testid={`live-card-flip-${r.id}`}>⟲</button>
  </div>;
}
