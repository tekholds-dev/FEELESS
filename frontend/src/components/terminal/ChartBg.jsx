import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const LOGO = '/assets/feeless-logo.png';
const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain: the bull set falls while the last real tick was green, the bear set fades in on a red one
const BULL = ['SENDIT', 'LFG', 'APED', 'BONDED', 'PUMPED', 'MOON', 'WAGMI', 'ALPHA', 'GMGM', 'HODL', 'CTO', 'FEELESS'];
const BEAR = ['JEET', 'RUGGED', 'DUMPED', 'NGMI', 'PAPER', 'EXIT', 'REKT', 'COPE', 'SELLWALL', 'DEVSOLD', 'BAGS', 'WICKED'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Every scene follows the
// REAL tick: CandleFx puts cfk-up / cfk-dn on the chart area and the accent (`--c`) switches green ↔ pink; neon streaks race on a green
// tick, the code rain flips to bear words, hyperspace runs in reverse and the casino reels lock on a red one. transform / opacity only, hidden in fx-lite / reduced motion, paused off-screen
// (`.cbg` is an fxPause surface). Never interactive.
export function ChartBg({ kind }) {
  if (!kind || kind === 'default' || !CHART_BGS.some(([k]) => k === kind)) return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'neon' && <div className="cbg-stage"><i className="cbg-stars" /><i className="cbg-sun" /><i className="cbg-ridge" />
      <div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" />{n(4, i => <b key={i} className="cbg-streak" style={{ '--i': i, left: `${16 + i * 22}%` }} />)}</div></div>
      <i className="cbg-horizon" />{n(3, i => <b key={i} className="cbg-beam" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />
      {n(22, i => { const z = i % 3; return <b key={i} className={`cbg-col is-z${z}`} style={{ '--i': i, left: `${((i * 4.53) % 97 + 1).toFixed(2)}%` }}>
        <span className="is-bull">{BULL[i % BULL.length]}</span><span className="is-bear">{BEAR[i % BEAR.length]}</span><u className="cbg-head" /></b>; })}
      <i className="cbg-sweep" /></div>}
    {kind === 'hyper' && <div className="cbg-stage"><i className="cbg-core" />
      {n(28, i => <b key={i} className="cbg-star" style={{ '--i': i, '--a': `${(i * 137.5) % 360}deg` }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'casino' && <div className="cbg-stage"><i className="cbg-felt" /><b className="cbg-sign">THE HOUSE ALWAYS RUGS</b>
      <div className="cbg-reels">{n(3, i => <b key={i} className="cbg-reel" style={{ '--i': i }}><span>{[...BULL.slice(i * 3, i * 3 + 4), '💎', '🚀', ...BULL.slice(i * 3, i * 3 + 4), '💎', '🚀'].map((w, j) => <u key={j}>{w}</u>)}</span></b>)}</div>
      {n(7, i => <em key={i} className="cbg-chip" style={{ '--i': i, left: `${(i * 13 + 6) % 92}%` }} />)}</div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a live scene behind the candles — every scene follows each real tick (green / pink, streaks, bull ↔ bear rain, hyperspace, casino reels). Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
