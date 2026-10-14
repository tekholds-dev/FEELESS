import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const LOGO = '/assets/feeless-logo.png';
const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain: the bull set falls while the last real tick was green, the bear set fades in on a red one
const BULL = ['SENDIT', 'LFG', 'APED', 'BONDED', 'PUMPED', 'MOON', 'WAGMI', 'ALPHA', 'GMGM', 'HODL', 'CTO', 'FEELESS'];
const BEAR = ['JEET', 'RUGGED', 'DUMPED', 'NGMI', 'PAPER', 'EXIT', 'REKT', 'COPE', 'SELLWALL', 'DEVSOLD', 'BAGS', 'WICKED'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Every scene follows the
// REAL tick: CandleFx puts cfk-up / cfk-dn on the chart area and the accent (`--c`) switches green ↔ pink; the 🌧 gutter ripples, the
// 🐋 sonar pings, 📼 Trench TV glitches on a red tick. transform / opacity only, hidden in fx-lite / reduced motion, paused off-screen
// (`.cbg` is an fxPause surface). Never interactive.
export function ChartBg({ kind }) {
  if (!kind || kind === 'default' || !CHART_BGS.some(([k]) => k === kind)) return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'neon' && <div className="cbg-stage"><div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" /></div></div><i className="cbg-horizon" />{n(3, i => <b key={i} className="cbg-beam" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />
      {n(14, i => <b key={i} className="cbg-col" style={{ '--i': i, left: `${(i * 7.1 + 1.5).toFixed(2)}%` }}><span className="is-bull">{BULL[i % BULL.length]}</span><span className="is-bear">{BEAR[i % BEAR.length]}</span></b>)}</div>}
    {kind === 'gutter' && <div className="cbg-stage"><i className="cbg-gsky" /><b className="cbg-gsign">TRENCH 24/7</b><i className="cbg-street" />
      <b className="cbg-grefl">TRENCH 24/7</b>{n(4, i => <i key={i} className="cbg-ripple" style={{ '--i': i, left: `${18 + i * 19}%` }} />)}
      {n(14, i => <em key={i} className="cbg-gdrop" style={{ '--i': i, left: `${(i * 43 + 5) % 98}%` }} />)}</div>}
    {kind === 'sonar' && <div className="cbg-stage"><i className="cbg-deep" /><i className="cbg-arm" />{n(3, i => <i key={i} className="cbg-ping" style={{ '--i': i }} />)}
      <i className="cbg-whale" />{n(9, i => <em key={i} className="cbg-bub" style={{ '--i': i, left: `${(i * 37 + 8) % 92}%` }} />)}</div>}
    {kind === 'lava' && <div className="cbg-stage">{n(5, i => <i key={i} className="cbg-blob" style={{ '--i': i, left: `${(i * 21 + 6) % 86}%` }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'vhs' && <div className="cbg-stage"><i className="cbg-lines" /><i className="cbg-band" /><i className="cbg-track" />
      <b className="cbg-rec"><i />REC</b><b className="cbg-ch">CH 03 · TRENCH TV</b><img className="cbg-mark" src={LOGO} alt="" /></div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a live scene behind the candles — every scene follows each real tick (green / pink, ripples, pings, glitches). Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
