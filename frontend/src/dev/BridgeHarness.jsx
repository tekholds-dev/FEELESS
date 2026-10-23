import React, { useEffect } from 'react';
import { BridgeDesk, Landed, RouteScene, StepRail, Vitals } from '../components/command/BridgeDesk';
import { routeVitals, SOLANA_ID } from '../lib/bridgeExec';
import '../styles/terminal.css';
import '../styles/meta.css';

// 🧪 DEV ONLY (`/dev/bridge`, `?day` · `?lite`): the bridge desk live (no wallet) + the quote / in-flight / landed states on a fixture LI.FI quote
// shaped like the real SOL → Base route (Relay, ~3 s). Nothing here can sign.
const Q = { tool: 'relaydepository', toolDetails: { name: 'Relay' }, action: { fromChainId: SOLANA_ID, toChainId: 8453, fromAmount: '25000000', fromToken: { symbol: 'SOL', decimals: 9 }, toToken: { symbol: 'ETH', decimals: 18 } },
  estimate: { toAmount: '1062000000000000', fromAmountUSD: '4.97', toAmountUSD: '4.93', executionDuration: 3, feeCosts: [{ amountUSD: '0.0124' }], gasCosts: [{ amountUSD: '0.0291' }] } };
export default function BridgeHarness() {
  const q = new URLSearchParams(window.location.search); const day = q.has('day');
  useEffect(() => { document.body.classList.toggle('theme-day', day); document.body.classList.toggle('fx-lite', q.has('lite')); document.body.style.background = day ? '#f3f7f4' : '#050806'; }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const v = routeVitals(Q);
  return <div style={{ height: '100vh', overflowY: 'auto', boxSizing: 'border-box', padding: 16, color: day ? '#111816' : '#ecf7f0' }}><div style={{ display: 'grid', gap: 18, maxWidth: 760, margin: '0 auto' }}>
    <h2 className="m-label">🧪 DEV PREVIEW · bridge desk</h2>
    <BridgeDesk />
    <h3 className="m-label">quoted · refreshing</h3>
    <div className="td-panel br"><RouteScene from="solana" to="base" v={v} step={0} asset="native" /><Vitals v={v} refreshIn={7} /><StepRail step={0} /></div>
    <h3 className="m-label">in flight</h3>
    <div className="td-panel br"><RouteScene from="solana" to="arbitrum" v={{ ...v, tool: 'Mayan' }} step={4} asset="usdc" /><StepRail step={4} /><p className="br-msg" role="status">Bridging — waiting for it to land on the other chain…</p></div>
    <h3 className="m-label">landed · failed</h3>
    <div className="td-panel br"><RouteScene from="base" to="solana" v={v} step={5} asset="usdc" /><StepRail step={5} /><Landed landed={{ got: 4.93, symbol: 'USDC', receivingLink: '#' }} to="solana" />
      <StepRail step={2} failed /><p className="br-msg bad" role="status">Declined in your wallet — nothing was sent.</p></div>
  </div></div>;
}
