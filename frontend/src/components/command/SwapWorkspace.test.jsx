import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { VersionedTransaction } from '@solana/web3.js';
import { SwapWorkspace } from './SwapWorkspace';

jest.mock('@solana/web3.js', () => ({
  VersionedTransaction: { deserialize: jest.fn() },
}));

const mockWalletState = { wallet: null, provider: null };

jest.mock('../../hooks/useWallet', () => ({
  useWallet: () => mockWalletState,
}));

jest.mock('./WorkspaceChrome', () => ({
  useClock: () => 1_700_000_000_000,
}));

jest.mock('./FeeBack', () => ({
  FeeBackPreview: () => null,
}));

jest.mock('../ui/dialog', () => {
  const mockReact = require('react');
  return {
    Dialog: ({ children }) => children,
    DialogContent: ({ children, ...props }) => mockReact.createElement('div', props, children),
    DialogTitle: ({ children }) => mockReact.createElement('h2', null, children),
    DialogDescription: ({ children }) => mockReact.createElement('p', null, children),
  };
});

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

function mount(props = {}) {
  const container = document.createElement('div');
  document.body.appendChild(container);
  const root = createRoot(container);
  act(() => root.render(<SwapWorkspace feeAssets={[]} {...props} />));
  return { container, root };
}

afterEach(() => {
  localStorage.clear();
  document.body.innerHTML = '';
  jest.restoreAllMocks();
  mockWalletState.wallet = null;
  mockWalletState.provider = null;
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

test('offers a safe status retry when saved-order recovery is temporarily unavailable', async () => {
  const orderId = 'c'.repeat(36);
  localStorage.setItem('feeless.pending-swap-order', JSON.stringify({ order_id: orderId }));
  global.fetch = jest.fn()
    .mockRejectedValueOnce(new Error('Temporary provider timeout'))
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ order_id: orderId, state: 'confirmed', signature: 'sig-recovered' }),
    });

  const { container, root } = mount();
  await act(async () => {});

  expect(container.querySelector('[data-testid="swap-status-message"]').textContent)
    .toContain('status could not be restored');
  expect(container.querySelector('[data-testid="swap-retry-recovery"]')).not.toBeNull();
  expect(container.querySelector('[data-testid="swap-fresh-order"]')).not.toBeNull();
  expect(JSON.parse(localStorage.getItem('feeless.pending-swap-order'))).toEqual({ order_id: orderId });
  expect(global.fetch).toHaveBeenNthCalledWith(1, `/api/trading/order/${orderId}`, {});

  await act(async () => container.querySelector('[data-testid="swap-retry-recovery"]').click());

  expect(global.fetch).toHaveBeenNthCalledWith(2, `/api/trading/order/${orderId}`, {});
  expect(global.fetch.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false);
  expect(container.querySelector('[data-testid="swap-result"] b').textContent).toBe('CONFIRMED');
  expect(localStorage.getItem('feeless.pending-swap-order')).toBeNull();
  act(() => root.unmount());
});

test('clears a temporarily unavailable saved order only after an explicit fresh-order choice', async () => {
  const orderId = 'd'.repeat(36);
  localStorage.setItem('feeless.pending-swap-order', JSON.stringify({ order_id: orderId }));
  global.fetch = jest.fn().mockRejectedValue(new Error('Temporary provider timeout'));

  const { container, root } = mount();
  await act(async () => {});

  expect(localStorage.getItem('feeless.pending-swap-order')).not.toBeNull();
  act(() => container.querySelector('[data-testid="swap-fresh-order"]').click());

  expect(localStorage.getItem('feeless.pending-swap-order')).toBeNull();
  expect(container.querySelector('[data-testid="swap-recovery-actions"]')).toBeNull();
  expect(container.querySelector('[data-testid="swap-status-message"]')).toBeNull();
  act(() => root.unmount());
});

