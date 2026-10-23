import React, { useState } from 'react';
import { PaperPerps } from '../components/PaperPerps';
import { PerpsEarn } from '../components/EarnStake';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/perps`): the Perps building's money read + paper desk on a fixture book (nothing reaches the server).
const ROW = { coin: 'BTC', mark: 81790, ch24: -0.3, fundApr: 11, oiUsd: 3.5e9, maxLev: 40, venues: ['kraken', 'coinbase'] };
let BOOK = { cash: 9250, equity: 10061.4, start: 10000, realized: 48.2, trades: 5, winPct: 60, liquidated: [],
  open: [{ id: 'p1', coin: 'BTC', side: 'long', lev: 10, margin: 500, pnl: 61.2, pnlPct: 12.2, fund: -0.8, liq: 74000, toLiqPct: 9.5 },
    { id: 'p2', coin: 'ETH', side: 'short', lev: 5, margin: 250, pnl: -19.6, pnlPct: -7.8, fund: 0.3, liq: 2850, toLiqPct: 17.4 }],
  closed: [{ id: 'c1', coin: 'SOL', side: 'long', lev: 20, pnl: -100, why: 'liquidated' }, { id: 'c2', coin: 'BTC', side: 'short', lev: 3, pnl: 88.4, why: 'closed' }] };
const VENUES = { kraken: ['Kraken Pro', () => 'https://pro.kraken.com/'], coinbase: ['Coinbase', () => 'https://www.coinbase.com/derivatives'] };
export default function PerpsHarness() {
  const [lev] = useState(10);
  if (!window.__ppFetch) { window.__ppFetch = window.fetch; window.fetch = (u, o) => (String(u).includes('/paper-perps') ? Promise.resolve({ ok: true, json: () => Promise.resolve(BOOK) }) : window.__ppFetch(u, o)); }
  return <WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#050407', boxSizing: 'border-box' }}><div style={{ maxWidth: 720 }}>
    <PerpsEarn row={ROW} lev={lev} /><PaperPerps row={ROW} lev={lev} venues={VENUES} devAddress="DEV1111111111111111111111111111111111111111" /></div></div></WalletProvider>;
}
