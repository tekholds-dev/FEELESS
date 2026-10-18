import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain: the bull set falls while the last real tick was green, the bear set fades in on a red one
// 🟩 matrix rain v3: glyph streams (katakana + trench marks), the bear words fade in on a red tick
const GLYPHS = ['ﾊﾐﾋｰｳ$ｼﾅﾓﾆ×ｻﾜ', 'ﾂｵﾘｱﾎ+ﾃﾏｹﾒ%ｴ', 'ｶｷﾑﾕﾗ◎ｾﾈｽﾀﾇﾍ', 'ﾖﾁﾌ⚡ｼﾛﾔｦｲｸｺｿ', 'ﾏﾐﾑﾒﾓ$ﾔﾕﾖﾗﾘﾙﾚ', 'FEELESSﾊﾐﾋｰｳ'];
// 🌆 synth city: building heights (%) for the far + near skyline, widths cycle so the two copies tile seamlessly
const FAR = [38, 52, 30, 64, 44, 58, 34, 70, 48, 40, 60, 36];
const NEAR = [26, 40, 22, 48, 34, 30, 44, 20, 38, 28];
const BW = [44, 62, 38, 54, 70, 46];
const BEAR = ['JEET', 'RUGGED', 'DUMPED', 'NGMI', 'PAPER', 'EXIT', 'REKT', 'COPE', 'SELLWALL', 'DEVSOLD', 'BAGS', 'WICKED'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Calm by design — the candles
// are the show: one accent `--c` that SWITCHES green ↔ pink on each REAL tick (CandleFx's cfk-up / cfk-dn on the chart area, never animated),
// marks ≤ 25% opacity. transform / opacity only, hidden in fx-lite / reduced motion, paused off-screen (`.cbg` is an fxPause surface).
export function ChartBg({ kind }) {
  if (!kind || kind === 'default' || !CHART_BGS.some(([k]) => k === kind)) return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'neon' && <div className="cbg-stage"><i className="cbg-sunglow" /><span className="cbg-sun"><img src="/assets/feeless-logo.png" alt="" decoding="async" /></span><b className="cbg-word">FEELESS</b>
      <div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" /></div></div><i className="cbg-horizon" /><i className="cbg-vignette" /></div>}
    {kind === 'city' && <div className="cbg-stage"><i className="cbg-sky" />
      {[['far', FAR], ['near', NEAR]].map(([k, row]) => <div key={k} className={`cbg-skyline is-${k}`}>{[0, 1].map(c => <div key={c} className="cbg-strip">{row.map((h, i) =>
        <i key={i} className="cbg-bld" style={{ height: `${h}%`, '--w': `${BW[(i + c) % BW.length]}` }}>{k === 'near' && i === 4 ? <b className="cbg-sign">FEELESS</b> : null}</i>)}</div>)}</div>)}
      {n(7, i => <i key={i} className="cbg-lamp" style={{ '--i': i, left: `${8 + i * 13}%`, bottom: `${10 + (i * 37) % 26}%` }} />)}<i className="cbg-street" /><i className="cbg-vignette" /></div>}
    {kind === 'warp' && <div className="cbg-stage"><i className="cbg-core" /><span className="cbg-mark"><img src="/assets/feeless-logo.png" alt="" decoding="async" /></span>
      {n(9, i => <i key={i} className="cbg-gate" style={{ '--i': i }} />)}{n(14, i => <i key={i} className="cbg-ray" style={{ '--i': i, '--a': `${i * 25.7}deg` }} />)}<i className="cbg-vignette" /></div>}
    {kind === 'orbit' && <div className="cbg-stage"><span className="cbg-mark is-big"><img src="/assets/feeless-logo.png" alt="" decoding="async" /></span>
      {n(3, i => <div key={i} className="cbg-orb" style={{ '--i': i }}><div className="cbg-spin"><i className="cbg-ring" />{n(3, j => <b key={j} className="cbg-ion" style={{ '--j': j }} />)}</div></div>)}<i className="cbg-pulse" /><i className="cbg-vignette" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />
      {n(18, i => { const z = i % 3; return <b key={i} className={`cbg-col is-z${z}`} style={{ '--i': i, left: `${((i * 5.71) % 96 + 2).toFixed(2)}%` }}>
        <span className="is-bull">{GLYPHS[i % GLYPHS.length]}</span><span className="is-bear">{BEAR[i % BEAR.length]}</span></b>; })}<i className="cbg-vignette" /></div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a calm live scene behind the candles — each one turns green / pink with every real tick (neon trench with the FEELESS sun, synth city, warp tunnel, orbit core, matrix rain). Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
