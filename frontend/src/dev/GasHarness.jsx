import React, { useEffect, useState } from 'react';
import { Gauge } from '../components/command/TradeDesk';
import { ChainOrb, RouteScene, StepRail, Vitals } from '../components/command/BridgeDesk';
import { routeVitals, SOLANA_ID } from '../lib/bridgeExec';
import '../styles/gasStation.css';
import '../styles/meta.css';
import '../styles/terminal.css';

// 🧪 DEV ONLY (`/dev/gas`, `?day` · `?lite`): the fuel station on fixture balances (no wallet) — the 11 tanks LI.FI can fill, paying with SOL.
const CH = [['ethereum', 'ETH', 3.1, 3], ['base', 'ETH', 0.9, 0.25], ['arbitrum', 'ETH', 0.04, 0.25], ['optimism', 'ETH', 0.6, 0.25], ['polygon', 'POL', 0.02, 0.25], ['bsc', 'BNB', 0.31, 0.25],
  ['avalanche', 'AVAX', null, 0.25], ['zksync', 'ETH', 0.12, 0.25], ['unichain', 'ETH', 0.0, 0.25], ['worldchain', 'ETH', 0.55, 0.25], ['cronos', 'CRO', 0.08, 0.25]]
  .map(([chain, symbol, usd, minUsd]) => ({ chain, symbol, usd, minUsd, balance: usd == null ? null : usd / 2400, enough: usd != null && usd >= minUsd }));
const Q = { tool: 'relaydepository', toolDetails: { name: 'Relay' }, action: { fromChainId: SOLANA_ID, toChainId: 42161, fromAmount: '10500000', fromToken: { symbol: 'SOL', decimals: 9 }, toToken: { symbol: 'ETH', decimals: 18 } },
  estimate: { toAmount: '843000000000000', fromAmountUSD: '2.01', toAmountUSD: '1.97', executionDuration: 2, feeCosts: [{ amountUSD: '0.005' }], gasCosts: [{ amountUSD: '0.029' }] } };
export default function GasHarness() {
  const [t, setT] = useState('arbitrum'); const q = new URLSearchParams(window.location.search); const day = q.has('day');
  useEffect(() => { document.body.classList.toggle('theme-day', day); document.body.classList.toggle('fx-lite', q.has('lite')); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: day ? '#f3f7f4' : '#050806', color: day ? '#111816' : '#dfe' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · fuel station</h2>
    <div className="td-panel gs"><header className="gs-head"><b className="is-low">{CH.filter(c => !c.enough).length} of {CH.length} chains running dry</b><small>tap a tank to fill it · ◎ 1.240 SOL ready to pay</small></header>
      <div className="gs-grid">{CH.map((c, i) => <span key={c.chain} style={{ '--i': i }}><Gauge c={c} on={t === c.chain} onPick={() => setT(c.chain)} /></span>)}</div>
      <div className="gs-fill"><div className="m-seg gs-pre">{['1', '2', '5', '10'].map(v => <button key={v} type="button" className={v === '2' ? 'active' : ''}>${v}</button>)}</div><span />
        <div className="m-seg gs-pay">{[['solana', 'SOL $236.4'], ['ethereum', 'ETH $3.1']].map(([k, l], i) => <button key={k} type="button" className={i ? '' : 'active'}><ChainOrb k={k} size={16} />{l}</button>)}</div></div>
      <RouteScene from="solana" to={t} v={routeVitals(Q)} step={0} asset="native" /><Vitals v={routeVitals(Q)} refreshIn={6} /><StepRail step={0} />
      <div className="br-go"><button type="button" className="btn-primary td-go m-go">⛽ Sign + fill $2</button></div></div>
  </div>;
}
