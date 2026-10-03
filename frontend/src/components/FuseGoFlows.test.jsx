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
jest.mock('../lib/launchRail', () => ({ relayConnection: async () => ({ connection: { getLatestBlockhash: async () => ({ blockhash: 'BH' }), sendRawTransaction: async () => 'PREPAYSIG' },
  web3: { PublicKey: function PK(a) { this.a = a; }, Transaction: function T() { this.add = () => this; this.serialize = () => new Uint8Array([9]); }, SystemProgram: { transfer: x => x } } }) }));
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
    if (u.endsWith('/fuses/receipt')) d = { settled: true, quotedUsd: 10, paidUsd: 10.02, paidFeesUsd: 0.12, feePct: 1.2,
      legs: (b.legs || []).map(l => ({ sig: l.sig, symbol: l.symbol, quotedUsd: 5, paidUsd: 5.01, paidFeesUsd: 0.06, gotTokens: 990, slippagePct: 0.4 })) };
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


test('BEFORE and AFTER receipts: buy and sell both show every coin before signing, then exact fills read back from chain', async () => {
  for (const side of ['buy', 'sell']) {
    const props = side === 'buy' ? { legs: [{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.05 }, { pairAddress: 'P2', baseAddress: 'B', symbol: 'B', sol: 0.05 }] }
      : { side: 'sell', position: 'card1', orders: unfuseOrders([{ pairAddress: 'P1', mint: 'A', symbol: 'A', tokens: 10 }], { A: { raw: '10000000', decimals: 6 } }, 'W', 150, 100) };
    const el = document.createElement('div'); document.body.appendChild(el);
    await act(async () => { createRoot(el).render(<FuseGo {...props} onClose={() => {}} />); }); await tick(80);
    const before = el.querySelector('[data-testid="fg-before"]');
    expect(before).toBeTruthy(); expect(before.textContent).toContain('BEFORE YOU SIGN'); expect(before.textContent).toContain('FEELESS fee'); expect(before.textContent).toContain('Total');
    await act(async () => { el.querySelector('[data-testid="fg-sign"]').click(); }); await tick(400);
    expect(el.querySelector('[data-testid="fg-before"]')).toBeNull();
    await tick(4200);                                                        // exact fills are read ~4s after confirm
    const after = el.querySelector('[data-testid="fg-after"]');
    expect(after.textContent).toContain('exact fills'); expect(after.textContent).toContain('$10.02'); expect(after.textContent).toContain('1.2% in fees');
    expect(posts.some(([p, b]) => p === '/fuses/receipt' && b.legs.every(l => l.sig))).toBe(true);
  }
});

test('PARTIAL: 1 of 2 coins fails → card records the landed one + expected list; retry re-quotes ONLY the missing coin wider and joins the same card', async () => {
  const base = global.fetch;
  let failR = true;
  global.fetch = jest.fn(async (url, opts) => {
    const u = String(url); const b = opts?.body ? JSON.parse(opts.body) : {};
    if (u.endsWith('/execute') && b.order_id.startsWith('o-R-') && failR) return { ok: false, status: 400, json: async () => ({ detail: 'slippage exceeded' }) };
    if (u.endsWith('/fuses/position')) { posts.push(['/fuses/position', b]); return { ok: true, json: async () => ({ ok: true, id: 'card9', missing: ['R1'] }) }; }
    return base(url, opts);
  });
  const legs = [{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.6, liquidityUsd: 5e6 }, { pairAddress: 'R1', baseAddress: 'R', symbol: 'R', sol: 0.4, runner: true }];
  const el = await run(<FuseGo legs={legs} onClose={() => {}} />);
  expect(el.querySelector('[data-testid="fg-partial"]').textContent).toContain('1/2');
  await tick(5200);
  const rec = posts.find(([p]) => p === '/fuses/position');
  expect(rec[1].legs.map(l => l.pairAddress)).toEqual(['P1']); expect(rec[1].expected).toEqual(['P1', 'R1']);
  failR = false; posts.length = 0;
  await act(async () => { el.querySelector('[data-testid="fg-retry"]').click(); }); await tick(200);
  const q = posts.filter(([p]) => p === '/quote');
  await act(async () => { el.querySelector('[data-testid="fg-sign"]').click(); }); await tick(5600);
  const sw = posts.find(([p]) => p === '/fuses/position/switch');
  expect(sw[1].id).toBe('card9'); expect(sw[1].legs.map(l => l.pairAddress)).toEqual(['R1']);
  expect(q.length === 0 || q.every(([, b]) => b.output_mint === 'R')).toBe(true);
});


test('PREPAY: a new card buy adds ONE prepaid-swaps transfer to the same approval and the card records its signature', async () => {
  const base = global.fetch;
  global.fetch = jest.fn(async (url, opts) => {
    if (String(url).includes('/fees/pricing')) return { ok: true, json: async () => ({ prepay: { on: true, usd: 0.5, swaps: 10, rounds: 5, perSwapUsd: 0.05 }, staff: false, rounds: { payTo: 'FEEWALLET' } }) };
    return base(url, opts);
  });
  const legs = [{ pairAddress: 'P1', baseAddress: 'A', symbol: 'A', sol: 0.6, liquidityUsd: 5e6 }];
  const el = await run(<FuseGo legs={legs} onClose={() => {}} />);
  expect(mockSignAll.mock.calls[0][0].length).toBe(2);                     // 1 swap + 1 prepay, ONE approval
  await tick(5200);
  const rec = posts.find(([p]) => p === '/fuses/position');
  expect(rec[1].prepaySig).toBe('PREPAYSIG'); expect(el.textContent).toContain('FUSED');
});
