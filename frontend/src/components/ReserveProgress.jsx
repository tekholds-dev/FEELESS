import React from 'react';
import { useWallet } from '../hooks/useWallet';
import { useQuests } from './QuestBoard';
import { perkLine } from './QuestBadgeCard';

// "$FEE → Fee Reserve" ladder: the next FRSV badge you can reach just by holding more $FEE, how far you are, and what
// it unlocks. Uses the same quest data as the Badges tab (no extra requests per surface).
export function nextReserveStep(badges = [], feeUsd = 0) {
  const steps = badges.filter(b => b.set === 'frsv' && !b.earned).map(b => {
    const hold = b.tasks.find(t => t.metric === 'fee_usd');
    const other = b.tasks.filter(t => t.metric !== 'fee_usd' && !t.done);
    return hold && hold.target > feeUsd ? { b, need: hold.target - feeUsd, target: hold.target, onlyHold: !other.length } : null;
  }).filter(Boolean);
  // Prefer badges where holding is the only thing missing, then the cheapest.
  return steps.sort((x, y) => (y.onlyHold - x.onlyHold) || (x.need - y.need))[0] || null;
}

export function ReserveProgress() {
  const { wallet } = useWallet() || {};
  const [d] = useQuests(wallet?.address);
  if (!d) return null;
  const fee = d.metrics?.fee_usd || 0;
  const step = nextReserveStep(d.badges, fee);
  if (!step) return null;
  const pct = Math.min(100, (fee / step.target) * 100);
  return <div className="m-card reserve-progress" data-testid="reserve-progress">
    <div className="m-row"><span className="m-label">FEE RESERVE · NEXT UNLOCK</span><b>{step.b.name}</b>{step.b.perks?.map((p, i) => <span key={i} className="m-chip ok">{perkLine(p)}</span>)}</div>
    <i className="qb-bar big"><i style={{ transform: `scaleX(${pct / 100})` }} /></i>
    <small className="m-dim">You hold ${fee.toLocaleString(undefined, { maximumFractionDigits: 2 })} of $FEE · hold ${step.need.toLocaleString(undefined, { maximumFractionDigits: 0 })} more{step.onlyHold ? ' to unlock it' : ' (plus its other tasks)'}</small>
  </div>;
}
