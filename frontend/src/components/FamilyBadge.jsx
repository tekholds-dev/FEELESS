import React from 'react';
import '../styles/familyBadge.css';
import { FamilyCrest } from './FamilyCrest';

// 🌹 THE FAMILY BADGE (crews.py PARTS / badge_view — change both): one badge per family, every part earned from TRACKED numbers. Drawn the same
// everywhere (board, podium, chips, profile, cards): the SVG crest (FamilyCrest — shape, field, drawn charge, metal frame, banner with the tag),
// an earned FX layer behind it, the motto and the rank chips it earned.
const FX = { none: '', smoke: 'fx-smoke', embers: 'fx-embers', lightning: 'fx-lightning', rain: 'fx-rain', gunsmoke: 'fx-gunsmoke' };   // literal names (cssHygiene)
const PX = { sm: 24, md: 60, lg: 150 };
// pure: the rank chips a badge shows (only what the family really earned)
export function rankChips(r) {
  const out = [];
  if (!r) return out;
  if (r.crowns) out.push(['👑', `${r.crowns}× #1`]);
  if (r.podiums) out.push(['🏆', `${r.podiums} podium${r.podiums > 1 ? 's' : ''}`]);
  if (r.best && !r.crowns) out.push(['⭐', `best #${r.best}`]);
  if (r.points) out.push(['🎯', `${r.points} pts`]);
  return out;
}
export function FamilyBadge({ b, size = 'md', chips = true, px, grid = false }) {
  if (!b) return null;
  const fx = size !== 'sm' ? FX[b.fx] || '' : '';
  return <span className={`fbadge is-${size}`} data-testid="family-badge" aria-label={`${b.name || 'family'} badge`}>
    {fx ? <span className={`fb-fx ${fx}`} aria-hidden="true">{[0, 1, 2, 3, 4, 5].map(i => <i key={i} style={{ '--i': i }} />)}</span> : null}
    <FamilyCrest b={b} px={px || PX[size] || 60} banner={size !== 'sm'} grid={grid} sheen={size !== 'sm'} title={`${b.name || 'family'} crest`} />
    {size === 'lg' && b.motto ? <em className="fb-motto">“{b.motto}”</em> : null}
    {chips && size !== 'sm' && rankChips(b.ranks).length ? <span className="fb-chips">{rankChips(b.ranks).map(([i, t]) => <small key={t}>{i} {t}</small>)}</span> : null}
  </span>;
}
