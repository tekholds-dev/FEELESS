import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { AvenueRoom, AVENUE_LENSES, HallRoom, pumpVitals, heatOf, blipOf, bankRows } from './CityAvenue';

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

test('🛣 every Avenue building has a room: Pump Radar trades (outside Familia: the war room; inside: the dock), the Bank buys fee-free, no full-page jumps', async () => {
  expect(AVENUE_LENSES.sort()).toEqual(['feebank', 'feecat', 'feedx', 'gas', 'perps', 'pumpradar', 'rep', 'runners', 'sleep', 'trades', 'watch']);
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:war-room', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AvenueRoom lens="pumpradar" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(q('av-pumpradar').textContent).toContain('2/3');
  await act(async () => { q('av-trade-M-CCCxx').click(); });
  expect(seen[0]).toMatchObject({ pairAddress: 'P-CCC' });
  expect(q('av-page')).toBeNull();   // 🏙 the room IS the tool — no jump to another FEELESS page
  await act(async () => { root.render(<AvenueRoom lens="feebank" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  await act(async () => { q('av-buy-fee').click(); });
  expect(seen[1]).toMatchObject({ pairAddress: 'P-FEE' });
  expect(q('av-coin-rfee')).toBeNull();
  await act(async () => { root.render(<AvenueRoom lens="nope" />); });
  expect(el.textContent).toBe('');
  window.removeEventListener('feeless:war-room', on); act(() => root.unmount());
});

test('📈 the Trade Center shows the desk live: meters + by-model chips; staff rows open the seat\'s war room', async () => {
  const TC = { open: 2, green: 1, avgPct: 4, by: { G4: { n: 1, avgPct: -4 }, OSSY: { n: 1, avgPct: 12 } }, staff: true,
    closed: { n: 120, by: { G4: { n: 33, wonPct: 18, median: -6 } }, last: [{ sym: 'McRib', who: 'OWNER', pct: -13.1, rule: 'R2 stop' }] },
    rows: [{ symbol: 'AAA', pair: 'P1', who: 'OSSY', pct: 12, state: 'ride', action: '', why: '' }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(TC) }));
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:war-room', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AvenueRoom lens="trades" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(q('av-trades').textContent).toContain('1/2'); expect(q('av-trades').textContent).toContain('OSSY');
  expect(q('av-closed').textContent).toContain('18% won'); expect(q('av-closed').textContent).toContain('McRib');
  await act(async () => { q('av-seat-0').click(); });
  expect(seen[0]).toMatchObject({ pairAddress: 'P1' });
  window.removeEventListener('feeless:war-room', on); act(() => root.unmount());
});

test('⚖ the Rep Courthouse leads with the week\'s top catches + vitals; a catch opens its case file', async () => {
  const RR = { totals: { caught: 6732, blocklisted: 513, funders: 497, rugs: 15 }, caught: [{ wallet: 'W'.repeat(40) + 'abcd', roles: ['bundler', 'sniper'], launches: 42, blocked: true }, { wallet: 'X'.repeat(44), roles: ['sniper'], launches: 7, blocked: false }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(RR) }));
  const seen = []; const on = e => seen.push(e.detail); window.addEventListener('feeless:investigate', on);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AvenueRoom lens="rep" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(q('av-court').textContent).toContain('6,732'); expect(q('av-court').textContent).toContain('42 launches');
  await act(async () => { q('av-case-0').click(); });
  expect(seen[0]).toBe('W'.repeat(40) + 'abcd');
  window.removeEventListener('feeless:investigate', on); act(() => root.unmount());
});

test('📉 the Perps Desk lists live markets with funding + leverage math and routes to each venue', async () => {
  const PD = { markets: [{ coin: 'SOL', mark: 150, ch24: 3.2, fundApr: 12.5, oiUsd: 9e8, vol24: 2e9, maxLev: 40, venues: ['jupiter', 'drift', 'hyperliquid'] }] };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(PD) }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<AvenueRoom lens="perps" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  const t = q('av-perps').textContent; expect(t).toContain('SOL'); expect(t).toContain('10.0% move');   // 10× default → a 10 % move liquidates
  const links = [...q('av-perps').querySelectorAll('a')].map(a => a.getAttribute('href'));
  expect(links).toEqual(['https://jup.ag/perps/sol', 'https://app.drift.trade/SOL-PERP', 'https://app.hyperliquid.xyz/trade/SOL']);
  act(() => root.unmount());
});

test('🏛 each outer city hall runs its own platform board: Bonk Bay reads LetsBONK, the docks open the court', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, status: 200, headers: { get: () => null }, json: () => Promise.resolve({ pairs: [], totals: {}, caught: [] }), text: () => Promise.resolve('') }));
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<HallRoom city="bay" />); });
  await act(async () => { await new Promise(r => setTimeout(r, 20)); });
  expect(global.fetch.mock.calls.some(c => String(c[0]).includes('scope=bonk'))).toBe(true);
  await act(async () => { root.render(<HallRoom city="docks" />); });
  expect(q('av-court')).not.toBeNull();
  act(() => root.unmount());
});
