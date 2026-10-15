// ⚛ The forge's card = the REAL live Fuse card (its tier look, aura and the real-time effects every Fuse card runs: CardLive heat, live %,
// ⟲ flip to its live book). Lazy-loaded by HomeEngine so Home does not carry the whole Arena bundle up front.
import React from 'react';
import { primeRow, TIER } from './ArenaPrime';
import { LiveFuseCard } from './FuseCard';

export default function HomeForgeCard({ card }) {
  if (!card) return null;
  const t = TIER[card.tier] || TIER.gold;
  return <LiveFuseCard r={primeRow(card)} aura={t.aura} look={t.look} label={card.real ? '💵 REAL · FUSE WALLET' : '📄 PAPER · TRUE FILLS'} serverOnly={!!card.real}
    mini={{ kind: 'prime', tpl: card.tpl, name: card.label }} />;
}
