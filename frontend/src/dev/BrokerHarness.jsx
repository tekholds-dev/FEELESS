import React from 'react';
import { BrokerDesk } from '../components/BrokerDesk';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/broker`, `?linked` for the linked view): THE BROKERAGE on fixtures — no wallet, no Alpaca; writes answer locally.
const DEV = 'DEVBROKER1111111111111111111111111111111111';
const LINKED = { ready: true, linked: true, value: 1640.5, pnl: 98, accounts: [{ id: 'alpaca', broker: 'Alpaca · PAPER', name: 'Your keys', number: '5678', cash: 40.5, buyingPower: 81, value: 1640.5,
  positions: [{ ticker: 'SPY', units: 2, price: 600, value: 1200, pnl: 100, pnlPct: 9.09 }, { ticker: 'BTC/USD', units: 0.005, price: 80000, value: 400, pnl: -2, pnlPct: -0.5 }] }] };
export default function BrokerHarness() {
  try { localStorage.setItem(`feeless:chat-session:${DEV}`, JSON.stringify({ token: 'dev', expiresAt: Date.now() / 1000 + 86400 })); } catch { /* private window */ }
  if (!window.__bkFetch) { window.__bkFetch = window.fetch; const linked = new URLSearchParams(window.location.search).has('linked');
    window.fetch = (u, o) => (String(u).includes('/familia/broker') ? Promise.resolve({ ok: true, json: () => Promise.resolve(String(u).includes('/keys') ? { ok: true, account: LINKED.accounts[0] }
      : linked ? LINKED : { ready: true, snaptrade: false, linked: false, signup: 'https://app.alpaca.markets/signup' }) }) : window.__bkFetch(u, o)); }
  return <WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#07060a', boxSizing: 'border-box' }}><div style={{ maxWidth: 760 }}><BrokerDesk devAddress={DEV} /></div></div></WalletProvider>;
}
