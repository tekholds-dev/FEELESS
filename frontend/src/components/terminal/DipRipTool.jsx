import React, { useState } from 'react';
import { toast } from 'sonner';
import { TrendingDown, TrendingUp } from 'lucide-react';
import { useWorkspace } from '../../hooks/useWorkspace';
import { currentSubscription, enablePush, readPushPrefs } from '../../lib/push';

const DIPS = [10, 20, 30];
const RIPS = [25, 50, 100];

// Meta trading tool: one-tap "buy the dip" / "sell the rip" alert presets.
// FEELESS is non-custodial — this arms a push alert at the target price, it never trades for you.
export function DipRipTool({ pair }) {
  const { watchlist = [], toggle, updateWatch, has } = useWorkspace() || {};
  const [armed, setArmed] = useState(null);
  const now = Number(pair?.priceUsd) || 0;
  const arm = async (pct, dir) => {
    if (!now) { toast.error('No live price yet.'); return; }
    const target = dir === 'down' ? now * (1 - pct / 100) : now * (1 + pct / 100);
    const key = dir === 'down' ? 'below' : 'above';
    try {
      if (!has?.(pair)) toggle?.(pair);
      setTimeout(() => updateWatch?.(pair, { alerts: { [key]: target } }), 0);
      if (!(await currentSubscription())) await enablePush([...watchlist, { ...pair, alerts: { [key]: target } }], readPushPrefs());
      setArmed(`${dir === 'down' ? 'Dip' : 'Rip'} ${pct}%`);
      toast.success(`🎯 Armed: push alert when ${pair.baseToken?.symbol} ${dir === 'down' ? 'dips' : 'rips'} ${pct}% (~$${target.toPrecision(4)})`);
    } catch (e) { toast.error(e.message); }
  };
  return <div className="dip-rip" data-testid="dip-rip-tool">
    <div className="dr-head"><span>Buy the Dip</span><span>Sell the Rip</span></div>
    <div className="dr-row">
      {DIPS.map(p => <button key={p} type="button" className={armed === `Dip ${p}%` ? 'active' : ''} onClick={() => arm(p, 'down')}><TrendingDown size={12} />-{p}%</button>)}
    </div>
    <div className="dr-row">
      {RIPS.map(p => <button key={p} type="button" className={armed === `Rip ${p}%` ? 'active' : ''} onClick={() => arm(p, 'up')}><TrendingUp size={12} />+{p}%</button>)}
    </div>
    <small className="dr-note">Arms a push alert at that price — non-custodial, you tap Buy/Sell yourself when it fires.</small>
  </div>;
}
