import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const LOGO = '/assets/feeless-logo.png';
const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain (one column each, upright letters)
const RAIN = ['SENDIT', 'LFG', 'APED', 'GMGM', 'WAGMI', 'BONDED', 'PUMPED', 'DEGEN', 'TRENCH', 'MOON', 'JEET', 'RUGPROOF', 'FEELESS', 'HODL', 'CTO', 'ALPHA'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked), all in the neon-trench
// language: one accent that flips green ↔ pink on every real tick (cfk-up / cfk-dn). transform / opacity only, hidden in fx-lite /
// reduced motion, paused off-screen (`.cbg` is in lib/fxPause FX_SURFACES). Never interactive.
export function ChartBg({ kind }) {
  if (!kind || kind === 'default') return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'neon' && <div className="cbg-stage"><div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" /></div></div><i className="cbg-horizon" />{n(3, i => <b key={i} className="cbg-beam" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'reactor' && <div className="cbg-stage"><i className="cbg-glow" /><i className="cbg-sweep" />{n(3, i => <i key={i} className="cbg-ring" style={{ '--i': i }} />)}{n(6, i => <b key={i} className="cbg-ion" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'helix' && <div className="cbg-stage"><i className="cbg-glow" /><div className="cbg-spin">{n(14, i => <i key={i} className="cbg-rung" style={{ '--i': i }}><u /><u /></i>)}</div><img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'city' && <div className="cbg-stage"><i className="cbg-glow" /><i className="cbg-sky is-far" style={{ '--i': 1 }} /><i className="cbg-sign" /><i className="cbg-sky" style={{ '--i': 0 }} />
      {n(24, i => <b key={i} className="cbg-win" style={{ '--i': i, left: `${(i * 41 + 7) % 96}%`, bottom: `${6 + ((i * 17) % 34)}%` }} />)}{n(16, i => <em key={i} className="cbg-drop" style={{ '--i': i, left: `${(i * 61 + 3) % 99}%` }} />)}</div>}
    {kind === 'warp' && <div className="cbg-stage"><i className="cbg-core" />{n(16, i => <b key={i} className="cbg-streak" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />{n(16, i => <b key={i} className="cbg-col" style={{ '--i': i, left: `${(i * 6.25 + 1.5).toFixed(2)}%` }}>{RAIN[i % RAIN.length]}</b>)}</div>}
    {kind === 'tunnel' && <div className="cbg-stage">{n(6, i => <i key={i} className="cbg-frame" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'storm' && <div className="cbg-stage">{n(3, i => <i key={i} className="cbg-cloud" style={{ '--i': i }} />)}<i className="cbg-flash" /><i className="cbg-bolt" /><i className="cbg-glow" />
      {n(20, i => <em key={i} className="cbg-slash" style={{ '--i': i, left: `${(i * 53 + 9) % 104}%` }} />)}</div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a live neon scene behind the candles — every scene flips green / pink with each real tick. Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
