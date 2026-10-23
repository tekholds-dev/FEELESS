import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { grow, split, hasRun, RUN_KEY } from './FiveRun';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'ME' } }) }));
const ROW = { project: 'jupiter-lend', mints: ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'], sym: 'USDC' };
jest.mock('./PoolHub', () => ({ usePools: () => ({ pools: [{ project: 'jupiter-lend', mints: ['EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v'], sym: 'USDC' }] }),
  LendBox: ({ r, amount0 }) => <p data-testid="lend-box">{r.sym} {amount0}</p> }));
const { FiveRun } = require('./FiveRun');
const ASSETS = [{ sym: 'USDC', mint: 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v', jl: 'jlUSDC', dec: 6, apy: 7.28, price: 1 }, { sym: 'SOL', mint: 'So11111111111111111111111111111111111111112', jl: 'jlSOL', dec: 9, apy: 3.83, price: 100 }];

test('💵 compounding math + the ticker digits', () => {
  expect(grow(5, 7.28, 31557600)).toBeCloseTo(5.364); expect(grow(5, 7.28, 8 * 3600) - 5).toBeCloseTo(0.000321, 5);
  expect(split(5.000384123)).toEqual(['5.00', '038412']);
});

test('💵 the $5 run: no deposit → a live $5 ticker + START; with one → YOUR on-chain balance, Jupiter\'s earnings, + $5 / withdraw', async () => {
  localStorage.clear(); let body = { assets: ASSETS, positions: [], minUsd: 5 };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(body) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<FiveRun />); }); await act(async () => { await Promise.resolve(); });
  expect(q('five-run').textContent).toContain('WHAT $5 DOES WHILE YOU WATCH'); expect(q('fr-tick').textContent).toMatch(/^\$5\.00\d{6}$/);
  expect(q('five-run').textContent).toContain('TONIGHT+$0.00032');                                   // tonight, honestly small
  await act(async () => { q('fr-start').click(); }); expect(q('lend-box').textContent).toBe('USDC 5');
  await act(async () => { q('fr-a-SOL').click(); }); expect(q('lend-box')).toBeNull();
  expect(hasRun()).toBe(false);
  body = { assets: ASSETS, positions: [{ ...ASSETS[0], balance: 5.00042, usd: 5.00042, earned: 0.00042 }], minUsd: 5 };
  await act(async () => { q('fr-a-USDC').click(); root.unmount(); });
  const root2 = createRoot(el);
  await act(async () => { root2.render(<FiveRun />); }); await act(async () => { await Promise.resolve(); });
  expect(q('five-run').textContent).toContain('YOUR USDC ON JUPITER LEND'); expect(q('fr-tick').textContent).toMatch(/^\$5\.00\d{6}$/);
  expect(q('five-run').textContent).toContain('+$0.00042 earned so far'); expect(localStorage.getItem(RUN_KEY)).toBe('1');
  await act(async () => { q('fr-add').click(); }); expect(q('lend-box').textContent).toBe('USDC 5');
  act(() => root2.unmount()); el.remove();
});
