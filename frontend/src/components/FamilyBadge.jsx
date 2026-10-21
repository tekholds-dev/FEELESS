import React from 'react';
import '../styles/familyBadge.css';

// 🌹 THE FAMILY BADGE (crews.py PARTS / badge_view — change both): one badge per family, every part earned from TRACKED numbers. Drawn the same
// everywhere (board, podium, chips, profile): emblem in a frame, the two family colors, an FX layer, the tag, the motto and the rank chips it earned.
export const EMBLEM = { rose: '🌹', skull: '💀', snake: '🐍', dice: '🎲', gun: '🔫', hat: '🎩', scorp: '🦂', dragon: '🐉', crown: '👑', diamond: '💎', sword: '⚔', wolf: '🐺', lion: '🦁' };
const FRAME = { iron: 'fb-iron', silver: 'fb-silver', gold: 'fb-gold', blood: 'fb-blood', holo: 'fb-holo', black: 'fb-black', warlord: 'fb-warlord' };   // literal names (cssHygiene)
const FX = { none: '', smoke: 'fx-smoke', embers: 'fx-embers', lightning: 'fx-lightning', rain: 'fx-rain', gunsmoke: 'fx-gunsmoke' };
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
export function FamilyBadge({ b, size = 'md', chips = true }) {
  if (!b) return null;
  const fx = FX[b.fx] || '';
  return <span className={`fbadge ${FRAME[b.frame] || 'fb-iron'} ${size === 'sm' ? 'is-sm' : size === 'lg' ? 'is-lg' : ''}`} style={{ '--c1': b.c1 || '#15d16a', '--c2': b.c2 || '#ffd36b' }} data-testid="family-badge" aria-label={`${b.name || 'family'} badge`}>
    <span className="fb-ring" aria-hidden="true" />
    {fx ? <span className={`fb-fx ${fx}`} aria-hidden="true">{[0, 1, 2, 3, 4, 5].map(i => <i key={i} style={{ '--i': i }} />)}</span> : null}
    <span className="fb-core"><span className="fb-emblem">{EMBLEM[b.emblem] || '🌹'}</span>{size !== 'sm' && b.tag ? <b className="fb-tag">{b.tag}</b> : null}</span>
    {size === 'lg' && b.motto ? <em className="fb-motto">“{b.motto}”</em> : null}
    {chips && size !== 'sm' && rankChips(b.ranks).length ? <span className="fb-chips">{rankChips(b.ranks).map(([i, t]) => <small key={t}>{i} {t}</small>)}</span> : null}
  </span>;
}
