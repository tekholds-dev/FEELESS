import React, { useState } from 'react';
import { Gauge } from '../components/command/TradeDesk';
import '../styles/gasStation.css';

// 🧪 DEV ONLY (`/dev/gas`): the fuel station's gauges on fixture balances (no EVM wallet needed).
const CH = [['ethereum', 'ETH', 3.1, 1.5], ['base', 'ETH', 0.9, 0.25], ['arbitrum', 'ETH', 0.04, 0.25], ['optimism', 'ETH', 0.6, 0.25], ['polygon', 'POL', 0.02, 0.1], ['bsc', 'BNB', 0.31, 0.3],
  ['avalanche', 'AVAX', null, 0.25], ['linea', 'ETH', 1.4, 0.25], ['scroll', 'ETH', 0.0, 0.25], ['zksync', 'ETH', 0.12, 0.25], ['blast', 'ETH', 0.55, 0.25], ['mantle', 'MNT', 0.08, 0.1]]
  .map(([chain, symbol, usd, minUsd]) => ({ chain, symbol, usd, minUsd, balance: usd == null ? null : usd / 2400, enough: usd != null && usd >= minUsd }));
export default function GasHarness() {
  const [t, setT] = useState('arbitrum');
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, background: '#050806', color: '#dfe' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · fuel station</h2>
    <div className="td-panel gs"><header className="gs-head"><b className="is-low">{CH.filter(c => !c.enough).length} of 12 chains running dry</b><small>tap a tank to fill it</small></header>
      <div className="gs-grid">{CH.map((c, i) => <span key={c.chain} style={{ '--i': i }}><Gauge c={c} on={t === c.chain} onPick={() => setT(c.chain)} /></span>)}</div>
      <div className="gs-fill"><div className="m-seg gs-pre">{['1', '2', '5', '10'].map(v => <button key={v} type="button" className={v === '2' ? 'active' : ''}>${v}</button>)}</div><span /><div className="gs-route"><b>Ethereum</b><span className="gs-pipe"><i /><i /><i /></span><b>Arbitrum</b></div><button type="button" className="btn-primary td-go m-go">⛽ Quote $2 of gas</button></div></div>
  </div>;
}
