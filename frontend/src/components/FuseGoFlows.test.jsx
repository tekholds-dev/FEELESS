// One-click wallet flows for Fuse cards, end to end on the client (wallet + network faked; nothing real is signed):
// BUY → one approval → every leg executes → the card is recorded with the plan; SELL (take profit / withdraw) → one approval →
// the close is recorded with the sell signatures; SWITCH (sell one + buy one in ONE approval) → both are reported to onLanded.
import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseGo } from './FuseGo';
import { unfuseOrders, SOL_MINT } from '../lib/fuseGo';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.setTimeout(20000);
const mockSignAll = jest.fn(async txs => txs);
jest.mock('../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'W' }, provider: { publicKey: { toString: () => 'W' }, signAllTransactions: (...a) => mockSignAll(...a) } }) }));
jest.mock('@solana/web3.js', () => ({ VersionedTransaction: { deserialize: () => ({ serialize: () => new Uint8Array([1, 2]) }) } }), { virtual: true });
jest.mock('../lib/chatSession', () => ({ readChatSession: () => 'SES' }));
jest.mock('sonner', () => ({ toast: { error: jest.fn(), success: jest.fn() } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
let posts;
beforeEach(() => {
  mockSignAll.mockImplementation(async txs => txs); posts = [];
  global.fetch = jest.fn(async (url, opts) => {
    const b = opts?.body ? JSON.parse(opts.body) : {}; const u = String(url);
    if (u.includes('/api/reputation/')) posts.push([u.replace(/.*\/api\/reputation/, ''), b]);
    let d = {};
    if (u.endsWith('/quote')) d = { order_id: `o-${b.output_mint}-${b.input_mint}`, input_mint: b.input_mint, output_mint: b.output_mint, amount: b.amount, quote: { transaction: btoa('x'), outAmount: '1000000', inUsdValue: 10 }, output_metadata: { decimals: 6 }, feeless_fee: { bps: 50 } };
    if (u.endsWith('/execute')) d = { state: 'confirmed', signature: `sig-${b.order_id}` };
    return { ok: true, json: async () => d };
  });
});
const run = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(60);
  await act(async () => { el.querySelector('[data-testid="fg-sign"]').click(); }); await tick(400); return el; };

test('BUY: one approval → card recorded with every confirmed leg + the risk plan', async () => {
  const legs = [{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.6 }, { pairAddress: 'R1', baseAddress: 'R', symbol: 'R', sol: 0.4, runner: true }];
  const el = await run(<FuseGo legs={legs} plan={{ risk: 'balanced' }} onClose={() => {}} />);
  expect(mockSignAll).toHaveBeenCalledTimes(1); expect(el.textContent).toContain('FUSED');
  await tick(5200);
  const rec = posts.find(([p]) => p === '/fuses/position');
  expect(rec[1].legs.map(l => [l.pairAddress, l.role])).toEqual([['P1', 'pool'], ['R1', 'runner']]); expect(rec[1].session).toBe('SES');
});

test('SELL (take profit 50%): one approval → close recorded with the sell signatures', async () => {
  const orders = unfuseOrders([{ pairAddress: 'P1', mint: 'A', symbol: 'A', tokens: 10 }], { A: { raw: '10000000', decimals: 6 } }, 'W', 150, 50);
  expect(orders[0].request).toMatchObject({ input_mint: 'A', output_mint: SOL_MINT, amount: '5' });
  const el = await run(<FuseGo side="sell" orders={orders} position="card1" onClose={() => {}} />);
  expect(el.textContent).toContain('UNFUSED'); await tick(5200);
  const close = posts.find(([p]) => p === '/fuses/position/close');
  expect(close[1]).toMatchObject({ id: 'card1', session: 'SES' }); expect(close[1].signatures[0]).toMatch(/^sig-o-/);
});

test('SWITCH: sell one coin + buy one coin in ONE approval → both legs reported for the card', async () => {
  const onLanded = jest.fn();
  const orders = [...unfuseOrders([{ pairAddress: 'P1', mint: 'A', symbol: 'A', tokens: 10 }], { A: { raw: '10000000', decimals: 6 } }, 'W'),
    { leg: { pairAddress: 'PN', symbol: 'NEW', role: 'runner' }, target: { mint: 'N', symbol: 'NEW' }, request: { input_mint: SOL_MINT, output_mint: 'N', amount: '0.1', slippage_bps: 150, wallet: 'W' } }];
  await run(<FuseGo orders={orders} onLanded={onLanded} onClose={() => {}} />);
  expect(mockSignAll).toHaveBeenCalledTimes(1); expect(mockSignAll.mock.calls[0][0]).toHaveLength(2);
  const landed = onLanded.mock.calls[0][0];
  expect(landed.map(l => [l.symbol, l.side])).toEqual([['A', 'sell'], ['NEW', 'buy']]); expect(onLanded.mock.calls[0][1]).toBe('SES');
});

test('a wallet that refuses signs NOTHING and sends nothing', async () => {
  mockSignAll.mockImplementation(async () => { throw new Error('User rejected the request'); });
  await run(<FuseGo legs={[{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.5 }]} onClose={() => {}} />);
  expect(global.fetch.mock.calls.some(([u]) => String(u).endsWith('/execute'))).toBe(false);
});
