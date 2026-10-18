import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain: the bull set falls while the last real tick was green, the bear set fades in on a red one
const BULL = ['SENDIT', 'LFG', 'APED', 'BONDED', 'PUMPED', 'MOON', 'WAGMI', 'ALPHA', 'GMGM', 'HODL', 'CTO', 'FEELESS'];
const BEAR = ['JEET', 'RUGGED', 'DUMPED', 'NGMI', 'PAPER', 'EXIT', 'REKT', 'COPE', 'SELLWALL', 'DEVSOLD', 'BAGS', 'WICKED'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Calm by design — the candles
// are the show: one accent `--c` that SWITCHES green ↔ pink on each REAL tick (CandleFx's cfk-up / cfk-dn on the chart area, never animated),
// marks ≤ 25% opacity. transform / opacity only, hidden in fx-lite / reduced motion, paused off-screen (`.cbg` is an fxPause surface).
export function ChartBg({ kind }) {
  if (!kind || kind === 'default' || !CHART_BGS.some(([k]) => k === kind)) return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'aurora' && <div className="cbg-stage">{n(3, i => <i key={i} className="cbg-veil" style={{ '--i': i }} />)}<i className="cbg-lattice" /><i className="cbg-vignette" /></div>}
    {kind === 'pulse' && <div className="cbg-stage"><i className="cbg-lattice" /><i className="cbg-scan" />{n(3, i => <i key={i} className="cbg-ring" style={{ '--i': i }} />)}<i className="cbg-vignette" /></div>}
    {kind === 'neon' && <div className="cbg-stage"><i className="cbg-sunglow" /><span className="cbg-sun"><img src="/assets/feeless-logo.png" alt="" decoding="async" /></span><b className="cbg-word">FEELESS</b>
      <div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" /></div></div><i className="cbg-horizon" /><i className="cbg-vignette" /></div>}
    {kind === 'moon' && <div className="cbg-stage"><i className="cbg-moon" />{n(18, i => <i key={i} className="cbg-star" style={{ '--i': i, left: `${(i * 37.7) % 100}%`, top: `${(i * 53.3) % 100}%` }} />)}
      {n(3, i => <span key={i} className="cbg-rocket" style={{ '--i': i }}>🚀</span>)}<i className="cbg-vignette" /></div>}
    {kind === 'pills' && <div className="cbg-stage"><i className="cbg-glow" />{n(12, i => <i key={i} className="cbg-pill" style={{ '--i': i, left: `${((i * 8.3) % 94 + 3).toFixed(1)}%` }} />)}<i className="cbg-vignette" /></div>}
    {kind === 'tape' && <div className="cbg-stage"><div className="cbg-tapes">{n(4, i => <b key={i} className="cbg-tape" style={{ '--i': i }}>
      <span className="is-bull">{n(2, () => BULL.join(' ✦ ')).join(' ✦ ')}</span><span className="is-bear">{n(2, () => BEAR.join(' ✦ ')).join(' ✦ ')}</span></b>)}</div><i className="cbg-vignette" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />
      {n(14, i => { const z = i % 3; return <b key={i} className={`cbg-col is-z${z}`} style={{ '--i': i, left: `${((i * 7.13) % 96 + 2).toFixed(2)}%` }}>
        <span className="is-bull">{BULL[i % BULL.length]}</span><span className="is-bear">{BEAR[i % BEAR.length]}</span><u className="cbg-head" /></b>; })}<i className="cbg-vignette" /></div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a calm live scene behind the candles — each one turns green / pink with every real tick (neon trench with the FEELESS sun, moon run, pill rush, degen tape, code rain, aurora, pulse grid). Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
