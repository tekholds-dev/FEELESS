import React, { useEffect, useId, useState } from 'react';
import { apiUrl } from '../lib/api';

const RARITY = {
  legendary: { label: 'Legendary', c1: '#ff5ad1', c2: '#f5c542', sides: 6 },
  epic: { label: 'Epic', c1: '#b388ff', c2: '#7cc8ff', sides: 8 },
  rare: { label: 'Rare', c1: '#7cc8ff', c2: '#12c07a', sides: 0 },
  common: { label: 'Common', c1: '#8fa89a', c2: '#cfd8dc', sides: 0 },
};
const poly = (n, r, cx = 50, cy = 50) => Array.from({ length: n }, (_, i) => { const a = (Math.PI * 2 * i) / n - Math.PI / 2; return `${cx + r * Math.cos(a)},${cy + r * Math.sin(a)}`; }).join(' ');

// Badge art: shape = rarity (hexagon/octagon/round), colors = rarity + season accent, glyph = theme.
// Legendary + epic get a slowly spinning halo so they read as special at a glance.
export function BadgeArt({ item, size = 64 }) {
  const r = RARITY[item.rarity] || RARITY.common; const id = `ba${useId().replace(/[^a-zA-Z0-9]/g, '')}`;
  const shape = r.sides ? <polygon points={poly(r.sides, 38)} fill={`url(#${id})`} stroke="#fff3" strokeWidth="2" /> : <circle cx="50" cy="50" r="38" fill={`url(#${id})`} stroke="#fff3" strokeWidth="2" />;
  return <svg className={`badge-art rarity-${item.rarity}`} width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`${r.label} ${item.name}`}>
    <defs><linearGradient id={id} x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor={r.c1} /><stop offset=".55" stopColor={item.accent || r.c2} /><stop offset="1" stopColor={r.c2} /></linearGradient></defs>
    {(item.rarity === 'legendary' || item.rarity === 'epic') && <g className="badge-halo"><circle cx="50" cy="50" r="47" fill="none" stroke={r.c1} strokeWidth="1.5" strokeDasharray="4 7" /></g>}
    {shape}
    {item.imageUrl ? <><clipPath id={`${id}c`}><circle cx="50" cy="50" r="30" /></clipPath><image href={item.imageUrl} x="20" y="20" width="60" height="60" preserveAspectRatio="xMidYMid slice" clipPath={`url(#${id}c)`} /></>
      : <><circle cx="50" cy="50" r="27" fill="#04110b" opacity=".55" /><text x="50" y="59" textAnchor="middle" fontSize="28">{item.glyph}</text></>}
  </svg>;
}

// Card thumbnail for image badges (portrait art) — small, tilts on hover.
export function BadgeThumb({ item, size = 64 }) {
  if (!item.imageUrl) return <BadgeArt item={item} size={size} />;
  return <span className={`badge-thumb rarity-${item.rarity}`} style={{ width: size * 1.1 }}><img src={item.imageUrl} alt={item.name} loading="lazy" /></span>;
}

