import React from 'react';
import { impactGate } from '../../lib/impactGuard';

// Shown under a quote when the price impact is heavy: a tick to accept, or a hard stop.
export function ImpactNote({ pct, ack, onAck }) {
  const g = impactGate(pct);
  if (g === 'ok') return null;
  return <div className={`impact-note ${g}`} data-testid="impact-note" role="status">
    <b>{g === 'block' ? `⛔ ${pct.toFixed(1)}% price impact — blocked` : `⚠ ${pct.toFixed(1)}% price impact`}</b>
    <span>{g === 'block' ? 'The pool is too thin for this size. Trade a smaller amount.' : 'You lose this much to the pool on entry. Smaller size = less impact.'}</span>
    {g === 'ack' && <label><input type="checkbox" checked={Boolean(ack)} onChange={e => onAck(e.target.checked)} data-testid="impact-ack" />I accept {pct.toFixed(1)}% price impact</label>}
  </div>;
}
