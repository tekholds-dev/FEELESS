import React from 'react';
import { CHART_BGS, setChartBg, useChartBg } from '../../lib/chartBg';
import '../../styles/chartBg.css';

const n = (len, f) => Array.from({ length: len }, (_, i) => f(i));
// trench words for the code rain: the bull set falls while the last real tick was green, the bear set fades in on a red one
// 🟩 matrix rain v3: glyph streams (katakana + trench marks), the bear words fade in on a red tick
const GLYPHS = ['ﾊﾐﾋｰｳ$ｼﾅﾓﾆ×ｻﾜ', 'ﾂｵﾘｱﾎ+ﾃﾏｹﾒ%ｴ', 'ｶｷﾑﾕﾗ◎ｾﾈｽﾀﾇﾍ', 'ﾖﾁﾌ⚡ｼﾛﾔｦｲｸｺｿ', 'ﾏﾐﾑﾒﾓ$ﾔﾕﾖﾗﾘﾙﾚ', 'FEELESSﾊﾐﾋｰｳ'];
// 📟 terminal tape rows: made-up tickers (never a real price) in the Bloomberg screen's look
const TAPE = ['SOL ▲2.1  JUP ▼0.8  BONK ▲6.4  WIF ▲3.3  PUMP ▲1.2', 'FEE ▲9.9  TRUMP ▼1.4  POPCAT ▲4.0  PENGU ▼2.2', 'BTC ▲0.6  ETH ▼0.3  RAY ▲2.8  ORCA ▲1.1',
  'MOON ▲42  RUG ▼99  SEND ▲69  JEET ▼33  APE ▲21', 'GERM ▲12  GUN ▲7  BAGS ▼18  WAGMI ▲88', 'VOL ▲  BUYS 62%  HOLDERS ▲  DEV 0%  LP LOCKED'];
const BEAR = ['JEET', 'RUGGED', 'DUMPED', 'NGMI', 'PAPER', 'EXIT', 'REKT', 'COPE', 'SELLWALL', 'DEVSOLD', 'BAGS', 'WICKED'];

// 🎨 The live scene BEHIND the candles (PriceChart makes its own background see-through while one is picked). Calm by design — the candles
// are the show: one accent `--c` that SWITCHES green ↔ pink on each REAL tick (CandleFx's cfk-up / cfk-dn on the chart area, never animated),
// marks ≤ 25% opacity. transform / opacity only, hidden in fx-lite / reduced motion, paused off-screen (`.cbg` is an fxPause surface).
export function ChartBg({ kind }) {
  if (!kind || kind === 'default' || !CHART_BGS.some(([k]) => k === kind)) return null;
  return <div className={`cbg cbg-${kind}`} aria-hidden data-testid={`chart-bg-${kind}`}>
    <i className="cbg-tide is-up" /><i className="cbg-tide is-dn" />{/* ⚡ every scene breathes with the REAL tick */}
    {kind === 'neon' && <div className="cbg-stage"><i className="cbg-sunglow" /><span className="cbg-sun"><img src="/assets/feeless-logo.png" alt="" decoding="async" /></span><b className="cbg-word">FEELESS</b>
      <div className="cbg-floor"><div className="cbg-plane"><i className="cbg-grid" /><i className="cbg-grid is-dn" /></div></div><i className="cbg-horizon" /><i className="cbg-shock" /><i className="cbg-vignette" /></div>}
    {kind === 'pit' && <div className="cbg-stage"><i className="cbg-slime" /><b className="cbg-pumpword">PUMP</b>
      {n(16, i => <i key={i} className="cbg-pill" style={{ '--i': i, left: `${((i * 6.3) % 94 + 3).toFixed(1)}%` }} />)}<i className="cbg-pop" /><i className="cbg-vignette" /></div>}
    {kind === 'tape' && <div className="cbg-stage"><i className="cbg-crt" />
      {n(10, i => <b key={i} className="cbg-trow" style={{ '--i': i, top: `${6 + i * 9.2}%` }}>{[0, 1].map(c => <span key={c}>{TAPE[i % TAPE.length]}{'   '}</span>)}</b>)}
      <i className="cbg-cursor" /><i className="cbg-vignette" /></div>}
    {kind === 'rain' && <div className="cbg-stage"><i className="cbg-glow" />
      {n(18, i => { const z = i % 3; return <b key={i} className={`cbg-col is-z${z}`} style={{ '--i': i, left: `${((i * 5.71) % 96 + 2).toFixed(2)}%` }}>
        <span className="is-bull">{GLYPHS[i % GLYPHS.length]}</span><span className="is-bear">{BEAR[i % BEAR.length]}</span></b>; })}<i className="cbg-flash" /><i className="cbg-vignette" /></div>}
  </div>;
}

// The picker in every chart's toolbar: Default or a neon scene. One choice, every chart.
export function ChartBgPicker() {
  const v = useChartBg();
  return <select className="chart-bg-pick" value={v} onChange={e => setChartBg(e.target.value)} aria-label="Chart background" data-testid="chart-bg-pick"
    data-tip="Chart background: the plain chart, or a calm live scene behind the candles — each one turns green / pink with every real tick (neon trench with the FEELESS sun, matrix rain, pump pit, terminal tape — each one reacts to every real trade). Applies to every chart; off in lite mode.">
    {CHART_BGS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>;
}
