import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import DustCleanup, { plan } from './DustCleanup';

jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'Own1111111111111111111111111111111111111111' }, provider: null, connect: jest.fn() }) }));

const rows = [
  { pubkey: 'A1', mint: 'M1', symbol: 'DUST', ui: 0.01, raw: 10, decimals: 3, usd: 0.0003, rentSol: 0.00204, actions: ['burn', 'swap'], best: 'burn' },
  { pubkey: 'A2', mint: 'M2', symbol: 'EMPTY', ui: 0, raw: 0, decimals: 6, usd: null, rentSol: 0.00204, actions: ['close'], best: 'close' },
  { pubkey: 'A3', mint: 'M3', symbol: 'BIG', ui: 5, raw: 5000, decimals: 3, usd: 12.5, rentSol: 0.00204, actions: ['swap', 'burn'], best: 'swap' },
];

test('the plan counts swaps, burns, closes and the rent that comes back', () => {
  const p = plan(rows, { A1: true, A2: true, A3: true }, {});
  expect(p.swaps.map(r => r.symbol)).toEqual(['BIG']); expect(p.burns.length).toBe(1); expect(p.closes.length).toBe(1);
  expect(p.rentSol).toBeCloseTo(0.00408, 6); expect(p.swapUsd).toBe(12.5);
  expect(plan(rows, { A3: true }, { A3: 'burn' }).burns.map(r => r.symbol)).toEqual(['BIG']);   // the owner's choice wins
});

test('reads the wallet, selects dust, and a burn needs the acknowledge box before anything is sent', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve({ rows, summary: { dust: 2, rentBackSol: 0.00408, swapUsd: 12.5 } }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<DustCleanup />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelector('[data-testid="dc-summary"]').textContent).toContain('◎0.0041');
  expect(el.querySelectorAll('.dc-row').length).toBe(3);
  await act(async () => { el.querySelector('[data-testid="dc-select-dust"]').click(); });
  expect(el.querySelector('[data-testid="dc-go"]').textContent).toContain('Clean up 2');
  expect(el.querySelector('[data-testid="dc-ack"]')).not.toBeNull();
  const calls = global.fetch.mock.calls.length;
  await act(async () => { el.querySelector('[data-testid="dc-go"]').click(); });
  expect(global.fetch.mock.calls.length).toBe(calls);   // not acknowledged → nothing built, nothing sent
});

test('EVM reads every chain the wallet holds, grouped by chain; the native coin is gas and cannot be picked', async () => {
  const { grouped, plan: pl } = require('./DustCleanup');
  const evm = [
    { chain: 'bsc', chainId: 56, address: '0xT1', symbol: 'CAKE', usd: 3, best: 'swap', actions: ['swap'], raw: '1', ui: 1 },
    { chain: 'ethereum', chainId: 1, address: '0x0000000000000000000000000000000000000000', symbol: 'ETH', usd: 9, best: 'gas', native: true, actions: [], raw: '1', ui: 1 },
    { chain: 'ethereum', chainId: 1, address: '0xT2', symbol: 'PEPE', usd: 0.1, best: 'dust', actions: ['swap'], raw: '1', ui: 1 },
  ];
  const chains = [{ chain: 'ethereum', usd: 9.1, coins: 2 }, { chain: 'bsc', usd: 3, coins: 1 }];
  expect(grouped(evm, chains).map(r => r.symbol)).toEqual(['ETH', 'PEPE', 'CAKE']);
  const p = pl(evm, { '1:0x0000000000000000000000000000000000000000': true, '1:0xT2': true, '56:0xT1': true }, {});
  expect(p.chosen.map(r => r.symbol).sort()).toEqual(['CAKE', 'PEPE']);   // native gas never chosen
  expect(p.dust.map(r => r.symbol)).toEqual(['PEPE']); expect(p.swaps.map(r => r.symbol)).toEqual(['CAKE']);
});
