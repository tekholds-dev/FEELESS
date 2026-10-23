import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { StakeSeg, PerpsEarn, perpsMath } from './EarnStake';
import { setStake, cash, STAKES } from '../lib/earnStake';
import { PoolRow } from './PoolHub';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const BTC = { coin: 'BTC', mark: 81000, ch24: 1.2, fundApr: 11, oiUsd: 9e8, maxLev: 40, venues: ['kraken'] };

test('pure: perps money at a stake × leverage — position, per 1 %, funding a day + who earns it, the wipe-out move, the fan', () => {
  const m = perpsMath(100, 10, BTC);
  expect(m.pos).toBe(1000); expect(m.per1).toBe(10); expect(m.liq).toBe(10); expect(m.earner).toBe('SHORTS');
  expect(m.fundDay).toBeCloseTo(1000 * 0.11 / 365); expect(m.fundYear).toBeCloseTo(110);
  expect(m.fan.find(f => f.m === -10)).toEqual({ m: -10, pnl: -100, wiped: true });                        // at 10× a 10 % drop takes the whole stake
  expect(m.fan.find(f => f.m === 5)).toEqual({ m: 5, pnl: 50, wiped: false });
  expect(perpsMath(5, 2, { fundApr: -20 }).earner).toBe('LONGS'); expect(perpsMath(5, 2, { fundApr: 0 }).earner).toBeNull();
  expect(cash(0.0011)).toBe('$0.0011'); expect(cash(0.055)).toBe('$0.055'); expect(cash(2.5)).toBe('$2.50'); expect(cash(1500)).toBe('$1.5K'); expect(STAKES).toEqual([100, 1000, 10000]);
});

test('one stake for the page: the picker re-quotes every pool row and the perps desk live', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  const pool = { id: 'p1', sym: 'SOL-USDC', proto: 'Orca', kind: 'v3', tvl: 5e6, apy: 36.5, base: 36.5, reward: 0 };
  act(() => setStake(100));
  await act(async () => { root.render(<><StakeSeg /><ol><PoolRow r={pool} /></ol><PerpsEarn row={BTC} lev={10} /></>); });
  expect(q('pool-earn-p1').textContent).toContain('$100 · DAY'); expect(q('pool-earn-p1').textContent).toContain('+$0.100'); expect(q('pool-earn-p1').textContent).toContain('$37 / yr');
  expect(q('perps-earn').textContent).toContain('$1.0K position'); expect(q('perps-earn').textContent).toContain('SHORTS EARN');
  await act(async () => { q('stake-10000').click(); });
  expect(q('stake-10000').getAttribute('aria-checked')).toBe('true');
  expect(q('pool-earn-p1').textContent).toContain('$10K · DAY'); expect(q('perps-earn').textContent).toContain('$10,000 × 10× = $100.0K position');
  expect(el.querySelectorAll('.es-bar.is-wiped')).toHaveLength(1);
  await act(async () => { q('stake-100').click(); });
  await act(async () => { root.unmount(); });
});
