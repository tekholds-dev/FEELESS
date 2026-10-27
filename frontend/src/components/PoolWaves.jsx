import React, { useMemo } from 'react';
import { useGlide } from '../lib/useGlide';
import { KIND_COLOR, usd } from '../lib/cityPlan';
import '../styles/poolWaves.css';

// 🌊 POOL WAVES (owner 2026-10-27: "night vault and pools in one — an advanced pools design, waves driven by pool flow"): the Pool Hall and the
// Night Vault share one sea. Each wave is one of the busiest pools right now — its HEIGHT is the pool's turnover (24h volume ÷ liquidity), its
// SPEED is the 24h volume, its colour is the pool kind. Vitals on top tick on every read; a tap on a wave's chip does that pool's real money
// thing (the room decides: the Pool Hall filters to it, the Night Vault pops the money desk on it).
const W = 1200, H = 150, LEN = 300;
const clamp = v => Math.max(0, Math.min(1, v));
// pure: the busiest pools → waves + the sea's vitals
export function poolFlow(rows, n = 5) {
  const rs = (rows || []).filter(r => r && Number(r.tvl) > 0);
  const flow = rs.reduce((a, r) => a + (Number(r.vol) || 0), 0); const tvl = rs.reduce((a, r) => a + (Number(r.tvl) || 0), 0);
  const tradeTvl = rs.filter(r => Number(r.vol) > 0).reduce((a, r) => a + r.tvl, 0);   // turnover only over pools that trade (lending / staking have no flow)
  const waves = rs.filter(r => Number(r.vol) > 0).sort((a, b) => b.vol - a.vol).slice(0, n).map(r => {
    const turn = r.vol / r.tvl;
    return { id: r.id, sym: r.sym, kind: r.kind, proto: r.proto, vol: r.vol, tvl: r.tvl, apy: r.apy, turn, r,
      amp: Math.round(5 + 23 * clamp(Math.log10(1 + turn * 10) / Math.log10(31))),            // 0 % → 5 px … 300 %+ turnover → 28 px
      dur: Math.round((16 - 11 * clamp((Math.log10(r.vol) - 4) / 3.5)) * 10) / 10 };           // $10K/day → 16 s a lap … $30M/day → 5 s
  });
  const hot = waves.reduce((b, w) => (w.turn > (b?.turn ?? -1) ? w : b), null);
  return { waves, flow, tvl, turn: tradeTvl ? flow / tradeTvl : 0, hot };
}
// pure: one wave's outline — a sine-ish run of quadratic humps two screens wide (it slides left one screen per lap, seamless)
export function wavePath(amp, base, len = LEN, width = W * 2) {
  let d = `M0 ${base}`;
  for (let x = 0, up = true; x < width; x += len / 2, up = !up) d += ` Q${x + len / 4} ${base + (up ? -2 * amp : 2 * amp)} ${x + len / 2} ${base}`;
  return `${d} L${width} ${H} L0 ${H} Z`;
}
const pc = v => `${(v * 100) >= 100 ? Math.round(v * 100) : (v * 100).toFixed(1)}%`;

export function PoolWaves({ rows, tone = 'day', onPick, pickWord = 'Show this pool' }) {
  const f = useMemo(() => poolFlow(rows), [rows]);
  const flow = useGlide(f.flow, 900); const tvl = useGlide(f.tvl, 900);
  if (!f.waves.length) return null;
  const n = f.waves.length;
  return <section className={`pw is-${tone}`} data-testid="pool-waves">
    <div className="pw-vitals">
      <span style={{ '--i': 0 }} data-tip="Every pool FEELESS tracks on Solana, added up"><em>TRACKED TVL</em><b className="m-num">{usd(tvl)}</b></span>
      <span style={{ '--i': 1 }} data-tip="What traded through those pools in the last 24 hours — the water's flow"><em>24H FLOW</em><b className="m-num">{usd(flow)}</b></span>
      <span style={{ '--i': 2 }} data-tip="24h volume ÷ liquidity across the pools that trade — how hard the water is moving (LP fees follow turnover)"><em>TURNOVER</em><b className="m-num">{pc(f.turn)}</b>
        <u aria-hidden="true"><s style={{ transform: `scaleX(${Math.max(0.03, clamp(f.turn))})` }} /></u></span>
      {f.hot ? <span style={{ '--i': 3 }} className="is-hot" data-tip={`${f.hot.sym} on ${f.hot.proto}: ${usd(f.hot.vol)} traded on ${usd(f.hot.tvl)} of liquidity in 24h — the roughest water, the fattest fees (and the most impermanent-loss risk)`}>
        <em>ROUGHEST WATER</em><b>{f.hot.sym}</b><small className="m-num">{pc(f.hot.turn)} turnover</small></span> : null}
    </div>
    <div className="pw-sea" aria-hidden="true">
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        {f.waves.map((w, i) => ({ w, i })).reverse().map(({ w, i }) => <g key={w.id} className="pw-wave" style={{ '--d': `${w.dur}s`, '--c': KIND_COLOR[w.kind] || '#45e486', '--o': 0.08 + (n - i) * 0.06 }}>
          <path d={wavePath(w.amp, 112 - i * 15)} /></g>)}
      </svg>
      <i className="pw-glint" /><i className="pw-foam" />
    </div>
    <ol className="pw-legend">{f.waves.map((w, i) => <li key={w.id} style={{ '--c': KIND_COLOR[w.kind] || '#45e486', '--i': i }}>
      <button type="button" onClick={() => onPick?.(w.r)} data-tip={`${w.sym} · ${w.proto}: ${usd(w.vol)} in 24h on ${usd(w.tvl)} liquidity (${pc(w.turn)} turnover)${w.apy != null ? ` · ${Number(w.apy).toFixed(1)}% APY` : ''} — ${pickWord}`} data-testid={`pw-${w.id}`}>
        <i aria-hidden="true" /><b>{w.sym}</b><small className="m-num">{usd(w.vol)} · {pc(w.turn)}</small></button></li>)}</ol>
  </section>;
}
