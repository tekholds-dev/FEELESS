import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { levPlan, levPnl } from '../lib/leverage';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
const mockProvider = { publicKey: { toString: () => 'ME' } };
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'ME' }, provider: mockProvider }) }));
const mockCalls = []; const calls = mockCalls;   // plain functions: CRA's resetMocks blanks jest.fn implementations
jest.mock('../lib/lendEarn', () => ({ lendSign: async () => { mockCalls.push('sign'); return 'SIG1'; } }));
jest.mock('../lib/swapEngine', () => ({ engineQuote: async a => { mockCalls.push(['quote', a.inputMint.slice(0, 4), a.outputMint.slice(0, 4), a.amount]); return { order_id: 'o' }; },
  engineSwap: async () => { mockCalls.push('swap'); return { state: 'confirmed' }; } }));
const { RealLeverage } = require('./RealLeverage');
const SOL = { vaultId: 1, coin: 'SOL', mint: 'So11111111111111111111111111111111111111112', dec: 9, price: 100, cf: 0.8, lt: 0.85, penalty: 1, borrowApr: 8.31, borrowableUsd: 1.7e7, minDebt: 1.06, maxLev: 1.7 };
const JUP = { ...SOL, vaultId: 40, coin: 'JUP', mint: 'JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN', dec: 6, price: 0.3, cf: 0.5, lt: 0.7, maxLev: 1.4 };

test('⚡ the plan is the server math: liquidation, exposure, the minimum loan', () => {
  const p = levPlan(SOL, 50, 1.5);
  expect(p.debt).toBe(25); expect(p.exposure).toBeCloseTo(0.75); expect(p.liq).toBeCloseTo(25 / (0.5 * 0.85)); expect(p.toLiqPct).toBeCloseTo(41.18, 1);
  expect(levPlan(SOL, 10, 1.9).lev).toBe(1.7);                 // capped at the vault's safe max
  expect(levPlan(SOL, 3, 1.3).tooSmall).toBe(true); expect(levPlan(SOL, 3, 1.3).minUsd).toBe(4);
  const r = { col: 0.5, debt: 25, entry: 100, liq: 58.8, apr: 10, at: 0, bought: true };
  const v = levPnl(r, 110, 3.156e10);                          // +10 % a year later
  expect(v.pnl).toBeCloseTo(7.5); expect(v.pnlPct).toBeCloseTo(15); expect(v.interest).toBeCloseTo(2.5); expect(v.toLiqPct).toBeCloseTo(46.5, 1);
});

test('⚡ the desk: live markets, the drawn picture, ① lock + borrow → ② buy, then close = ① sell to repay → ② repay all', async () => {
  localStorage.clear(); calls.length = 0;
  const posts = [];
  global.fetch = jest.fn((u, o) => {
    if (o?.method === 'POST') { const b = JSON.parse(o.body); posts.push(b); return Promise.resolve({ ok: true, json: () => Promise.resolve({ transaction: 'T', nftId: 777, plan: b.act === 'open' ? { debt: 12.5, lev: 1.5, liq: 58.82, exposure: 0.375 } : null }) }); }
    return Promise.resolve({ ok: true, json: () => Promise.resolve({ markets: [{ ...SOL, minDebt: 6 }, JUP], positions: [{ vaultId: 40, nftId: 5, coin: 'JUP' }] }) });
  });
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<RealLeverage coin="SOL" />); });
  await act(async () => { await Promise.resolve(); });
  expect(q('real-leverage').textContent).toContain('Long SOL up to 1.7×');
  expect(q('lv-go').textContent).toContain('GO 1.5× LONG SOL · $25'); expect(q('real-leverage').textContent).toContain('$58.82');
  expect(el.querySelectorAll('a[href^="http"]')).toHaveLength(0);   // no link-outs
  expect(q('lv-close-5')).toBeTruthy();                              // a Jupiter position opened elsewhere can still be closed here
  await act(async () => { q('lv-u-10').click(); }); await act(async () => { q('lv-l-1.3').click(); });
  expect(q('lv-go').disabled).toBe(true); expect(q('lv-go').textContent).toContain('Min $21');   // $3 lent < Jupiter's $6 minimum
  await act(async () => { q('lv-c-JUP').click(); }); expect(q('lv-l-1.4')).toBeTruthy(); expect(q('lv-l-1.5')).toBeNull();
  await act(async () => { q('lv-c-SOL').click(); q('lv-u-25').click(); }); await act(async () => { q('lv-l-1.5').click(); });
  await act(async () => { q('lv-go').click(); });
  expect(posts[0]).toEqual({ address: 'ME', act: 'open', vaultId: 1, col: '0.250000000', lev: 1.5 });
  expect(calls).toEqual(['sign', ['quote', 'EPjF', 'So11', '12.475000'], 'swap']);   // ② buys SOL with the borrowed USDC
  expect(q('lv-pos-777').textContent).toContain('SOL 1.5×');
  calls.length = 0;
  await act(async () => { q('lv-close-777').click(); });
  expect(calls[0][1]).toBe('So11'); expect(calls[0][2]).toBe('EPjF'); expect(calls.slice(1)).toEqual(['swap', 'sign']);
  expect(posts[1]).toEqual({ address: 'ME', act: 'close', vaultId: 1, nftId: 777 });
  expect(q('lv-pos-777')).toBeNull();
  act(() => root.unmount()); el.remove();
});
