import React, { useEffect, useMemo, useState } from 'react';
import { useHeldList } from '../../lib/myHoldings';
import { formatUSD, formatPct } from '../../lib/dexscreener';
import { DipRipTool } from './DipRipTool';

// Radar › Signals, first section: the coins YOU hold, biggest move first, each with a one-tap Dip/Rip alert.
// One batched DexScreener request for all of them (deepest pool per coin), refreshed every minute while visible.
export function signalOf(p) {
  const h1 = Number(p?.priceChange?.h1) || 0; const m5 = Number(p?.priceChange?.m5) || 0;
  return h1 >= 10 || m5 >= 4 ? ['pump', '🚀 ripping'] : h1 <= -10 || m5 <= -4 ? ['dump', '🩸 dumping'] : ['calm', 'steady'];
}

export function HeldSignals() {
  const held = useHeldList();
  const mints = useMemo(() => held.map(h => h.mint).filter(Boolean).slice(0, 30), [held]);
  const [pairs, setPairs] = useState({});
  const [open, setOpen] = useState(null);
  const key = mints.join(',');
  useEffect(() => {
    if (!key) return undefined;
    let alive = true;
    const load = () => !document.hidden && fetch(`https://api.dexscreener.com/tokens/v1/solana/${key}`).then(r => (r.ok ? r.json() : [])).then(list => {
      const best = {};
      (Array.isArray(list) ? list : []).forEach(p => { const m = p.baseToken?.address; if (m && (!best[m] || (p.liquidity?.usd || 0) > (best[m].liquidity?.usd || 0))) best[m] = p; });
      if (alive) setPairs(best);
    }).catch(() => {});
    load(); const t = setInterval(load, 60000);
    return () => { alive = false; clearInterval(t); };
  }, [key]);
  if (!held.length) return null;
  const rows = held.map(h => ({ h, p: pairs[h.mint] })).filter(r => r.p).sort((a, b) => Math.abs(b.p.priceChange?.h1 || 0) - Math.abs(a.p.priceChange?.h1 || 0));
  return <section className="m-card held-signals" data-testid="held-signals">
    <div className="m-row"><span className="m-label">SIGNALS ON COINS YOU HOLD</span><small className="m-dim">{held.length} coin{held.length === 1 ? '' : 's'} · biggest move first</small></div>
    {!rows.length && <p className="m-dim">Loading your coins…</p>}
    {rows.map(({ h, p }) => { const [tone, label] = signalOf(p); return <div key={h.mint} className={`hs-row tone-${tone}`}>
      <b>${p.baseToken?.symbol}</b><span className={`m-chip ${tone === 'pump' ? 'ok' : tone === 'dump' ? 'bad' : ''}`}>{label}</span>
      <span className="m-num sm">{formatPct(p.priceChange?.h1)} 1h</span><span className="m-dim">{formatUSD(Number(h.holding) * Number(p.priceUsd || 0))} held</span>
      <button type="button" className="m-btn" aria-expanded={open === h.mint} data-testid={`held-alert-${h.mint}`} onClick={() => setOpen(o => (o === h.mint ? null : h.mint))}>🎯 Dip/Rip alert</button>
      {open === h.mint && <div className="hs-tool"><DipRipTool pair={p} /></div>}</div>; })}
  </section>;
}
