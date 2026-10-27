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

test('💸 any typed amount quotes the page; the high-yield row names the risk and skips dust', async () => {
  const { highYield } = await import('./PoolHub');
  const rows = [{ id: 'a', sym: 'A-USDC', kind: 'v3', tvl: 5e5, apy: 240, base: 20, reward: 220 }, { id: 'b', sym: 'B', kind: 'lend', tvl: 4e7, apy: 18, base: 18 },
    { id: 'c', sym: 'DUST', kind: 'v2', tvl: 1e4, apy: 900 }, { id: 'd', sym: 'LOW', kind: 'stake', tvl: 1e9, apy: 7 }];
  const hy = highYield(rows);
  expect(hy.map(x => x.r.id)).toEqual(['a', 'b']);                                     // dust + low APY stay out, biggest first
  expect(hy[0].risk).toEqual(['impermanent loss', 'mostly reward tokens', 'thin pool', 'may not last']); expect(hy[1].risk).toEqual(['contract risk']);
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<StakeSeg />); });
  const inp = el.querySelector('[data-testid="stake-in"]');
  await act(async () => { const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(inp, '2500'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  expect(localStorage.getItem('feeless.earn.stake')).toBe('2500');
  await act(async () => { root.unmount(); }); act(() => setStake(100));
});
