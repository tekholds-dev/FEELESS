import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { StakeSeg } from './EarnStake';
import { setStake, cash, STAKES } from '../lib/earnStake';
import { PoolRow } from './PoolHub';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
test('pure: cash words + the stake ladder', () => {
  expect(cash(0.0011)).toBe('$0.0011'); expect(cash(0.055)).toBe('$0.055'); expect(cash(2.5)).toBe('$2.50'); expect(cash(1500)).toBe('$1.5K'); expect(STAKES).toEqual([100, 1000, 10000]);
});

test('one stake for the page: the picker re-quotes every pool row live', async () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  const pool = { id: 'p1', sym: 'SOL-USDC', proto: 'Orca', kind: 'v3', tvl: 5e6, apy: 36.5, base: 36.5, reward: 0 };
  act(() => setStake(100));
  await act(async () => { root.render(<><StakeSeg /><ol><PoolRow r={pool} /></ol></>); });
  expect(q('pool-earn-p1').textContent).toContain('$100 · DAY'); expect(q('pool-earn-p1').textContent).toContain('+$0.100'); expect(q('pool-earn-p1').textContent).toContain('$37 / yr');
  await act(async () => { q('stake-10000').click(); });
  expect(q('stake-10000').getAttribute('aria-checked')).toBe('true');
  expect(q('pool-earn-p1').textContent).toContain('$10K · DAY');
  await act(async () => { q('stake-100').click(); });
  await act(async () => { root.unmount(); });
});
