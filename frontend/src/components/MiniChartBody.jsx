import React from 'react';
import { PriceChart } from './terminal/PriceChart';
import { useMyPosition } from './terminal/TrenchChart';
import { usePrime, fuseLevels } from './ArenaPrime';

const pp = v => (Number(v) > 0 ? `$${Number(v) >= 1 ? Number(v).toFixed(2) : Number(v).toPrecision(4)}` : '—');
const mcf = v => { const n = Number(v); if (!(n > 0)) return '—'; return n >= 1e9 ? `$${(n / 1e9).toFixed(2)}B` : n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` : n >= 1e3 ? `$${(n / 1e3).toFixed(1)}K` : `$${n.toFixed(0)}`; };
const sg = v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;

// The mini chart's inside (lazy: the chart library loads only when a mini chart is open). It draws the SAME lines the war room
// draws: a Fuse card's entry · stop · lock (carried from where it was opened, else found on the live cards by coin) and YOUR
// own FEELESS trades on the coin (entry line + buy / sell marks), with one strip saying where you stand.
// metric 'marketCap' (the default, like the war room) = the same candles × supply; no cap known → price.
export default function MiniChartBody({ pair, tf, fuse: carried, metric = 'marketCap' }) {
  const d = usePrime(60000);
  const [myPos] = useMyPosition(pair);
  let fuse = carried && Number(carried.entry) > 0 ? carried : null;
  if (!fuse) for (const c of d?.cards || []) { const l = (c.legs || []).find(x => x.pairAddress === pair.pairAddress && Number(x.entry) > 0 && !x.buying); if (l) { fuse = fuseLevels(l, c.cfgEff || d.cfg, c.label); break; } }
  const px = Number(pair.priceUsd) || 0;
  const mine = myPos?.tokensHeld > 0 ? Number(myPos.fillPrice || myPos.avgEntry) || 0 : 0;
  const mc = Number(pair.marketCap) || 0; const asMc = metric === 'marketCap' && mc > 0 && px > 0; const k = asMc ? mc / px : 1;
  const p4 = v => (asMc ? mcf(Number(v) * k) : pp(v));
  return <>
    {(fuse || mine > 0) && <div className="mch-strip" data-testid="mch-strip">
      {fuse && <span className="mch-fuse" data-tip={`${fuse.card || 'Fuse card'}: where the card got in, where it stops and where it locks`}>⚛ <b>{p4(fuse.entry)}</b>{px > 0 && <em className={px >= fuse.entry ? 'm-pos' : 'm-neg'}>{sg((px / fuse.entry - 1) * 100)}</em>}
        {fuse.stop ? <u className="is-stop">🛑 {p4(fuse.stop)}</u> : null}{fuse.lock ? <u className="is-lock">❄ {p4(fuse.lock)}</u> : null}{fuse.trail ? <u className="is-lock">🏔 {p4(fuse.trail)}</u> : null}</span>}
      {mine > 0 && <span className="mch-you" data-tip="Your own FEELESS trades on this coin: your entry and where you stand">👤 <b>{p4(mine)}</b>{px > 0 && <em className={px >= mine ? 'm-pos' : 'm-neg'}>{sg((px / mine - 1) * 100)}</em>}</span>}
    </div>}
    <PriceChart key={`${pair.pairAddress}-${tf}-${asMc ? 'mc' : 'px'}`} pair={pair} interval={tf} metric={asMc ? 'marketCap' : 'price'} showVolume={false} fuse={fuse} userEntry={mine > 0 ? mine : null} userTrades={myPos?.trades || null} />
  </>;
}
