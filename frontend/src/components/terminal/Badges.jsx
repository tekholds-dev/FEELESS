import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';

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

// Full shelf (profiles) or compact icons (chat). Each badge carries its evidence as a tooltip.
export function Badges({ address, compact = false, max = 3 }) {
  const badges = useBadges(address);
  if (!badges.length) return null;
  if (compact) return <span className="badge-icons">{badges.slice(0, max).map(b => <i key={b.id} className={`tone-${b.tone}`} title={`${b.label} — ${b.why}`}>{b.icon}</i>)}</span>;
  return <div className="badge-shelf" data-testid="badge-shelf">{badges.map(b => <span key={b.id} className={`badge-pill tone-${b.tone}`} title={b.why}><i>{b.icon}</i>{b.label}</span>)}</div>;
}
