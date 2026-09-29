import React from 'react';
import { Zap } from 'lucide-react';
import { useReputation } from '../../lib/reputation';

// One definition everywhere: the bolt is a compact meta signal, never a generic Pump badge.
// It requires a healthy creator reputation plus either top-three discovery rank or a real callout.
export function BoltSignal({ pair, rank, callCount = 0, size = 13 }) {
  const rep = useReputation(pair);
  const reputable = rep && ['trusted', 'veteran', 'building'].includes(rep.badge) && Number(rep.score) >= 50;
  const top = Number(rank) > 0 && Number(rank) <= 3;
  if (!reputable || (!top && callCount < 1)) return null;
  const metaScore = Math.min(99, Math.round(Number(rep.score) + (top ? 5 : 0) + Math.min(12, callCount * 3)));
  const reason = [top ? `top ${rank}` : '', callCount ? `${callCount} callout${callCount === 1 ? '' : 's'}` : '', `rep ${rep.score}`].filter(Boolean).join(' · ');
  return <i className="pink-bolt" title={`Bolt ${metaScore} · ${reason}`} data-testid="bolt-signal"><Zap size={size} />{callCount > 0 ? callCount : ''}</i>;
}

export function BoltLegend() {
  return <span className="bolt-legend" title="The Bolt appears only when reputation is 50+ and the coin is top-three or has a tracked callout."><Zap size={11} /> Bolt = rep 50+ · top 3 or called</span>;
}
