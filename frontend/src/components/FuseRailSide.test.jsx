import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseRail } from './FuseRail';
import { FuseSide } from './FuseSide';
import { quoteLine } from './FuseGo';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./EcosystemChat', () => ({ __esModule: true, default: ({ room }) => <div data-testid="chat">{room}</div> }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const card = style => ({ style, pools: ['a', 'b', 'c'], fitness: 80, bornGen: 3, arena: style === 'yield' ? { avgPct: 2.5, runs: 4 } : null, parts: { grade: 'B', aprScore: 40, momentum24h: 1, calm: 70, feeDragPct: 1, impactLegs: 0 },
  legs: ['a', 'b', 'c'].map(p => ({ pairAddress: p, symbol: p.toUpperCase(), weight: 33, liquidityUsd: 1e6 })) });

test('prebuilt rail: one flip card per strategy, Use loads it with the budget in SOL', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [card('yield'), card('degen')], budgetUsd: 20, solUsd: 200 }) }));
  const onUse = jest.fn();
  const el = await mount(<FuseRail onUse={onUse} />);
  expect(el.querySelectorAll('.frail-item')).toHaveLength(2); expect(el.textContent).toContain('arena +2.5%');
  await act(async () => { el.querySelector('[data-testid="frail-use-yield"]').click(); });
  expect(onUse.mock.calls[0][0]).toHaveLength(3); expect(onUse.mock.calls[0][1]).toBeCloseTo(0.1);
  expect(global.fetch.mock.calls[0][0]).toContain('/fuses/prebuilt?legs=3');
});

test('fuse side: chat is the one fuse-lab room; Holders slides in with live P&L', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ total: 1, holders: [{ address: 'A'.repeat(43), handle: 'degen', fuses: 2, names: ['Core'], pnlPct: 12.5 }] }) }));
  const el = await mount(<FuseSide />);
  expect(el.querySelector('[data-testid="chat"]').textContent).toBe('fuse-lab');
  await act(async () => { el.querySelector('[data-testid="fside-holders"]').click(); }); await tick(20);
  expect(el.querySelector('.fside-track').className).toContain('at-holders'); expect(el.textContent).toContain('@degen'); expect(el.textContent).toContain('+12.5%');
});

test('receipt line: $ in, FEELESS fee, network fee and impact from the quote', () => {
  const l = quoteLine({ request: { amount: '0.5' }, target: { symbol: 'X' }, order: { feeless_fee: { bps: 50 }, output_metadata: { decimals: 6 },
    quote: { inUsdValue: 100, outAmount: '2000000', signatureFeeLamports: 5000, prioritizationFeeLamports: 95000, priceImpactPct: '0.004' } } });
  expect(l.usd).toBe(100); expect(l.feeUsd).toBe(0.5); expect(l.tokens).toBe(2); expect(l.networkUsd).toBeCloseTo(0.02); expect(l.impact).toBeCloseTo(0.4);
});

test('receipt line knows the pool: route, depth, your share of it, price per coin', () => {
  const l = quoteLine({ leg: { weight: 40, liquidityUsd: 50000, dex: 'raydium' }, request: { amount: '0.5' }, target: { symbol: 'X' },
    order: { feeless_fee: { bps: 50 }, output_metadata: { decimals: 6 }, quote: { inUsdValue: 100, outAmount: '2000000', routePlan: [{ swapInfo: { label: 'Raydium CLMM' } }] } } });
  expect(l.route).toEqual(['Raydium CLMM']); expect(l.share).toBeCloseTo(0.2); expect(l.price).toBe(50); expect(l.weight).toBe(40);
});
