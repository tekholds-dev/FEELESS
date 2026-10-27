import React, { useMemo } from 'react';
import { useGlide } from '../lib/useGlide';
import { usd } from '../lib/cityPlan';
import '../styles/poolWaves.css';

// 🌊 THE POOL INTAKE (owner 2026-10-27: "the same intake from the agents tab everywhere — water levels + colour dots, a simple legend; the waves
// weren't vital"): the Pool Hall and the Night Vault share one band in the HQ intake's look. Each WATER LEVEL is a pool kind, each dot one pool:
// across = its TVL (log $100K … $10B), colour = what it pays (APY), a ring = the busiest money (24h volume ≥ its own TVL). Vitals tick on top;
// a tap on a dot does that pool's real money thing (the room decides: the Pool Hall filters to it, the Night Vault pops the money desk).
export const POOL_LANES = [['v3', 'CLMM'], ['dlmm', 'DLMM'], ['v2', 'V2'], ['vault', 'VAULTS'], ['lend', 'LEND'], ['stake', 'STAKE']];
export const POOL_LEGEND = [['hot', '50 %+ APY'], ['up', '10–50 %'], ['ok', '3–10 %'], ['q', 'under 3 %'], ['busy', 'ring = trades its TVL in a day']];
const TICKS = [[1e5, '$100K'], [1e6, '$1M'], [1e7, '$10M'], [1e8, '$100M'], [1e9, '$1B'], [1e10, '$10B']];
const clamp = v => Math.max(0, Math.min(1, v));
export const tvlX = v => (Number(v) > 0 ? clamp((Math.log10(Number(v)) - 5) / 5) : 0);
export const apyTone = a => (a == null ? 'q' : a >= 50 ? 'hot' : a >= 10 ? 'up' : a >= 3 ? 'ok' : 'q');
// pure: the pools → dots on their kind's level + the band's vitals
export function poolFlow(rows) {
  const rs = (rows || []).filter(r => r && Number(r.tvl) > 0);
  const flow = rs.reduce((a, r) => a + (Number(r.vol) || 0), 0); const tvl = rs.reduce((a, r) => a + (Number(r.tvl) || 0), 0);
  const tradeTvl = rs.filter(r => Number(r.vol) > 0).reduce((a, r) => a + r.tvl, 0);   // turnover only over pools that trade (lending / staking have no flow)
  const dots = rs.map(r => ({ id: r.id, sym: r.sym, kind: r.kind, proto: r.proto, tvl: r.tvl, vol: Number(r.vol) || 0, apy: r.apy, r, lane: POOL_LANES.findIndex(([k]) => k === r.kind),
    x: tvlX(r.tvl), tone: apyTone(r.apy), busy: Number(r.vol) >= r.tvl })).filter(d => d.lane >= 0);
  const hot = rs.filter(r => Number(r.vol) > 0).reduce((b, r) => (r.vol / r.tvl > (b ? b.vol / b.tvl : -1) ? r : b), null);
  return { dots, flow, tvl, turn: tradeTvl ? flow / tradeTvl : 0, hot: hot ? { ...hot, turn: hot.vol / hot.tvl } : null, n: POOL_LANES.map((_, i) => rs.filter(r => r.kind === POOL_LANES[i][0]).length) };
}
const pc = v => `${(v * 100) >= 100 ? Math.round(v * 100) : (v * 100).toFixed(1)}%`;

export function PoolWaves({ rows, tone = 'day', onPick, pickWord = 'Show this pool' }) {
  const f = useMemo(() => poolFlow(rows), [rows]);
  const flow = useGlide(f.flow, 900); const tvl = useGlide(f.tvl, 900);
  if (!f.dots.length) return null;
  return <section className={`pw is-${tone}`} style={{ '--n': POOL_LANES.length }} data-testid="pool-waves">
    <div className="pw-vitals">
      <span style={{ '--i': 0 }} data-tip="Every pool FEELESS tracks on Solana, added up"><em>TRACKED TVL</em><b className="m-num">{usd(tvl)}</b></span>
      <span style={{ '--i': 1 }} data-tip="What traded through those pools in the last 24 hours"><em>24H FLOW</em><b className="m-num">{usd(flow)}</b></span>
      <span style={{ '--i': 2 }} data-tip="24h volume ÷ liquidity across the pools that trade — LP fees follow turnover"><em>TURNOVER</em><b className="m-num">{pc(f.turn)}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, clamp(f.turn))})` }} /></u></span>
      {f.hot ? <span style={{ '--i': 3 }} className="is-hot" data-tip={`${f.hot.sym} on ${f.hot.proto}: ${usd(f.hot.vol)} traded on ${usd(f.hot.tvl)} of liquidity in 24h — the fattest fees (and the most impermanent-loss risk)`}>
        <em>ROUGHEST WATER</em><b>{f.hot.sym}</b><small className="m-num">{pc(f.hot.turn)} turnover</small></span> : null}
    </div>
    <div className="pw-body">
      <div className="pw-field">
        {POOL_LANES.map(([k, l], i) => <i key={k} className={`pw-lane is-${k}`} style={{ '--l': i }}><small>{l}</small></i>)}
        {TICKS.map(([v, l]) => <em key={l} className="pw-tick" style={{ left: `${tvlX(v) * 100}%` }}>{l}</em>)}
        {f.dots.map(d => <button key={d.id} type="button" className={`pw-dot t-${d.tone} ${d.busy ? 'is-busy' : ''}`} style={{ left: `${d.x * 100}%`, '--l': d.lane }} onClick={() => onPick?.(d.r)}
          data-tip={`${d.sym} · ${d.proto} · TVL ${usd(d.tvl)}${d.apy != null ? ` · ${Number(d.apy).toFixed(1)}% APY` : ''}${d.vol ? ` · ${usd(d.vol)} traded 24h` : ''} — ${pickWord}`} aria-label={`${d.sym} ${d.proto}`} data-testid={`pw-${d.id}`}><i /></button>)}
      </div>
      <ol className="pw-count">{POOL_LANES.map(([k, l], i) => <li key={k} className={`is-${k}`}><b className="m-num">{f.n[i]}</b><small>{l}</small></li>)}</ol>
    </div>
    <p className="pw-legend" aria-label="Legend">{POOL_LEGEND.map(([k, l]) => <span key={k} className={`t-${k}`}><i />{l}</span>)}</p>
  </section>;
}
