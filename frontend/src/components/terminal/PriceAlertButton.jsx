import React, { useState } from 'react';
import { toast } from 'sonner';
import { BellPlus } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { currentSubscription, enablePush, readPushPrefs } from '../../lib/push';

// Set a price target right from the chart → push to your phone when it hits.
export function PriceAlertButton({ pair }) {
  const { watchlist = [], toggle, updateWatch, has } = useWorkspace() || {};
  const [open, setOpen] = useState(false);
  const [dir, setDir] = useState('above');
  const now = Number(pair?.priceUsd) || 0;
  const [target, setTarget] = useState(() => (now ? (now * 1.2).toPrecision(4) : ''));
  const save = async () => {
    const v = Number(target);
    if (!(v > 0)) return;
    try {
      if (!has?.(pair)) toggle?.(pair);
      setTimeout(() => updateWatch?.(pair, { alerts: { [dir]: v, [dir === 'above' ? 'below' : 'above']: null } }), 0);
      if (!(await currentSubscription())) await enablePush([...watchlist, { ...pair, alerts: { [dir]: v } }], readPushPrefs());
      toast.success(`🔔 Alert set: ${pair.baseToken.symbol} ${dir === 'above' ? '≥' : '≤'} $${v}`);
      setOpen(false);
    } catch (e) { toast.error(e.message); }
  };
  return <span className="pa-wrap"><button type="button" className="chart-meta-btn" data-testid="price-alert" onClick={() => setOpen(o => !o)} title="Price alert"><BellPlus size={13} />Alert</button>
    {open && <div className="pa-pop" data-testid="price-alert-pop"><small>Notify me when ${pair.baseToken.symbol} goes</small>
      <div className="pa-dir">{['above', 'below'].map(d => <button key={d} type="button" className={dir === d ? 'active' : ''} onClick={() => { setDir(d); setTarget(now ? (now * (d === 'above' ? 1.2 : 0.8)).toPrecision(4) : ''); }}>{d}</button>)}</div>
      <input inputMode="decimal" value={target} onChange={e => setTarget(e.target.value)} /><small>now ${now ? now.toPrecision(4) : '—'}</small>
      <button type="button" className="btn-primary" onClick={save}>Set alert</button></div>}
  </span>;
}
