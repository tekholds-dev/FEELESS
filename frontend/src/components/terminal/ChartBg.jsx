import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const LOGO = '/assets/feeless-logo.png';
// three mountain ridges, far → near (each its own outline)
const RIDGES = ['polygon(0 55%, 8% 38%, 16% 50%, 27% 12%, 36% 44%, 47% 22%, 58% 52%, 69% 8%, 80% 46%, 90% 28%, 100% 48%, 100% 100%, 0 100%)',
  'polygon(0 40%, 10% 58%, 21% 26%, 33% 54%, 44% 34%, 54% 60%, 66% 30%, 77% 56%, 88% 22%, 100% 50%, 100% 100%, 0 100%)',
  'polygon(0 62%, 12% 34%, 24% 60%, 38% 40%, 50% 66%, 63% 36%, 75% 62%, 87% 44%, 100% 64%, 100% 100%, 0 100%)'];
const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Real 3D:
// perspective + preserve-3d, transform / opacity only, hidden in fx-lite / reduced motion (the plain chart shows), paused
// off-screen (`.cbg` is in lib/fxPause FX_SURFACES). Never interactive.
export function ChartBg({ kind }) {
  if (!kind || kind === 'default') return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    {kind === 'reactor' && <div className="cbg-stage">{n(3, i => <i key={i} className="cbg-ring" style={{ '--i': i }} />)}{n(6, i => <b key={i} className="cbg-ion" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'helix' && <div className="cbg-stage"><div className="cbg-spin">{n(14, i => <i key={i} className="cbg-rung" style={{ '--i': i }}><u /><u /></i>)}</div><img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'sunset' && <div className="cbg-stage"><i className="cbg-sun" /><i className="cbg-haze" /><div className="cbg-sea">{n(7, i => <b key={i} className="cbg-glint" style={{ '--i': i }} />)}{n(3, i => <i key={i} className="cbg-swell" style={{ '--i': i }} />)}</div><img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'aurora' && <div className="cbg-stage">{n(18, i => <b key={i} className="cbg-star" style={{ '--i': i, left: `${(i * 37 + 11) % 97}%`, top: `${(i * 23 + 5) % 58}%` }} />)}{n(3, i => <i key={i} className="cbg-veil" style={{ '--i': i }} />)}<i className="cbg-ridge" /><img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'peaks' && <div className="cbg-stage"><i className="cbg-dawn" />{RIDGES.map((r, i) => <i key={i} className="cbg-peak" style={{ '--i': i, clipPath: r }} />)}{n(3, i => <b key={i} className="cbg-fog" style={{ '--i': i }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'sakura' && <div className="cbg-stage"><i className="cbg-moon" /><i className="cbg-pond" />{n(14, i => <b key={i} className="cbg-petal" style={{ '--i': i, left: `${(i * 29 + 12) % 104}%` }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
    {kind === 'deep' && <div className="cbg-stage">{n(4, i => <i key={i} className="cbg-ray" style={{ '--i': i }} />)}{n(3, i => <b key={i} className="cbg-jelly" style={{ '--i': i }}><u /><u /><u /></b>)}{n(10, i => <em key={i} className="cbg-bub" style={{ '--i': i, left: `${(i * 41 + 7) % 96}%` }} />)}<img className="cbg-mark" src={LOGO} alt="" /></div>}
  </div>;
}

// The picker in every chart's toolbar: Default, a Fuse scene, or a calm one. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a live scene behind the candles (Fuse reactor / helix, or a calm sunset / aurora). Applies to every chart; switches off by itself in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
