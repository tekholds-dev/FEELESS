import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { SwapWorkspace } from './SwapWorkspace';

jest.mock('@solana/web3.js', () => ({
  VersionedTransaction: { deserialize: jest.fn() },
}));

jest.mock('../../hooks/useWallet', () => ({
  useWallet: () => ({ wallet: null, provider: null }),
}));

jest.mock('./WorkspaceChrome', () => ({
  useClock: () => 1_700_000_000_000,
}));

jest.mock('./FeeBack', () => ({
  FeeBackPreview: () => null,
}));

jest.mock('../ui/dialog', () => ({
  Dialog: ({ children }) => children,
  DialogContent: ({ children }) => children,
  DialogTitle: ({ children }) => children,
  DialogDescription: ({ children }) => children,
}));

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mount() {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<SwapWorkspace feeAssets={[]} />));
  return { container, root };
}

afterEach(() => {
  localStorage.clear();
  document.body.innerHTML = '';
  jest.restoreAllMocks();
});

test('restores a saved submitted order and checks its status without storing transaction data', async () => {
  const orderId = 'a'.repeat(36);
  localStorage.setItem('feeless.pending-swap-order', JSON.stringify({ order_id: orderId }));
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ order_id: orderId, state: 'submitted', signature: 'sig-123' }),
  });

  const { container, root } = mount();
  await act(async () => {});

  expect(global.fetch).toHaveBeenCalledWith(`/api/trading/order/${orderId}`, {});
  expect(container.querySelector('[data-testid="swap-result"] b').textContent).toBe('SUBMITTED');
  expect(container.querySelector('[data-testid="swap-check-status"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="swap-status-message"]').textContent).toContain('Nothing was resubmitted');
  expect(JSON.parse(localStorage.getItem('feeless.pending-swap-order'))).toEqual({ order_id: orderId });
  expect(localStorage.getItem('feeless.pending-swap-order')).not.toContain('signed_transaction');
  expect(localStorage.getItem('feeless.pending-swap-order')).not.toContain('transaction');
  act(() => root.unmount());
});