import React, { act } from 'react';
import { createRoot } from 'react-dom/client';

const mockCall = jest.fn(async () => ({ tookUsd: 1, principalUsd: 4 }));
jest.mock('../lib/adminCall', () => ({ useAdmin: () => ({ call: mockCall }) }));
jest.mock('../lib/sharedJson', () => ({ _resetShared: () => {}, sharedJson: async () => ({ cards: [{ real: true, tpl: 't1', label: 'Prime', realBook: { fundedUsd: 5, reconciliation: { cardCashUsd: 1.88 } } }] }) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('react-router-dom', () => ({ Link: ({ children }) => children, useNavigate: () => jest.fn() }), { virtual: true });
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: null }) }));

test('💵 Fuse card withdraw takes the typed amount, never more than its cash (it used to take all of it)', async () => {
  mockCall.mockImplementation(async () => ({ tookUsd: 1, principalUsd: 4 })); const { RealCardFixes } = require('./FusePage');
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<RealCardFixes addr="Me" />); }); await act(async () => {});
  const btn = el.querySelector('[data-testid="withdraw-cash-t1"]'); expect(btn).not.toBeNull();
  window.confirm = jest.fn(() => true);
  window.prompt = jest.fn(() => '5'); await act(async () => { btn.click(); });   // more than the card's cash: refused, nothing sent
  expect(window.prompt.mock.calls[0][1]).toBe('1'); expect(mockCall).not.toHaveBeenCalled();
  window.prompt = jest.fn(() => '1'); await act(async () => { btn.click(); });
  expect(mockCall).toHaveBeenCalledWith('/admin/fuse-wallet/withdraw-cash', expect.objectContaining({ body: JSON.stringify({ tpl: 't1', usd: 1 }) }));
  act(() => root.unmount()); el.remove();
});
