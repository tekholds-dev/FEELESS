import React, { useEffect, useState } from 'react';
import { MetaCard } from './cards/MetaCard';
import '../styles/fuseLab.css';
import { tokenImageUrls } from './terminal/MarketPrimitives';
import { legTarget } from '../lib/fuseGo';
import { useLivePrices } from '../lib/livePrices';
import { MoneyMath } from './FuseMoney';

// A Fuse champion as a collectible card: drag to tilt, ⟲ to flip. Front = grade crest + the fused pools;
// back = every number behind its score. Grade sets rarity, strategy sets the design.
const RARITY = { A: 'legendary', B: 'epic', C: 'rare', D: 'common', F: 'common' };
const DESIGN = { yield: 'aurora', momentum: 'ember', steady: 'obsidian', degen: 'glitch' };
const ACCENT = { yield: ['#19f58f', '#6ad7ff'], momentum: ['#ff8a3d', '#f5c451'], steady: ['#19f58f', '#f5c451'], degen: ['#ff5ad1', '#00e5ff'] };
// The crest shows the basket's top-weighted coin, through the sitewide logo chain (DexScreener → CDN → FEELESS cache).
// The coin a leg shows: the leg's own mint (card legs / runners / a SOL anchor), else the coin a pool buys. Never empty.
export const legPair = l => { const t = legTarget(l) || {}; const address = l.mint || t.mint || l.baseAddress;
  return { chainId: l.chainId || 'solana', baseToken: { address, symbol: l.symbol || t.symbol }, info: { imageUrl: address === l.baseAddress || address === l.mint ? (l.logo || l.imageUrl || null) : null } }; };
