import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

const mockWallet = { current: null };
jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: mockWallet.current, provider: {}, connect: jest.fn() }) }));
jest.mock('../../lib/batchSend', () => ({ batchSend: (...a) => mockSend(...a) }));
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
jest.mock('../CopyBtn', () => ({ CopyBtn: () => null }));
const mockSend = jest.fn();
const { TreasuryHub } = require('./TreasuryHub');
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const OWNER = 'Own1111111111111111111111111111111111111111';
const money = {
  admin: OWNER, adminSol: 1.5,
  feeAccounts: [{ label: 'SOL fee account (wSOL)', asset: 'wSOL', address: 'FeeSol111', owner: OWNER, amount: 2, ok: true }, { label: 'USDC fee account', asset: 'USDC', address: '', ok: false }],
  reserves: [], splits: [], owners: [OWNER],
  routes: [{ label: 'Multisig', address: 'Msig1111111111111111111111111111111111111111', pct: 60 }, { label: 'Buyback', address: 'Buyb1111111111111111111111111111111111111111', pct: 40 }],
};

test('shows what is wired, previews the split and signs it from the fee account owner', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({}) }));
  mockSend.mockImplementation(async () => ['sig1']);
  mockWallet.current = { chain: 'solana', address: OWNER };
  const call = jest.fn(async path => (path === '/admin/treasury/money' ? money : { total: 2, transfers: 2 }));
  const el = document.createElement('div');
  await act(async () => { createRoot(el).render(<TreasuryHub call={call} />); });
  expect(el.textContent).toContain('USDC fee account exists');
  expect(el.querySelector('.pulse-checks li.bad').textContent).toContain('USDC fee account exists');
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent.startsWith('wSOL')).click(); });
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === 'Max 2').click(); });
  expect(el.querySelector('.m-kv').textContent).toContain('1.2 SOL');
  expect(el.querySelector('.m-kv').textContent).toContain('0.8 SOL');
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent.startsWith('Split 2 wSOL')).click(); });
  expect(mockSend.mock.calls[0][0]).toMatchObject({ owner: OWNER, source: 'FeeSol111', mint: 'So11111111111111111111111111111111111111112' });
  expect(call).toHaveBeenCalledWith('/admin/treasury/split', expect.objectContaining({ body: JSON.stringify({ sigs: ['sig1'], asset: 'wSOL' }) }));
});
