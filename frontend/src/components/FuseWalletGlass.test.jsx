import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'ME' } }) }));
const { FuseWalletGlass } = require('./FuseWalletGlass');

test('🧬 the family building shows the wallet\'s live Fuse cards: total, P&L, a coin-split bar per card, best + worst coin', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ held: { cards: 1, valueUsd: 23.4, pnlUsd: 3.4, pnlPct: 17 },
    rows: [{ id: 'c1', name: 'Trench card', closed: false, pnlUsd: 3.4, pnlPct: 17, legs: [{ symbol: 'AAA', pairAddress: 'p1', valueUsd: 15, pnlPct: 40 }, { symbol: 'BBB', pairAddress: 'p2', valueUsd: 8.4, pnlPct: -12 }] }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<FuseWalletGlass />); }); await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(global.fetch.mock.calls[0][0]).toContain('/api/reputation/fuses/pnl/ME');
  const t = el.textContent; expect(t).toContain('1 live card'); expect(t).toContain('Trench card'); expect(t).toContain('▲ $AAA +40.0%'); expect(t).toContain('▼ $BBB -12.0%');
  expect(el.querySelectorAll('.fwg-legs i')).toHaveLength(2);
  act(() => root.unmount());
});
