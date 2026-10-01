import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';

jest.mock('../../hooks/useWallet', () => ({ useWallet: () => ({ wallet: { chain: 'solana', address: 'Wa11et1111111111111111111111111111111111111', name: 'Phantom' }, provider: {} }) }));
jest.mock('../../hooks/useMarket', () => ({ useMarket: () => ({ data: { assets: [] } }) }));
// eslint-disable-next-line import/first
import { QuickTrade } from './QuickTrade';

test('quick trade renders for a Solana coin with a wallet (buy + sell)', async () => {
  const order = { order_id: 'o'.repeat(36), expires_at: Date.now() / 1000 + 45, output_metadata: { decimals: 6 }, feeless_fee: { bps: 400, notes: ['20% holder discount (tier 3)'] },
    quote: { transaction: 'AQ==', outAmount: '1000000', otherAmountThreshold: '990000', priceImpactPct: '0.01', inUsdValue: 12 } };
  global.fetch = jest.fn(async url => ({ ok: true, json: async () => (String(url).includes('/rugshield/') ? { level: 'danger', reasons: ['Freeze authority is live'], mint: 'Coin1111111111111111111111111111111111111111' }
    : String(url).includes('/quote') ? order : String(url).includes('/simulate') ? { success: true } : String(url).includes('/points/') ? { points: 12 } : {}) }));
  const errors = [];
  const orig = console.error; console.error = (...a) => { errors.push(a.join(' ')); };
  const host = document.createElement('div'); document.body.appendChild(host);
  const pair = { chainId: 'solana', pairAddress: 'Pair111111111111111111111111111111111111111', baseToken: { address: 'Coin1111111111111111111111111111111111111111', symbol: 'SC' }, priceUsd: '0.001', quoteToken: { symbol: 'SOL' } };
  await act(async () => createRoot(host).render(<QuickTrade pair={pair} />));
  await act(async () => { await new Promise(r => setTimeout(r, 600)); });
  expect(host.querySelector('[data-testid="quick-trade-approve"]')).not.toBeNull();
  await act(async () => [...host.querySelectorAll('.qt-side button')][1].click());
  await act(async () => { await new Promise(r => setTimeout(r, 50)); });
  console.error = orig;
  expect(errors.filter(e => /Error|Cannot|undefined is not|not a function/.test(e)).join('\n')).toBe('');
  expect(host.querySelector('[data-testid="quick-trade"]')).not.toBeNull();
});

test('P&L Exit flips only the quick trade for that coin to Sell (war room + trenches mounted together)', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({}) }));
  Element.prototype.scrollIntoView = jest.fn();
  const coin = n => ({ chainId: 'solana', pairAddress: `Pair${n}`.padEnd(43, '1'), baseToken: { address: `Coin${n}`.padEnd(44, '1'), symbol: `C${n}` }, priceUsd: '0.001', quoteToken: { symbol: 'SOL' } });
  const mountOne = async p => { const h = document.createElement('div'); document.body.appendChild(h); await act(async () => createRoot(h).render(<QuickTrade pair={p} />)); return h; };
  const a = await mountOne(coin('A')); const b = await mountOne(coin('B'));
  const sideOf = h => h.querySelector('.qt-side button.active')?.textContent.trim().toUpperCase();
  expect([sideOf(a), sideOf(b)]).toEqual(['BUY', 'BUY']);
  await act(async () => { window.dispatchEvent(new CustomEvent('feeless:quick-exit', { detail: { pct: 100, mint: coin('A').baseToken.address } })); });
  expect([sideOf(a), sideOf(b)]).toEqual(['SELL', 'BUY']);
});
