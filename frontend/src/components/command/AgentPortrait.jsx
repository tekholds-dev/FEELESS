import React from 'react';
import { apiUrl } from '../../lib/api';
import { thumbOf } from '../../lib/wireface';
import { Ic3 } from '../../lib/icon3d';
import '../../styles/character.css';

// 🎭 An agent's picture wherever it shows in a list: a small still, so a page of agents costs no graphics work. Nothing picked yet: its fallback.
export function AgentPortrait({ cat, size = 56, fallback = null }) {
  const id = cat?.face?.id;
  const live = cat?.live?.on;
  if (!id) return fallback;
  const src = id === 'custom' ? apiUrl(thumbOf(id, cat.id)) : thumbOf(id);
  return <span className={`chr-por${live ? ' is-live' : ''}`} style={{ '--s': `${size}px` }} data-testid="agent-portrait"><img src={src} alt={`${cat?.name || 'Agent'}'s character`} loading="lazy" />{live ? <em data-tip={`Live on ${(cat.live.where || []).join(' and ')}`}><Ic3 e="🔴" /> LIVE</em> : null}</span>;
}
