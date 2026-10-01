import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseGo } from './FuseGo';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const mockSignAll = jest.fn(async txs => txs);
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'W' }, provider: { publicKey: { toString: () => 'W' }, signAllTransactions: (...a) => mockSignAll(...a) } }) }));
jest.mock('@solana/web3.js', () => ({ VersionedTransaction: { deserialize: () => ({ serialize: () => new Uint8Array([1, 2]) }) } }), { virtual: true });
jest.mock('sonner', () => ({ toast: { error: m => console.log('TOAST', m) } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));

test('one wallet approval signs every leg, then each leg executes and confirms', async () => {
  mockSignAll.mockImplementation(async txs => txs);
  const executed = [];
  global.fetch = jest.fn(async (url, opts) => {
    const b = opts?.body ? JSON.parse(opts.body) : {};
    let d = {};
    if (url.endsWith('/quote')) d = { order_id: `o-${b.output_mint}`, input_mint: b.input_mint, output_mint: b.output_mint, amount: b.amount, quote: { transaction: btoa('x'), outAmount: '1000000', inUsdValue: 50 }, output_metadata: { decimals: 6 }, feeless_fee: { bps: 50 } };
    if (url.endsWith('/execute')) { executed.push(b.order_id); d = { state: 'confirmed', signature: `sig-${b.order_id}` }; }
    return { ok: true, json: async () => d };
  });
  const el = document.createElement('div'); document.body.appendChild(el);
  const legs = [{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.6 }, { pairAddress: 'P2', baseAddress: 'B', symbol: 'B', sol: 0.4 }];
  await act(async () => { createRoot(el).render(<FuseGo legs={legs} onClose={() => {}} />); });
  await tick(50);
  const btn = el.querySelector('[data-testid="fg-sign"]');
  expect(btn.textContent).toContain('Approve 2 swaps');
  await act(async () => { btn.click(); }); await tick(300);
  expect(mockSignAll).toHaveBeenCalledTimes(1); expect(mockSignAll.mock.calls[0][0]).toHaveLength(2);
  expect(executed.sort()).toEqual(['o-A', 'o-B']);
  expect(el.textContent).toContain('FUSED');
});
