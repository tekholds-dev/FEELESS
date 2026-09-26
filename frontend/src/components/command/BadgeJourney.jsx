import React, { useEffect, useState } from 'react';
import { apiUrl } from '../../lib/api';

const TIERS = { 1: 'Rookie', 2: 'Trencher', 3: 'Veteran', 4: 'Legend' };

// Progress toward a badge from real wallet data (only where we can measure it).
function progressFor(id, pr) {
  if (!pr) return null;
  if (id === 'fee-holder') return { now: pr.feeUsd, goal: 1, fmt: v => `$${v.toFixed(2)}` };
  if (id === 'fee-whale') return { now: pr.feeUsd, goal: 1000, fmt: v => `$${Math.round(v).toLocaleString()}` };
  if (id === 'caller') return { now: pr.calls, goal: 1, fmt: v => `${v} call${v === 1 ? '' : 's'}` };
  if (id === 'sharp-caller') return { now: Math.min(pr.calls, 5) / 5 * 0.5 + Math.min(pr.hitRate, 0.5), goal: 1, fmt: () => `${pr.calls}/5 calls · ${Math.round(pr.hitRate * 100)}% / 50% hit` };
  return null;
}

export function BadgeJourney({ address, mine }) {
  const [catalog, setCatalog] = useState([]);
  const [mineBadges, setMineBadges] = useState(null);
  useEffect(() => {
    fetch(apiUrl('/api/reputation/badges/catalog')).then(r => r.json()).then(d => setCatalog(d.catalog || [])).catch(() => {});
    fetch(apiUrl(`/api/reputation/badges/${address}`)).then(r => r.json()).then(setMineBadges).catch(() => setMineBadges({ badges: [] }));
  }, [address]);
  if (!catalog.length) return null;
  const earned = new Set((mineBadges?.badges || []).map(b => (String(b.id).startsWith('custom-') ? 'custom' : b.id)));
  const got = catalog.filter(c => earned.has(c.id)).length;
  const tiers = [1, 2, 3, 4].map(t => ({ t, items: catalog.filter(c => c.tier === t) }));
  return <section className="wp-card wp-journey" data-testid="badge-journey">
    <div className="wpj-head"><h3>Badge journey</h3><span className="wpj-count"><b>{got}</b>/{catalog.length} unlocked</span></div>
    <div className="wpj-bar"><i style={{ width: `${(got / catalog.length) * 100}%` }} /></div>
    <p className="wp-bio">{mine ? 'Every badge is earned from real on-chain or FEELESS activity — here is how to unlock the rest.' : 'Badges are earned from real wallet activity. Here is how.'}</p>
    <div className="wpj-path">{tiers.map(({ t, items }) => <div key={t} className="wpj-tier"><small className="wpj-tier-name">Tier {t} · {TIERS[t]}</small>
      {items.map(c => { const on = earned.has(c.id); const pg = !on && progressFor(c.id, mineBadges?.progress); const pct = pg ? Math.max(0, Math.min(100, (pg.now / pg.goal) * 100)) : 0;
        return <div key={c.id} className={`wpj-badge ${on ? 'on' : 'off'} tone-${c.tone}`}>
          <span className="wpj-icon">{c.icon}</span>
          <div><b>{c.label}{on && <em>✓ earned</em>}</b><small>{c.how}</small>
            {pg && <div className="wpj-prog"><i style={{ width: `${pct}%` }} /><span>{pg.fmt(pg.now)}</span></div>}</div>
        </div>; })}
    </div>)}</div>
  </section>;
}
