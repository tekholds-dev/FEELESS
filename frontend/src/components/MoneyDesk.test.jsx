import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { providersOf, growth, topPoolOf, MoneyDesk, SOL, USDC, needApy, feeApy, feeHunters } from './MoneyDesk';
import { DIR_GROUPS, dirLive } from './FeeCity3D';
import { PLACES } from '../lib/cityPlan';

global.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./FamiliaTrade', () => ({ familiaDocked: () => true, familiaSwap: jest.fn(), familiaTrade: jest.fn() }));
jest.mock('../lib/sharedJson', () => ({ sharedJson: () => new Promise(() => {}), _resetShared: () => {} }));   // no network: rows come in as props
jest.mock('../lib/hotPools', () => ({ useHotPools: () => [{ id: 'H1', pool: 'H1', sym: 'PANGEA-SOL', coin: 'C1', coinSym: 'PANGEA', tvl: 115000, feeDay: 0.06, apy: 2190, ageH: 40, holders: 1962 }] }));
jest.mock('../lib/lpBuilder', () => ({ dammQuote: jest.fn(), dammJoin: jest.fn() }));
const { familiaSwap } = require('./FamiliaTrade');

const ROWS = [
  { id: 'jito', kind: 'stake', proto: 'Jito', sym: 'JITOSOL', hold: 'J1', apy: 7.1, tvl: 1e9 }, { id: 'inf', kind: 'stake', proto: 'Sanctum', sym: 'INF', hold: 'I1', apy: 8.2, tvl: 2e8 },
  { id: 'dust', kind: 'stake', proto: 'Tiny', sym: 'TINY', hold: 'T1', apy: 30, tvl: 1e5 },                                   // too small to lead anyone's money
  { id: 'jl-usdc', kind: 'lend', project: 'jupiter-lend', proto: 'Jupiter Lend', sym: 'USDC', mints: [USDC], apy: 6.4, tvl: 4e8, stable: true },
  { id: 'k-usdc', kind: 'lend', project: 'kamino-lend', proto: 'Kamino Lend', sym: 'USDC', mints: [USDC], apy: 9, tvl: 3e8 },   // no in-place builder → never a provider
  { id: 'usdy', kind: 'rwa', proto: 'Ondo', sym: 'USDY', hold: 'Y1', apy: 4.7, tvl: 1.8e8 },
  { id: 'p0', kind: 'v3', proto: 'Raydium', sym: 'IOST-USDC', pair: 'P0', apy: 0, tvl: 9e7 }, { id: 'p1', kind: 'v2', proto: 'Raydium', sym: 'RAY-SOL', pair: 'P1', apy: 12, tvl: 5e6 },
];

test('💸 providers are only what runs IN FEELESS: LSTs by swap, Jupiter Lend by deposit, treasuries by swap — best paying first, the tapped one leads', () => {
  const st = providersOf('stake', ROWS); expect(st.map(p => p.sym)).toEqual(['INF', 'JITOSOL']); expect(st[0]).toMatchObject({ how: 'swap', from: SOL, to: 'I1' });
  const ln = providersOf('lend', ROWS); expect(ln[0]).toMatchObject({ how: 'lend', sym: 'USDC', name: 'Jupiter Lend' }); expect(ln.some(p => p.id === 'k-usdc')).toBe(false);
  expect(providersOf('rwa', ROWS).some(p => p.id === 'usdy')).toBe(false); expect(providersOf('best', ROWS).some(p => p.id === 'usdy')).toBe(false);   // 🇺🇸 issuer-restricted treasuries are never routed
  expect(providersOf('rwa', ROWS)[0]).toMatchObject({ how: 'lend', sym: 'USDC' });
  expect(providersOf('stake', ROWS, ROWS[0])[0].id).toBe('jito');                                       // the building / row you tapped leads
  expect(providersOf('perps', ROWS)[0]).toMatchObject({ sym: 'JLP', how: 'swap', from: USDC });          // the house side of perps, as a token
  expect(providersOf('best', ROWS).map(p => p.apy)).toEqual([...providersOf('best', ROWS).map(p => p.apy)].sort((a, b) => b - a));
  expect(topPoolOf(ROWS, 'Raydium').id).toBe('p1');                                                       // a paying SOL pair beats a deeper 0 % pool
  const lp = providersOf('lp', ROWS, topPoolOf(ROWS, 'Raydium')); expect(lp[0]).toMatchObject({ how: 'trade', id: 'p1' }); expect(lp.length).toBe(3);
});

test('📈 the money math compounds daily, top-ups compound on top, a year doubles at ~69.3 / APY', () => {
  const g = growth(1000, 10); expect(g.day).toBeCloseTo(0.274, 2); expect(g.end).toBeCloseTo(1105.2, 0); expect(g.pts).toHaveLength(13); expect(g.double).toBeCloseTo(6.93, 1);
  const t = growth(1000, 10, 100); expect(t.paid).toBe(2200); expect(t.end).toBeGreaterThan(2200); expect(t.earned).toBeCloseTo(t.end - 2200, 6);
  expect(growth(1000, 0).double).toBeNull(); expect(growth(5, 8).day).toBeLessThan(0.002);              // why $5 does nothing
});

