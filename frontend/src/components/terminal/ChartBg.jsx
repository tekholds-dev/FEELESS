import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const LOGO = '/assets/feeless-logo.png';
const CAT = '/assets/feecat-mark.png';
const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Real 3D:
// perspective + preserve-3d, transform / opacity only, hidden in fx-lite / reduced motion (the plain chart shows), paused
// off-screen (`.cbg` is in lib/fxPause FX_SURFACES). Never interactive.
export function ChartBg({ kind }) {
  if (!kind || kind === 'default') return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    {kind === 'reactor' && <div className="cbg-stage">{n(3, i => <i key={i} className="cbg-ring" style={{ '--i': i }} />)}{n(6, i => <b key={i} className="cbg-ion" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'warp' && <div className="cbg-stage">{n(7, i => <i key={i} className="cbg-gate" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /><em className="cbg-word">FUSE</em></div>}
    {kind === 'helix' && <div className="cbg-stage"><div className="cbg-spin">{n(14, i => <i key={i} className="cbg-rung" style={{ '--i': i }}><u /><u /></i>)}</div><img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'cat' && <div className="cbg-stage"><img className="cbg-mark cbg-cat" src={CAT} alt="" />{n(8, i => <i key={i} className="cbg-paw" style={{ '--i': i }}>🐾</i>)}{n(3, i => <b key={i} className="cbg-coin" style={{ '--i': i }}><img src={LOGO} alt="" /></b>)}</div>}
  </div>;
}

// The picker in every chart's toolbar: Default or one of the four scenes. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a live 3D scene behind the candles. Applies to every chart; switches off by itself in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
