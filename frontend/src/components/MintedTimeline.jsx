import React from 'react';
import { useQuests } from './QuestBoard';
import { BadgeArt } from './BadgeArt';

// Profile story: every badge earned (with its edition number) and every trophy, newest first. Same quest data as the
// Badges tab (one shared request); granted (HQ) badges are left out so the story is what the wallet actually did.
export function timelineOf(d) {
  if (!d) return [];
  const byId = Object.fromEntries((d.badges || []).map(b => [b.id, b]));
  const badges = Object.entries(d.earnedAt || {}).map(([id, at]) => ({ id, at, b: byId[id] })).filter(x => x.b && x.b.earned && !x.b.granted)
    .map(x => ({ key: x.id, at: x.at, kind: 'badge', title: x.b.name, art: x.b.art, edition: d.editions?.[x.id], tier: x.b.tier }));
  const trophies = (d.trophies || []).map(t => ({ key: t.id, at: t.at, kind: 'trophy', title: t.name, glyph: t.glyph, tier: t.rarity }));
  return [...badges, ...trophies].sort((a, b) => b.at - a.at);
}

export function MintedTimeline({ address }) {
  const [d] = useQuests(address);
  const rows = timelineOf(d).slice(0, 12);
  if (!rows.length) return null;
  return <section className="wp-card minted-timeline" data-testid="minted-timeline"><h3>Minted</h3><ol>{rows.map(r => <li key={r.key} className={`tier-${r.tier}`}>
    {r.kind === 'badge' ? <BadgeArt art={r.art} name={r.title} size="sm" /> : <span className="mt-glyph">{r.glyph}</span>}
    <span><b>{r.title}</b>{r.edition ? <em className="mc-edition"> #{String(r.edition).padStart(3, '0')}</em> : null}<small>{new Date(r.at * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</small></span></li>)}</ol></section>;
}
