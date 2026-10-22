import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AvenueRoom, AVENUE_LENSES, pumpVitals, heatOf, blipOf, bankRows } from './CityAvenue';

const pair = (sym, m5, extra = {}) => ({ chainId: 'solana', pairAddress: `P-${sym}`, baseToken: { address: `M-${sym}xx`, symbol: sym }, priceChange: { m5 }, volume: { h1: 1000 }, marketCap: 2e5, ...extra });
const PUMP = { pairs: [pair('AAA', 12), pair('BBB', -6), pair('CCC', 40)] };
const ASSETS = { assets: [{ id: 'fee', pair: { ...pair('FEE', 0), priceUsd: '0.0012', priceChange: { h24: 8.5 }, liquidity: { usd: 45000 } } }, { id: 'rfee', pair: null }] };
const q = id => document.querySelector(`[data-testid="${id}"]`);

beforeEach(() => {
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, status: 200, headers: { get: () => null }, json: () => Promise.resolve(String(url).includes('/assets') ? ASSETS : PUMP), text: () => Promise.resolve('') }));
});

test('📡 Pump Radar vitals: how many are up, the average 5m move, the hour volume, the top mover; heat + blips are bounded', () => {
  const v = pumpVitals(PUMP.pairs);
  expect(v).toMatchObject({ n: 3, up: 2, vol1h: 3000, top: { sym: 'CCC', m5: 40 } }); expect(v.avg5m).toBeCloseTo(15.33, 1);
  expect(pumpVitals([])).toMatchObject({ n: 0, up: 0, avg5m: null, top: null });
  expect(heatOf(-50)).toBe(0); expect(heatOf(100)).toBe(1); expect(heatOf(10)).toBeCloseTo(0.5);
  const b0 = blipOf(PUMP.pairs[0], 0, 3); const b2 = blipOf(PUMP.pairs[2], 2, 3);
  expect(Math.hypot(b0.x - 110, b0.y - 110)).toBeLessThan(Math.hypot(b2.x - 110, b2.y - 110));      // #1 nearest the centre
  for (const b of [b0, b2]) { expect(b.x).toBeGreaterThan(10); expect(b.x).toBeLessThan(210); }
  expect(blipOf(PUMP.pairs[1], 1, 3).up).toBe(false);
});

test('🏦 the $FEE Bank reads /assets: a row per coin with a pool, nothing invented for one without', () => {
  expect(bankRows(ASSETS)).toEqual([expect.objectContaining({ id: 'fee', sym: 'FEE', price: 0.0012, ch: 8.5, liq: 45000 })]);
  expect(bankRows(null)).toEqual([]);
});

test('🛣 every Avenue building has a room: Pump Radar trades open the war room (the wallet signs), the Bank buys fee-free, full page links', async () => {
  expect(AVENUE_LENSES.sort()).toEqual(['feebank', 'feecat', 'feedx', 'gas', 'pumpradar', 'rep', 'runners', 'sleep', 'watch']);
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:war-room', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AvenueRoom lens="pumpradar" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(q('av-pumpradar').textContent).toContain('2/3');
  await act(async () => { q('av-trade-M-CCCxx').click(); });
  expect(seen[0]).toMatchObject({ pairAddress: 'P-CCC' });
  expect(q('av-page').getAttribute('href')).toBe('/terminal/pump');
  await act(async () => { root.render(<AvenueRoom lens="feebank" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  await act(async () => { q('av-buy-fee').click(); });
  expect(seen[1]).toMatchObject({ pairAddress: 'P-FEE' });
  expect(q('av-coin-rfee')).toBeNull();
  await act(async () => { root.render(<AvenueRoom lens="nope" />); });
  expect(el.textContent).toBe('');
  window.removeEventListener('feeless:war-room', on); act(() => root.unmount());
});
