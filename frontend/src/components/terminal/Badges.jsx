import { QuestBadgeCard } from '../QuestBadgeCard';
import { BadgeDetail } from '../QuestBoard';
import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { BadgeIcon } from './BadgeIcon';

const BUILTIN = new Set(['feeless-hq', 'fee-holder', 'feecat-holder', 'rfee-holder', 'fee-whale', 'rides-with-fee', 'caller', 'sharp-caller', 'feeless-launcher', 'trusted-creator', 'flagged-creator', 'blocklisted', 'airdrop-recipient']);

const cache = new Map();
export function useBadges(address) {
  const [badges, setBadges] = useState(() => cache.get(address)?.badges || []);
  useEffect(() => {
    if (!address || typeof fetch !== 'function') return undefined;
    let alive = true;
    const hit = cache.get(address);
    if (hit && Date.now() - hit.at < 300000) { setBadges(hit.badges); return undefined; }
    const req = hit?.pending || fetch(apiUrl(`/api/reputation/badges/${address}`)).then(r => (r.ok ? r.json() : { badges: [] })).catch(() => ({ badges: [] }));
    cache.set(address, { ...(hit || {}), pending: req });
    req.then(d => { cache.set(address, { at: Date.now(), badges: d.badges || [] }); if (alive) setBadges(d.badges || []); });
    return () => { alive = false; };
  }, [address]);
  return badges;
}

const order = (badges, featured) => {
  if (!featured?.length) return badges;
  const pick = featured.map(id => badges.find(b => b.id === id)).filter(Boolean);
  return [...pick, ...badges.filter(b => !featured.includes(b.id))];
};

// Full shelf (profiles) or compact icons (chat). Every badge carries its evidence as a tooltip
// and has a small live animation; featured badges (up to 3, chosen by the owner) lead.
export function Badges({ address, compact = false, max = 3, featured }) {
  const badges = order(useBadges(address), featured);
  if (!badges.length) return null;
  // Chat: small card chips (tone ring + emblem), hover/focus shows the name and why. Emblem = hand-made SVG for
  // built-ins, the card glyph for custom badges and season cards.
  if (compact) return <span className="badge-chips" data-testid="chat-badges">{badges.slice(0, max).map(b => <i key={b.id} tabIndex={0} className={`badge-chip tone-${b.tone} ${b.rarity ? `r-${b.rarity}` : ''}`} data-tip={`${b.label}${b.why ? ` — ${b.why}` : ''}`} aria-label={b.label}>
    {b.art ? <img className="badge-chip-art" src={`${b.art}.jpg`} alt="" loading="lazy" /> : BUILTIN.has(b.id) ? <BadgeIcon id={b.id} tone={b.tone} size={13} /> : <span>{b.icon || '⭐'}</span>}</i>)}</span>;
  return <div className="badge-shelf" data-testid="badge-shelf">{badges.map((b, i) => <span key={b.id} className={`badge-pill tone-${b.tone} ${featured?.includes(b.id) ? 'is-featured' : ''}`} style={{ animationDelay: `${i * 0.35}s` }} title={b.why}><i>{b.art ? <img className="badge-chip-art" src={`${b.art}.jpg`} alt="" loading="lazy" /> : <BadgeIcon id={b.id} tone={b.tone} size={15} />}</i>{b.label}</span>)}</div>;
}

// Featured badges as spinning 3D artifacts (profile header).
const qb = b => ({ id: b.id, set: b.id.startsWith('frsv-') ? 'frsv' : 'feeless', name: b.label, tier: b.rarity || 'rare', art: b.art, earned: true, tasks: [], perks: [], xp: 0, pct: 100 });

export function BadgeArtifacts({ address, featured }) {
  const badges = useBadges(address);
  const [open, setOpen] = useState(null);
  const RANK_Q = { mythic: 5, legendary: 4, epic: 3, rare: 2, common: 1 };
  let pick = (featured || []).map(id => badges.find(b => b.id === id)).filter(Boolean).slice(0, 3);
  // Nothing featured yet: showcase the 3 rarest quest badges earned, so every profile shows its story.
  if (!pick.length) pick = badges.filter(b => b.art).sort((x, y) => (RANK_Q[y.rarity] || 0) - (RANK_Q[x.rarity] || 0)).slice(0, 3);
  if (!pick.length) return null;
  return <><div className="badge-artifacts" data-testid="badge-artifacts">{pick.map((b, i) => b.art
    ? <button type="button" key={b.id} className="artifact-card" title={`${b.label} — ${b.why}`} onClick={() => setOpen(b)}><QuestBadgeCard size="xs" b={qb(b)} /></button>
    : <div key={b.id} className={`artifact tone-${b.tone}`} title={`${b.label} — ${b.why}`} style={{ animationDelay: `${i * -2}s` }}>
    <div className="artifact-coin" style={{ animationDelay: `${i * -1.3}s` }}><span className="face front"><BadgeIcon id={b.id} tone={b.tone} size={30} /></span></div>
    <small>{b.label}</small>
  </div>)}</div>{open && <BadgeDetail b={{ ...qb(open), tasks: [], perks: [] }} onClose={() => setOpen(null)} />}</>;
}
