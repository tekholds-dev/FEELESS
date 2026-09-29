import React from 'react';
import { SHIELD_LABEL } from '../../lib/tradeIntel';

// Verdict + reasons from on-chain forensics. For 'danger' the parent requires an explicit acknowledgement.
export function ShieldNote({ shield, ack, onAck }) {
  if (!shield) return null;
  return <div className={`shield-note lvl-${shield.level}`} data-testid="rug-shield">
    <b>{SHIELD_LABEL[shield.level] || SHIELD_LABEL.unknown}</b>
    {shield.reasons?.length > 0 && <ul>{shield.reasons.slice(0, 3).map(r => <li key={r}>{r}</li>)}</ul>}
    {shield.level === 'danger' && onAck && <label className="shield-ack"><input type="checkbox" checked={Boolean(ack)} onChange={e => onAck(e.target.checked)} data-testid="rug-shield-ack" />I understand the risk. Let me buy anyway.</label>}
  </div>;
}
