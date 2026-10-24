import React from 'react';
import { PerpsDash } from '../components/PerpsDash';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/perps`): the FEELESS perps dash on LIVE markets + Jupiter's live pools (no wallet — nothing is signed); 🧪 PRACTICE
// reads a fixture paper book.
let BOOK = { cash: 9250, equity: 10061.4, start: 10000, realized: 48.2, trades: 5, winPct: 60, liquidated: [],
  open: [{ id: 'p1', coin: 'BTC', side: 'long', lev: 10, margin: 500, pnl: 61.2, pnlPct: 12.2, fund: -0.8, liq: 74000, toLiqPct: 9.5 },
    { id: 'p2', coin: 'ETH', side: 'short', lev: 5, margin: 250, pnl: -19.6, pnlPct: -7.8, fund: 0.3, liq: 2850, toLiqPct: 17.4 }],
  closed: [{ id: 'c1', coin: 'SOL', side: 'long', lev: 20, pnl: -100, why: 'liquidated' }, { id: 'c2', coin: 'BTC', side: 'short', lev: 3, pnl: 88.4, why: 'closed' }] };
export default function PerpsHarness() {
  if (!window.__ppFetch) { window.__ppFetch = window.fetch; window.fetch = (u, o) => (String(u).includes('/paper-perps') ? Promise.resolve({ ok: true, json: () => Promise.resolve(BOOK) }) : window.__ppFetch(u, o)); }
  return <WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#020403', boxSizing: 'border-box' }}><PerpsDash devAddress="DEV1111111111111111111111111111111111111111" /></div></WalletProvider>;
}