const usd = v => (v >= 1e6 ? `$${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `$${(v / 1e3).toFixed(1)}K` : `$${Math.round(v || 0)}`);

// The back's money math for a budget: each leg's $ slice and what its last-24h move did to it, then the basket total
// minus the estimated network-fee drag. A replay of the last 24h, not a forecast.
export function cardMath(c, budget = 20) {
  const total = c.legs.reduce((a, l) => a + (Number(l.weight) || 0), 0) || 1;
  const legs = c.legs.map(l => { const usd = budget * (Number(l.weight) || 0) / total; const move = Number(l.replayPct ?? l.change24h) || 0; /* honest window: young pools use 6h / 1h, never since-launch */ return { ...l, usd, move, pnl: usd * move / 100 }; });
  const gross = legs.reduce((a, l) => a + l.pnl, 0); const fees = budget * (Number(c.parts?.feeDragPct) || 0) / 100;
  return { legs, gross, fees, net: gross - fees, end: budget + gross - fees };
}
const fmtPx = v => (v >= 1 ? v.toFixed(3) : v >= 0.001 ? v.toFixed(5) : v.toPrecision(3));
const sgn = v => `${v >= 0 ? '+' : '−'}$${Math.abs(v).toFixed(Math.abs(v) < 1 ? 2 : 2)}`;

export function FuseCard({ c, style = 'yield', rank = 0, budget = 20, aura = '', autoFlip = 0 }) {
  const [flipped, setFlipped] = useState(false);
  const [hold, setHold] = useState(false);
  // autoFlip (ms): showcase cards turn by themselves front ⇄ back; paused while hovered/focused, off for reduced motion.
  useEffect(() => {
    if (!autoFlip || hold || window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return undefined;
    const t = setInterval(() => setFlipped(f => !f), autoFlip); return () => clearInterval(t);
  }, [autoFlip, hold]);
  const [a, b] = ACCENT[style] || ACCENT.yield;
  const p = c.parts || {};
  const card = { key: c.pools.join(), kind: 'fuse', title: c.legs.slice(0, 3).map(l => l.symbol).join(' · ') + (c.legs.length > 3 ? ` +${c.legs.length - 3}` : ''),
    subtitle: `${['🥇', '🥈', '🥉'][rank] || ''} ${style.toUpperCase()} · FIT ${c.fitness}`, rarity: RARITY[p.grade] || 'rare', design: DESIGN[style] || 'holo',
    accent: a, accent2: b, glyph: p.grade || '✦', art: tokenImageUrls(legPair([...c.legs].sort((x, y) => (y.weight || 0) - (x.weight || 0))[0] || {})), motion: rank === 0 ? 'alive' : 'still', aura, holders: c.legs.length, edition: `GEN ${String(c.bornGen ?? 0).padStart(2, '0')}` };
  const live = useLivePrices(c.legs.map(l => l.pairAddress));
  // live truth: a leg with a real entry shows its move SINCE ENTRY at the live price (else the honest 24h replay)
  const legsLive = c.legs.map(l => { const lp_ = live.get(l.pairAddress)?.price; return lp_ > 0 && Number(l.entry) > 0 ? { ...l, replayPct: (lp_ / Number(l.entry) - 1) * 100, sinceEntry: true } : l; });
  const isLive = legsLive.some(l => l.sinceEntry);
  const m = cardMath({ ...c, legs: legsLive }, budget);
  const lp = pa => live.get(pa);
  const back = <div className="fcd-back">
    <div className="mc-top"><span>${budget} IN · {isLive ? 'SINCE ENTRY · LIVE' : 'LAST 24H'}</span><span>{p.grade}</span></div>
    <ul>{m.legs.map(l => <li key={l.pairAddress}><b>{l.symbol || (l.baseAddress ? `${l.baseAddress.slice(0, 4)}…` : '—')}</b><span>{Math.round(l.weight)}% · ${l.usd.toFixed(2)}</span><em className={l.pnl >= 0 ? 'up' : 'down'}>{l.move >= 0 ? '+' : ''}{l.move.toFixed(1)}% {sgn(l.pnl)}{lp(l.pairAddress) ? <i className={`fcd-px ${lp(l.pairAddress).m5 >= 0 ? 'up' : 'down'}`}> · ● ${fmtPx(lp(l.pairAddress).price)} {lp(l.pairAddress).m5 >= 0 ? '+' : ''}{lp(l.pairAddress).m5.toFixed(1)}% 5m</i> : null}</em></li>)}</ul>
    <dl><dt>Moves</dt><dd className={m.gross >= 0 ? 'up' : 'down'}>{sgn(m.gross)}</dd><dt>Fee drag</dt><dd className="down">−${m.fees.toFixed(2)}</dd>
      <dt>${budget} → </dt><dd className={m.net >= 0 ? 'up' : 'down'}><b>${m.end.toFixed(2)}</b></dd><dt>Calm · APR</dt><dd>{p.calm} · {p.aprScore}</dd></dl>
    <small className="fcd-note">{isLive ? 'Live: each coin from its real entry at today\'s price (10s), true fills.' : 'Replay of the last 24h, not a promise.'} APR = pool fee rate (busy-ness), not paid to holders.</small>
  </div>;
  return <div className="fcd" data-testid={`fuse-card-${rank}`} onMouseEnter={() => setHold(true)} onMouseLeave={() => setHold(false)} onFocus={() => setHold(true)} onBlur={() => setHold(false)}>
    <MetaCard card={card} size="md" interactive flipped={flipped} onFlip={setFlipped} back={back} className="fcd-card" />
    <button type="button" className="fcd-flip" aria-label={flipped ? 'Show front' : 'Show details'} onClick={() => setFlipped(f => !f)} data-testid={`fuse-card-flip-${rank}`}>⟲</button>
  </div>;
}

// Recompute an owned card's value from live prices (same rules as the server's position_pnl).
export function revalue(r, live) {
  let cost = 0; let value = 0; let anyLive = false;
  const legs = r.legs.map(l => {
    const px = live?.get?.(l.pairAddress)?.price;
    if (l.soldUsd != null || !(px > 0)) { cost += l.usd || 0; value += l.valueUsd || 0; return l; }
    anyLive = true;
    // a leg that knows its pool (tier cards) is valued at what SELLING it would pay — a big bag in a thin pool is worth less than mid
    const mid = (l.tokens || 0) * px; const lq = l.liq === undefined ? 0 : l.liq > 0 ? l.liq : 20000;   // tier legs: unknown depth = thin (server UNKNOWN_LIQ)
    const held = lq > 0 ? mid / (1 + mid / (lq / 2)) : mid; const v = held + (l.realizedUsd || 0); const c = l.usd || 0;
    cost += c; value += v;
    return { ...l, priceNow: px, heldUsd: held, valueUsd: v, pnlUsd: v - c, pnlPct: c ? (v / c - 1) * 100 : 0, priced: true };
  });
  // Cards that compound / take profit inside (Prime) measure against what they STARTED with (baseUsd), plus cash + parked SOL
  // (extraUsd) — per-leg cost re-bases on every TP, so leg cost would read ~0% forever.
  if (r.baseUsd > 0 && !anyLive) return r;   // no live price yet: keep the server's numbers
  if (r.baseUsd > 0) { const v = value + (r.extraUsd || 0); return { ...r, legs, valueUsd: v, costUsd: r.baseUsd, pnlUsd: v - r.baseUsd, pnlPct: (v / r.baseUsd - 1) * 100 }; }
  return { ...r, legs, valueUsd: value, pnlUsd: value - cost, pnlPct: cost ? (value / cost - 1) * 100 : 0 };
}

// An OWNED Fuse card (a real position from /fuses/pnl): front = the same card, back = live money per leg — what you put in,
// what you still hold at today's price, what you've already taken out, and the P&L. Never preview numbers.
const m$ = v => `${v < 0 ? '−' : ''}$${Math.abs(v || 0).toFixed(2)}`;
export function LiveFuseCard({ r: r0, aura = '', look = null, label = null }) {
  const [flipped, setFlipped] = useState(false);
  const live = useLivePrices(r0.legs.filter(l => l.soldUsd == null).map(l => l.pairAddress));
  const r = revalue(r0, live);   // every 10s: held tokens × the live price (server P&L every 30s backs it)
  const legs = [...r.legs].sort((a, b) => (b.usd || 0) - (a.usd || 0));
  const up = r.pnlUsd >= 0;
  const g = r.closed ? 'C' : r.pnlPct >= 25 ? 'A' : r.pnlPct >= 0 ? 'B' : r.pnlPct >= -15 ? 'C' : 'D';
  const card = { key: r.id, kind: 'fuse', title: legs.slice(0, 3).map(l => l.symbol).join(' · ') + (legs.length > 3 ? ` +${legs.length - 3}` : ''),
    subtitle: `${r.name || 'MY FUSE'} · ${up ? '+' : ''}${r.pnlPct.toFixed(1)}%`, rarity: RARITY[g], design: up ? 'aurora' : 'ember', accent: up ? '#19f58f' : '#ff8fa3', accent2: '#f5c451', ...(look || {}),
    glyph: g, motion: up && !r.closed ? 'alive' : 'still', holders: legs.length, edition: r.closed ? 'CLOSED' : 'LIVE', aura,
    art: tokenImageUrls(legPair(legs[0] || {})), fallbackGlyph: String(legs[0]?.symbol || '✦').slice(0, 4) };
  // 🧮 the money as ONE equation: PUT IN → IN CARD + PAID OUT = NOW (paid out = profit that left the card, never the gross takes)
  const paid = r.realizedUsd || 0;
  const back = <div className="fcd-back fcd-live">
    <div className="mc-top"><span>{r.closed ? 'WITHDRAWN' : label || 'LIVE · YOUR MONEY'}</span><span>{m$(r.valueUsd)}</span></div>
    <ul className="fcd-legs">{legs.map(l => <li key={l.pairAddress + (l.sig || '')} className={`fcd-leg ${l.soldUsd != null ? 'is-out' : ''}`}
      data-tip={`${l.symbol}: in ${m$(l.usd)} → now ${m$(l.valueUsd)}${l.priceNow ? ` · price $${fmtPx(l.priceNow)}` : ''}${l.soldUsd != null ? ' · sold' : (l.realizedUsd || 0) > 0 ? ` · took ${m$(l.realizedUsd)}` : ''}${!l.priced && l.soldUsd == null ? ' · no live price' : ''}`}>
      <b>{l.role === 'runner' ? '🏃 ' : l.role === 'anchor' ? '⚓ ' : ''}{l.symbol}</b><span>{m$(l.usd)} → {m$(l.valueUsd)}</span>
      <em className={l.pnlPct >= 0 ? 'up' : 'down'}>{l.soldUsd != null ? 'sold' : `${l.pnlPct >= 0 ? '+' : ''}${l.pnlPct.toFixed(1)}%`}</em></li>)}</ul>
    <MoneyMath putIn={r.costUsd} held={r.valueUsd - paid} paidOut={paid} compact />
    <small className="fcd-note">● Live prices every 10s · {label && label.includes('PAPER') ? 'paper at true fills' : 'exact fills from chain'} · fees apart.</small>
  </div>;
  return <div className="fcd" data-testid={`live-card-${r.id}`}>
    <MetaCard card={card} size="md" interactive flipped={flipped} onFlip={setFlipped} back={back} className="fcd-card" />
    <button type="button" className="fcd-flip" aria-label={flipped ? 'Show front' : 'Show live money'} onClick={() => setFlipped(f => !f)} data-testid={`live-card-flip-${r.id}`}>⟲</button>
  </div>;
}
