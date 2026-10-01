import React, { useState } from 'react';
import { MetaCard } from './cards/MetaCard';

const DESIGN = { common: 'obsidian', rare: 'circuit', epic: 'aurora', legendary: 'holo', mythic: 'ember' };
const ACCENT = { feeless: ['#19f58f', '#f5c451'], frsv: ['#b46bff', '#f5c451'] };
export const perkLine = p => (p.kind === 'fee_discount' ? `−${p.pct}% FEELESS fee` : p.kind === 'chat_bg' ? `${p.id} chat background` : p.id);

// A quest badge as a FEELESS card: the art lives in the crest circle (the same circle chat shows), rarity sets the frame,
// earned cards come alive (sweep + glow), locked ones stay dim. Back = the tasks and perks. GIF only while hovered/open.
export function QuestBadgeCard({ b, holders, size = 'md', interactive = false, live = false, onOpen }) {
  const [hot, setHot] = useState(false);
  const [a, c] = ACCENT[b.set] || ACCENT.feeless;
  const card = {
    key: b.id, kind: 'badge', title: b.name, subtitle: b.set === 'frsv' ? 'FEE RESERVE BADGE' : 'FEELESS BADGE', rarity: b.tier,
    design: DESIGN[b.tier] || 'holo', accent: a, accent2: c, art: b.art ? `${b.art}.${hot || live ? 'gif' : 'jpg'}` : null,
    holders: holders ?? 0, motion: b.earned ? 'alive' : 'still',
  };
  const back = <div className="qbc-back">
    <div className="mc-top"><span>{b.earned ? 'EARNED' : `${b.pct}% DONE`}</span><span>+{b.xp} XP</span></div>
    <ul>{(b.tasks || []).map(t => <li key={t.id} className={t.done ? 'done' : ''}><span>{t.done ? '✓' : '○'} {t.label}</span><i><i style={{ transform: `scaleX(${(t.pct ?? 0) / 100})` }} /></i></li>)}</ul>
    {b.perks?.length > 0 && <p className="mc-how">Perks: {b.perks.map(perkLine).join(' · ')}</p>}
  </div>;
  return <div className={`qbc ${b.earned ? 'is-earned' : 'is-locked'}`} data-testid={`badge-${b.id}`} onMouseEnter={() => setHot(true)} onMouseLeave={() => setHot(false)}
    onFocus={() => setHot(true)} onBlur={() => setHot(false)} onDoubleClick={onOpen}>
    <MetaCard card={card} size={size} interactive={interactive} back={back} onFlip={interactive ? undefined : onOpen} />
  </div>;
}
