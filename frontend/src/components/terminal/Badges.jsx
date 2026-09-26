import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';
import { BadgeIcon } from './BadgeIcon';

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
  if (compact) return <span className="badge-icons">{badges.slice(0, max).map((b, i) => <i key={b.id} className={`tone-${b.tone}`} style={{ animationDelay: `${i * 0.4}s` }} title={`${b.label} — ${b.why}`}><BadgeIcon id={b.id} tone={b.tone} size={14} /></i>)}</span>;
  return <div className="badge-shelf" data-testid="badge-shelf">{badges.map((b, i) => <span key={b.id} className={`badge-pill tone-${b.tone} ${featured?.includes(b.id) ? 'is-featured' : ''}`} style={{ animationDelay: `${i * 0.35}s` }} title={b.why}><i><BadgeIcon id={b.id} tone={b.tone} size={15} /></i>{b.label}</span>)}</div>;
}

// Featured badges as spinning 3D artifacts (profile header).
export function BadgeArtifacts({ address, featured }) {
  const badges = useBadges(address);
  const pick = (featured || []).map(id => badges.find(b => b.id === id)).filter(Boolean).slice(0, 3);
  if (!pick.length) return null;
  return <div className="badge-artifacts" data-testid="badge-artifacts">{pick.map((b, i) => <div key={b.id} className={`artifact tone-${b.tone}`} title={`${b.label} — ${b.why}`} style={{ animationDelay: `${i * -2}s` }}>
    <div className="artifact-coin" style={{ animationDelay: `${i * -1.3}s` }}><span className="face front"><BadgeIcon id={b.id} tone={b.tone} size={30} /></span></div>
    <small>{b.label}</small>
  </div>)}</div>;
}