test('keeps an uncertain execution pending across reopen without resending the signed transaction', async () => {
  const orderId = 'b'.repeat(36);
  const walletAddress = 'Wallet1111111111111111111111111111111111111';
  const tokenMint = 'Token1111111111111111111111111111111111111';
  const feeAsset = { id: 'token', label: 'TOKEN', mint: tokenMint, chain: 'solana' };
  const quote = {
    order_id: orderId,
    expires_at: 1_700_000_045,
    output_metadata: { decimals: 6, symbol: 'TOKEN' },
    quote: {
      transaction: 'AQIDBA==',
      outAmount: '1000000',
      otherAmountThreshold: '990000',
      routePlan: [],
    },
  };
  const signed = Uint8Array.from([1, 2, 3, 4]);
  const provider = {
    publicKey: { toString: () => walletAddress },
    signTransaction: jest.fn().mockResolvedValue({ serialize: () => signed }),
  };

  mockWalletState.wallet = { chain: 'solana', address: walletAddress };
  mockWalletState.provider = provider;
  VersionedTransaction.deserialize.mockReturnValue({
    message: { staticAccountKeys: [{ toBase58: () => walletAddress }] },
  });
  global.fetch = jest.fn()
    .mockResolvedValueOnce({ ok: true, json: async () => quote })
    .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true, broadcast: false }) })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ order_id: orderId, state: 'submitted', signature: 'sig-uncertain' }),
    });

  const firstMount = mount({ feeAsset });
  await act(async () => firstMount.container.querySelector('[data-testid="swap-get-quote"]').click());
  await act(async () => firstMount.container.querySelector('[data-testid="swap-review"]').click());
  await act(async () => firstMount.container.querySelector('[data-testid="swap-approve-wallet"]').click());

  expect(provider.signTransaction).toHaveBeenCalledTimes(1);
  expect(global.fetch).toHaveBeenNthCalledWith(
    3,
    '/api/trading/execute',
    expect.objectContaining({ method: 'POST', body: expect.stringContaining(orderId) }),
  );
  expect(firstMount.container.querySelector('[data-testid="swap-result"] b').textContent).toBe('SUBMITTED');
  expect(JSON.parse(localStorage.getItem('feeless.pending-swap-order'))).toEqual({ order_id: orderId });
  expect(localStorage.getItem('feeless.pending-swap-order')).not.toContain('signed_transaction');
  expect(localStorage.getItem('feeless.pending-swap-order')).not.toContain('AQIDBA==');
  act(() => firstMount.root.unmount());

  global.fetch = jest.fn()
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ order_id: orderId, state: 'submitted', signature: 'sig-uncertain' }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ order_id: orderId, state: 'submitted', signature: 'sig-uncertain' }),
    });
  const reopened = mount({ feeAsset });
  await act(async () => {});

  expect(global.fetch).toHaveBeenNthCalledWith(1, `/api/trading/order/${orderId}`, {});
  expect(reopened.container.querySelector('[data-testid="swap-result"] b').textContent).toBe('SUBMITTED');
  expect(reopened.container.querySelector('[data-testid="swap-check-status"]')).not.toBeNull();
  expect(reopened.container.querySelector('[data-testid="swap-status-message"]').textContent).toContain('Nothing was resubmitted');

  await act(async () => reopened.container.querySelector('[data-testid="swap-check-status"]').click());

  expect(global.fetch).toHaveBeenNthCalledWith(2, `/api/trading/order/${orderId}`, {});
  expect(global.fetch.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false);
  expect(provider.signTransaction).toHaveBeenCalledTimes(1);
  act(() => reopened.root.unmount());
});

test('keeps the swap review facts and approval action readable at every text size', async () => {
  const walletAddress = 'Wallet1111111111111111111111111111111111111';
  const feeAsset = { id: 'token', label: 'TOKEN', mint: 'Token1111111111111111111111111111111111111', chain: 'solana' };
  const quote = {
    order_id: 'd'.repeat(36),
    expires_at: 1_700_000_045,
    output_metadata: { decimals: 6, symbol: 'TOKEN' },
    quote: {
      transaction: 'AQIDBA==',
      outAmount: '1000000',
      otherAmountThreshold: '990000',
      routePlan: [],
    },
  };

  mockWalletState.wallet = { chain: 'solana', address: walletAddress };
  mockWalletState.provider = {};

  for (const [fontScale, expectedScale] of [['normal', '1'], ['large', '1.12'], ['xlarge', '1.24']]) {
    global.fetch = jest.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => quote })
      .mockResolvedValueOnce({ ok: true, json: async () => ({ success: true }) });

    const { container, root } = mount({ feeAsset, fontScale });
    await act(async () => container.querySelector('[data-testid="swap-get-quote"]').click());
    await act(async () => container.querySelector('[data-testid="swap-review"]').click());

    const dialog = container.querySelector('[data-testid="swap-review-dialog"]');
    expect(dialog).not.toBeNull();
    expect(document.body.style.getPropertyValue('--swap-review-readable-scale')).toBe(expectedScale);
    expect(dialog.querySelector('.review-facts').textContent).toEqual(expect.stringContaining('Pay'));
    expect(dialog.querySelector('.review-facts').textContent).toEqual(expect.stringContaining('Expected output'));
    expect(dialog.querySelector('.review-facts').textContent).toEqual(expect.stringContaining('Minimum output'));
    expect(dialog.querySelector('.review-facts').textContent).toEqual(expect.stringContaining('Slippage'));
    expect(dialog.querySelector('.review-facts').textContent).toEqual(expect.stringContaining('Expiry'));
    expect(dialog.querySelector('[data-testid="swap-approve-wallet"]').textContent).toContain('Approve in Phantom');

    act(() => root.unmount());
  }
});