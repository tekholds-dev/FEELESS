import React from 'react';
import MyMoney from '../components/MyMoney';
import { WalletProvider } from '../hooks/useWallet';

// 🧪 DEV ONLY (`/dev/money`): the YOUR MONEY room on a fixture read (a fake wallet + fake positions — nothing reaches the server).
const READ = { total: 412.37, coins: 4, markets: 2, dust: 3, unpriced: 1, positions: [
  { kind: 'market', key: 'jito', sym: 'JitoSOL', name: 'Jito', usd: 180.2, apy: 7.4, share: 0.437 },
  { kind: 'coin', key: 'WIF', sym: 'WIF', usd: 96.1, ch24: 6.2, pair: 'P1', share: 0.233 },
  { kind: 'market', key: 'jlp', sym: 'JLP', name: 'Jupiter JLP', usd: 61.5, apy: 21.3, share: 0.149 },
  { kind: 'coin', key: 'BONK', sym: 'BONK', usd: 40.4, ch24: -3.8, pair: 'P2', share: 0.098 },
  { kind: 'coin', key: 'POPCAT', sym: 'POPCAT', usd: 22.9, ch24: 1.1, pair: 'P3', share: 0.056 },
  { kind: 'coin', key: 'MEW', sym: 'MEW', usd: 11.27, ch24: -9.4, pair: 'P4', share: 0.027 }] };
export default function MoneyHarness() {
  if (!window.__moneyFetch) {
    window.__moneyFetch = window.fetch;
    window.fetch = (u, o) => (String(u).includes('/familia/my-money') ? Promise.resolve({ ok: true, json: () => Promise.resolve(READ) }) : window.__moneyFetch(u, o));
  }
  return <WalletProvider><div style={{ minHeight: '100vh', padding: 16, background: '#050407', boxSizing: 'border-box' }}><div style={{ maxWidth: 760 }}><MyMoneyAs /></div></div></WalletProvider>;
}
// the room needs a wallet: the harness pretends one is connected
function MyMoneyAs() { return <MyMoney devAddress="DEV1111111111111111111111111111111111111111" />; }
