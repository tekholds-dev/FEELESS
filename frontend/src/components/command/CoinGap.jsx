import React, { useEffect, useState } from 'react';
import { sharedJson } from '../../lib/sharedJson';
import { Rail } from '../PriceGaps';
import '../../styles/priceGaps.css';

// 📐 SITE-11 (Q23) — the coin's PRICE GAP before you buy: every real pool it trades in, drawn as one rail (cheap pool lamp → rich pool lamp,
// the lit bridge = what is left after a swap's cost each side), read once a minute from GET /api/reputation/price-gap/{mint}. When a quote is
// open it says whether Jupiter's route already goes through the cheap pool's DEX. READ-ONLY: nothing here trades or changes the order.
const SOL = 'So11111111111111111111111111111111111111112';

export function routeHitsCheap(gap, quote) {
  if (!gap || !quote?.routePlan?.length) return null;
  const want = String(gap.lo?.dex || '').toLowerCase();
  if (!want) return null;
  return quote.routePlan.some(r => String(r.swapInfo?.label || r.label || '').toLowerCase().includes(want));
}

export function CoinGap({ mint, quote }) {
  const [d, setD] = useState(null); const [err, setErr] = useState(false); const [age, setAge] = useState(0);
  useEffect(() => {
    if (!mint || mint === SOL) { setD(null); return undefined; }
    let on = true; setD(null); setErr(false);
    const go = () => sharedJson(`/api/reputation/price-gap/${mint}`, { maxAge: 55000 }).then(x => { if (on && x) { setD(x); setErr(false); setAge(0); } }).catch(() => on && setErr(true));
    go(); const t = setInterval(() => { if (!document.hidden) go(); }, 60000); const c = setInterval(() => { if (!document.hidden) setAge(a => a + 1); }, 1000);
    return () => { on = false; clearInterval(t); clearInterval(c); };
  }, [mint]);
  if (!mint || mint === SOL) return null;
  const g = d?.gap; const hit = routeHitsCheap(g, quote);
  return <section className="gp cg" data-testid="coin-gap">
    <header className="gp-head">
      <span className="gp-title" data-tip="This coin priced in every real pool it trades in (deep pool, real volume, trades this hour). Read-only — your swap still routes through Jupiter and your wallet signs."><em>BEFORE YOU BUY</em><b>📐 PRICE GAP</b></span>
      <span className="gp-k" data-tip="Real pools this coin trades in right now (of every pool DexScreener lists)"><small>POOLS</small><b className="m-num">{d ? `${d.realPools}/${d.pools}` : '…'}</b></span>
      <span className="gp-k" data-tip="What one swap costs (pool fee + slippage at a small size) — taken off each side"><small>COST / SIDE</small><b className="m-num">{d ? `${d.cost}%` : '…'}</b></span>
    </header>
    {g ? <ol className="gp-rails"><Rail g={g} i={0} age={g.open ? age : 0} /></ol>
      : <p className="gp-wait" data-testid="coin-gap-wait">{err ? 'The price feed did not answer — trying again in a minute.' : !d ? 'Pricing every pool…' : !d.answered ? 'No pool data for this coin yet.' : 'One real pool — no gap to measure. Jupiter prices it there.'}</p>}
    {g && hit != null ? <p className={`cg-route${hit ? ' is-ok' : ''}`} data-testid="coin-gap-route" data-tip="Jupiter's route vs the cheapest pool's DEX, read from the open quote">{hit ? `✓ Your route goes through ${g.lo.dex}, the cheapest pool.` : `Your route skips ${g.lo.dex} (cheapest) — Jupiter judged depth + impact; the gap is ${g.gapPct.toFixed(2)}%.`}</p> : null}
  </section>;
}
