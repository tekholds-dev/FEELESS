import React, { useState } from 'react';
import { LiveFuseCard } from './FuseCard';
import { usePrime, primeRow, fuseLevels, TIER } from './ArenaPrime';
import { useLivePrices } from '../lib/livePrices';
import MiniChartBody from './MiniChartBody';

const TFS = ['1m', '5m', '15m'];
const sg = v => `${v >= 0 ? '+' : ''}${v.toFixed(1)}%`;

// The mini card's inside: 🃏 the SAME LiveFuseCard the page shows (tier look, flips to its live money) ⇄ 📈 the chart of one of
// its coins (the SAME mini chart body: the card's entry / stop / lock + your own trades). A tier card is always read live.
export default function MiniCardBody({ src, side, size, tf, setTf }) {
  const d = usePrime(src.kind === 'prime' ? 15000 : 600000);
  const [pick, setPick] = useState(0);
  const c = src.kind === 'prime' ? (d?.cards || []).find(x => x.tpl === src.tpl) : null;
  const r = c ? primeRow(c) : src.kind === 'row' ? src.row : null;
  const coins = (r?.legs || []).filter(l => l.pairAddress && l.soldUsd == null);
  const live = useLivePrices(coins.map(l => l.pairAddress));
  if (!r) return <p className="m-dim mch-wait" data-testid="mcd-wait">{src.kind === 'prime' && d ? 'This card is not live right now.' : 'Loading card…'}</p>;
  const t = c ? (TIER[c.tier] || TIER.gold) : null;
  if (side !== 'chart') return <div className="mcd-side mcd-card" key="card" data-testid="mcd-card">
    <LiveFuseCard r={r} aura={t ? t.aura : src.aura || ''} look={t ? t.look : null} label={c ? (c.real ? '💵 REAL · FUSE WALLET' : '📄 PAPER · TRUE FILLS') : null} serverOnly={!!c?.real} /></div>;
  const l = coins[Math.min(pick, coins.length - 1)];
  if (!l) return <p className="m-dim mch-wait">No coin on this card right now.</p>;
  const leg = c ? (c.legs || []).find(x => x.pairAddress === l.pairAddress) : null;
  const entry = leg ? 0 : l.tokens > 0 ? (l.usd || 0) / l.tokens : 0;
  const fuse = leg ? fuseLevels(leg, c.cfgEff || d.cfg, c.label) : entry > 0 ? { card: src.name, pairAddress: l.pairAddress, symbol: l.symbol, entry } : null;
  const pair = { chainId: 'solana', pairAddress: l.pairAddress, baseToken: { address: l.mint, symbol: l.symbol }, priceUsd: live.get?.(l.pairAddress)?.price ?? l.priceNow ?? null };
  return <div className="mcd-side mcd-chart" key="chart" data-testid="mcd-chart">
    <div className="mcd-coins" role="tablist" aria-label="Coins on this card">
      {coins.map((x, i) => { const p = Number(x.pnlPct); return <button key={x.pairAddress} type="button" role="tab" aria-selected={x === l} className={x === l ? 'active' : ''} onClick={() => setPick(i)} data-testid={`mcd-coin-${x.symbol}`}>
        ${x.symbol}{Number.isFinite(p) && !x.buying && <em className={p >= 0 ? 'm-pos' : 'm-neg'}>{sg(p)}</em>}</button>; })}
      <span className="mcd-tfs">{TFS.map(x => <button key={x} type="button" className={tf === x ? 'active' : ''} aria-pressed={tf === x} onClick={() => setTf(x)} data-testid={`mcd-tf-${x}`}>{x}</button>)}</span></div>
    <MiniChartBody key={`${l.pairAddress}-${size}`} pair={pair} tf={tf} fuse={fuse} />
  </div>;
}