// Focus view: the badge over a blurred page. Click the card to flip between art and lore; click
// outside (or press Esc) to close.
export function BadgeDetail({ item, onClose }) {
  const [flipped, setFlipped] = useState(false);
  useEffect(() => { setFlipped(false); if (!item) return undefined; const k = e => e.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [item, onClose]);
  if (!item) return null;
  const r = RARITY[item.rarity] || RARITY.common;
  const facts = <dl>
    <div><dt>Season</dt><dd>{item.seasonName || item.season}</dd></div>
    {item.how && <div><dt>Earned by</dt><dd>{item.how}{item.rank ? ` (rank #${item.rank})` : ''}</dd></div>}
    {item.score != null && <div><dt>Points</dt><dd>{Number(item.score).toLocaleString()}</dd></div>}
    {item.badgeRewardPct > 0 && <div><dt>Reserve reward plan</dt><dd>{Number(item.badgeRewardPct).toLocaleString()}% of the season Fee Reserve pool shared by eligible badge holders · planned, not yet paid</dd></div>}
    {item.at && <div><dt>Dropped</dt><dd>{new Date(item.at * 1000).toLocaleDateString()}</dd></div>}
    {item.holders != null && <div><dt>Holders</dt><dd>{item.holders}</dd></div>}
  </dl>;
  return <div className="badge-modal" role="dialog" aria-modal="true" onClick={onClose}>
    <div className={`badge-flip ${flipped ? 'is-flipped' : ''} rarity-${item.rarity}`} style={{ '--r1': r.c1, '--r2': r.c2 }} onClick={e => { e.stopPropagation(); setFlipped(f => !f); }} title="Click to flip">
      <div className="badge-face front">{item.imageUrl ? <img src={item.imageUrl} alt={item.name} /> : <div className="badge-face-art"><BadgeArt item={item} size={150} /><h3>{item.name}</h3></div>}<span className="badge-flip-hint">tap to read the lore ↻</span></div>
      <div className="badge-face back"><span className="badge-rarity">{r.label}{item.week ? ` · Week ${item.week}` : ''}</span><h3>{item.name}</h3><p>{item.story}</p>{facts}<span className="badge-flip-hint">tap to flip back ↻</span></div>
    </div>
  </div>;
}

// The weekly drop schedule for the live season, each drop previewed at Legendary.
export function WeeklyDrops() {
  const [d, setD] = useState(null); const [open, setOpen] = useState(null);
  useEffect(() => { fetch(apiUrl('/api/reputation/season/drops')).then(r => r.json()).then(setD).catch(() => {}); }, []);
  if (!d?.weeks?.length) return null;
  return <section className="season-card weekly-drops" data-testid="weekly-drops">
    <h3>Weekly drops <small>a new badge every week · rarity by how you place</small></h3>
    <div className="drops-row">{d.weeks.map(w => { const item = { ...w, rarity: 'legendary', accent: d.accent, seasonName: `Season ${d.season.slice(1)}`, how: 'Top 3 → Legendary · top 10% → Epic · 300+ pts → Rare · 50+ pts → Common', holders: w.holders };
      return <button key={w.week} type="button" className={`drop ${w.status}`} onClick={() => setOpen(item)}><BadgeThumb item={item} size={72} /><b>{w.name}</b><small>Week {w.week} · {w.status === 'live' ? 'LIVE' : w.status === 'distributed' ? `${w.holders} holders` : new Date(w.start * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</small></button>; })}</div>
    <div className="drops-rarities">{d.rarities.map(([k, how]) => <span key={k} className={`rarity-chip rarity-${k}`}>{RARITY[k].label}<small>{how}</small></span>)}</div>
    <BadgeDetail item={open} onClose={() => setOpen(null)} />
  </section>;
}

// A wallet's vault: every season badge and weekly drop it has ever earned.
export function SeasonVault({ address }) {
  const [items, setItems] = useState(null); const [open, setOpen] = useState(null);
  useEffect(() => { if (!address) return; fetch(apiUrl(`/api/reputation/collection/${address}`)).then(r => r.json()).then(d => setItems(d.items || [])).catch(() => setItems([])); }, [address]);
  return <section className="wp-card season-vault" data-testid="season-vault">
    <h3>Vault <small>{items ? `${items.length} item${items.length === 1 ? '' : 's'}` : ''}</small></h3>
    {items == null ? <p className="wp-bio">Opening the vault…</p> : !items.length ? <p className="wp-bio">Empty for now — weekly drops land here every Monday of a season.</p>
      : <div className="vault-grid">{items.map(it => <button key={it.id} type="button" onClick={() => setOpen(it)} title={it.name}><BadgeThumb item={it} size={56} /><small>{it.name}</small></button>)}</div>}
    <BadgeDetail item={open} onClose={() => setOpen(null)} />
  </section>;
}
