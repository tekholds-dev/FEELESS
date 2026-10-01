import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FusePayouts } from './FuseAdminSettings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { address: 'FeeWa11et' }, provider: {} }) }));
const mockBatchSend = jest.fn(async () => ["SIG1"]);
jest.mock('../../lib/batchSend', () => ({ batchSend: (...a) => mockBatchSend(...a) }));

test('weekly payout: build the plan, pay everyone in one approval, then the server verifies the signatures', async () => {
  mockBatchSend.mockResolvedValue(['SIG1']);   // CRA resets mock implementations before each test
  const call = jest.fn(async (path) => (path.endsWith('/plan') ? { id: 'p1', rows: [{ wallet: 'Aaaa1111111111111111111111111111111111111111', owedUsd: 2, sol: 0.02 }], totalUsd: 2, totalSol: 0.02, solUsd: 100, bots: 1, history: [] }
    : { ok: true, paidUsd: 2, wallets: 1 }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<FusePayouts call={call} />); });
  await act(async () => { el.querySelector('[data-testid="payout-load"]').click(); });
  expect(el.textContent).toContain('1 bot wallet(s) excluded');
  await act(async () => { el.querySelector('[data-testid="payout-pay"]').click(); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(mockBatchSend.mock.calls[0][0].recipients).toEqual([{ address: 'Aaaa1111111111111111111111111111111111111111', amount: 0.02 }]);
  expect(call).toHaveBeenLastCalledWith('/admin/fuses/payouts/paid', { method: 'POST', body: JSON.stringify({ planId: 'p1', sigs: ['SIG1'] }) });
});
