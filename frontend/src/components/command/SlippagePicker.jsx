import React, { useState } from 'react';
import NumInput from '../NumInput';

// Slippage in basis points (string). Presets for meme trading plus a custom % (0.01–50).
export const SLIPPAGE_PRESETS = [['50', '0.5%'], ['100', '1%'], ['500', '5%']];
const MAX_BPS = 5000;

export function SlippagePicker({ value, onChange, disabled, className = '' }) {
  const custom = !SLIPPAGE_PRESETS.some(([bps]) => bps === value);
  const [draft, setDraft] = useState(custom ? String(Number(value) / 100) : '');
  const commit = text => {
    setDraft(text);
    const bps = Math.round(Number(text) * 100);
    if (bps >= 1 && bps <= MAX_BPS) onChange(String(bps));
  };
  return <div className={`slip-pick ${className}`} role="group" aria-label="Max slippage">
    {SLIPPAGE_PRESETS.map(([bps, label]) => <button key={bps} type="button" data-testid={`slippage-${bps}`} className={value === bps ? 'active' : ''} disabled={disabled} onClick={() => { setDraft(''); onChange(bps); }}>{label}</button>)}
    <label className={custom ? 'active' : ''}><NumInput type="text" inputMode="decimal" placeholder="Custom" aria-label="Custom slippage percent" value={draft} disabled={disabled} onChange={e => commit(e.target.value.replace(/[^0-9.]/g, ''))} />%</label>
    {Number(value) >= 1000 && <small className="slip-warn">High slippage: you may get much less than quoted.</small>}
  </div>;
}