test('🖱 the desk: pick a provider + an amount → the numbers re-quote, the action runs in place (no link out)', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<MoneyDesk job="stake" rows={ROWS} />); });
  expect(el.querySelectorAll('a[href^="http"]')).toHaveLength(0);
  expect(q('md-risk-safe').getAttribute('aria-checked')).toBe('true');   // a stake building opens on its safe yields
  expect(q('md-prov-inf').getAttribute('aria-checked')).toBe('true'); expect(q('money-desk-stake').textContent).toContain('8.2%');
  await act(async () => { q('md-amt-1000').click(); }); expect(q('money-desk-stake').textContent).toContain('+$0.225');   // $1K × 8.2 % / 365
  expect(q('md-goal').textContent).toContain('18% APY');   // $0.50 a day on $1K = 18.25 % a year
  await act(async () => { q('md-prov-jito').click(); }); expect(q('md-go').textContent).toContain('SOL → JITOSOL');
  await act(async () => { q('md-go').click(); }); expect(familiaSwap).toHaveBeenCalledWith({ from: SOL, to: 'J1', amount: undefined });
  await act(async () => { root.render(<MoneyDesk job="lend" rows={ROWS} />); });
  await act(async () => { q('md-go').click(); }); expect(q('lend-jl-usdc')).not.toBeNull(); expect(q('lend-amt').value).toBe('1000');   // Jupiter Lend, prefilled with the amount you picked, your wallet signs
  act(() => root.unmount()); el.remove();
});

test('🧭 the directory leads with the money and still reaches every place', () => {
  const keys = DIR_GROUPS.flatMap(([, ks]) => ks); expect(keys.sort()).toEqual(PLACES.map(p => p.key).sort());
  expect(DIR_GROUPS[0][0]).toContain('MONEY'); expect(DIR_GROUPS[0][1].every(k => PLACES.find(p => p.key === k).money || ['pumpradar', 'runners'].includes(k))).toBe(true);
  expect(dirLive('sleep', { pools: ROWS })).toContain('while you sleep'); expect(dirLive('court', { pools: ROWS })).toBeNull();
});

test('💵 small money, honest: $0.50 a day on $10 needs ~1,825 % APY; only busy LP pools pay fees like that — and the hunters list says so', () => {
  expect(Math.round(needApy(10))).toBe(1825); expect(Math.round(needApy(5))).toBe(3650); expect(needApy(1000)).toBeCloseTo(18.25, 2);
  const kimchi = { id: 'k', kind: 'v2', proto: 'PumpSwap', sym: 'KIMCHI-SOL', src: 'pair', tvl: 370000, vol: 10.1e6 };   // 27× its size a day
  expect(feeApy(kimchi)).toBeGreaterThan(1800);                                             // 10.1M × 0.20 % × 365 ÷ 370K ≈ 1,993 %
  expect(feeApy({ ...kimchi, proto: 'Orca' })).toBeNull();                                  // unknown fee tier → no guess
  expect(feeApy({ base: 25, proto: 'Raydium' })).toBe(25);                                  // a published fee APY wins
  const list = feeHunters([kimchi, ROWS[7], { ...kimchi, id: 'thin', tvl: 5e4 }]); expect(list.map(x => x.r.id)).toEqual(['k']);   // ROWS[7] has no fee data · too thin never shows
  expect(((10 * list[0].apy) / 100 / 365)).toBeGreaterThan(0.5);                          // $10 there ≈ $0.55 a day in fees (before price moves)
});

test('🚀 MOON by default where money can move fast: the best desk leads with tight v3 bands; ±5 % concentrates more than ±25 %', async () => {
  const { moonHunters, bandBoost } = require('./MoneyDesk');
  expect(bandBoost(5)).toBeGreaterThan(bandBoost(10)); expect(bandBoost(10)).toBeGreaterThan(bandBoost(25)); expect(bandBoost(100)).toBeCloseTo(1, 5);
  const v3 = [{ id: 'a', kind: 'v3', proto: 'Raydium', sym: 'WXRP-USDC', tvl: 5e5, base: 66 }, { id: 'b', kind: 'v3', proto: 'Orca', sym: 'SOL-BONK', tvl: 3e5, base: 29 }, { id: 'c', kind: 'v2', proto: 'PumpSwap', sym: 'X', tvl: 4e5, vol: 9e6 }];
  const m = moonHunters(v3, 10); expect(m.map(x => x.r.id)).toEqual(['a', 'b']); expect(m[0].apy).toBeCloseTo(66 * bandBoost(10), 5);   // v2 can't be tightened
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el); const q = id => el.querySelector(`[data-testid="${id}"]`);
  await act(async () => { root.render(<MoneyDesk job="best" rows={[...ROWS, ...v3]} />); });
  expect(q('md-risk-moon').getAttribute('aria-checked')).toBe('true'); expect(q('md-moon').textContent).toContain('WXRP-USDC'); expect(q('md-go')).toBeNull();   // no safe clutter in MOON
  expect(q('md-hot').textContent).toContain('PANGEA-SOL'); expect(q('md-hot').textContent).toContain('6.0%/day'); expect(q('md-hot').textContent).toContain('+$0.200');   // $10 × 6 % ÷ 3 overnight
  await act(async () => { q('md-hot-join-H1').click(); }); expect(q('md-join-H1')).not.toBeNull(); expect(q('md-join-H1').querySelectorAll('a[href^="http"]')).toHaveLength(0);
  await act(async () => { q('md-risk-degen').click(); }); expect(q('md-hunters').textContent).toContain('X');
  await act(async () => { q('md-risk-safe').click(); }); expect(q('md-go')).not.toBeNull();
  act(() => root.unmount()); el.remove();
});
