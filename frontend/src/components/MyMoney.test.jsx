import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
let mockWallet = { chain: 'solana', address: 'ME' };
const mockTrade = jest.fn();
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: mockWallet }) }));
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'sess' }));
jest.mock('./FamiliaTrade', () => ({ familiaTrade: p => mockTrade(p) }));
jest.mock('../lib/sharedJson', () => ({ sharedJson: () => Promise.resolve({ total: 40, coins: 1, markets: 1, dust: 2, unpriced: 0, positions: [
  { kind: 'market', key: 'jito', sym: 'JitoSOL', name: 'Jito', usd: 30, apy: 7.1, share: 0.75 },
  { kind: 'coin', key: 'MINTA', sym: 'AAA', usd: 10, ch24: -4.2, pair: 'PA', share: 0.25 }] }), _resetShared: () => {} }));
const { default: MyMoney, towerFloors } = require('./MyMoney');

test('💵 YOUR MONEY: a floor per proved position, the live total, each coin one tap from its desk; no wallet = a dark tower', async () => {
  const fl = towerFloors([{ key: 'a', kind: 'market', share: 0.75 }, { key: 'b', kind: 'coin', ch24: -1, share: 0.25 }, { key: 'c', kind: 'coin', ch24: 3, share: 0 }]);
  expect(fl.map(f => f.tone)).toEqual(['gold', 'dn', 'up']); expect(fl[0].w).toBeGreaterThan(fl[1].w);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<MyMoney />); }); await act(async () => { await Promise.resolve(); });
  expect(q('my-money').textContent).toContain('1 coin · 1 market · 2 dust'); expect(el.querySelectorAll('.ym-floor')).toHaveLength(2);
  expect(q('ym-row-jito').textContent).toContain('APY 7.1%'); expect(q('ym-row-MINTA').textContent).toContain('24h -4.2%');
  act(() => q('ym-trade-MINTA').click()); expect(mockTrade).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'PA' }));
  expect(q('my-money').textContent).not.toMatch(/realized/i);
  mockWallet = null;
  await act(async () => { root.render(<MyMoney key="x" />); });
  expect(q('ym-empty')).not.toBeNull();
  await act(async () => { root.unmount(); });
});
