import React, { useState } from 'react';
import { MetaCard } from './cards/MetaCard';
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

export function FuseCard({ c, style = 'yield', rank = 0 }) {
  const [flipped, setFlipped] = useState(false);
  const [a, b] = ACCENT[style] || ACCENT.yield;
  const p = c.parts || {};
  const card = { key: c.pools.join(), kind: 'fuse', title: c.legs.slice(0, 3).map(l => l.symbol).join(' · ') + (c.legs.length > 3 ? ` +${c.legs.length - 3}` : ''),
    subtitle: `${['🥇', '🥈', '🥉'][rank] || ''} ${style.toUpperCase()} · FIT ${c.fitness}`, rarity: RARITY[p.grade] || 'rare', design: DESIGN[style] || 'holo',
    accent: a, accent2: b, glyph: p.grade || '✦', art: tokenImageUrls(legPair([...c.legs].sort((x, y) => (y.weight || 0) - (x.weight || 0))[0] || {})), motion: rank === 0 ? 'alive' : 'still', holders: c.legs.length, edition: `GEN ${String(c.bornGen ?? 0).padStart(2, '0')}` };
  const back = <div className="fcd-back">
    <div className="mc-top"><span>WHY IT WON</span><span>{p.grade}</span></div>
    <ul>{c.legs.map(l => <li key={l.pairAddress}><b>{l.symbol}</b><span>{Math.round(l.weight)}%</span><em>{usd(l.liquidityUsd)} liq</em></li>)}</ul>
    <dl><dt>APR score</dt><dd>{p.aprScore}</dd><dt>24h move</dt><dd>{p.momentum24h}%</dd><dt>Calm</dt><dd>{p.calm}</dd><dt>Fee drag</dt><dd>{p.feeDragPct}%</dd>{p.impactLegs > 0 && <><dt>Too thin</dt><dd>{p.impactLegs}</dd></>}</dl>
  </div>;
  return <div className="fcd" data-testid={`fuse-card-${rank}`}>
    <MetaCard card={card} size="md" interactive flipped={flipped} onFlip={setFlipped} back={back} className="fcd-card" />
    <button type="button" className="fcd-flip" aria-label={flipped ? 'Show front' : 'Show details'} onClick={() => setFlipped(f => !f)} data-testid={`fuse-card-flip-${rank}`}>⟲</button>
  </div>;
}
