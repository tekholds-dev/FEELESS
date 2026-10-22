import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Realtor, forSale, tierOf } from './Realtor';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const V = { cities: [{ key: 'fee', name: 'FEE CITY', boroughs: ['fee'], plots: 3, held: 1 }, { key: 'harbor', name: 'Pump Harbor', boroughs: ['harbor', 'market'], plots: 3, held: 0 }],
  boroughs: [{ key: 'fee', name: 'Fee City', tier: 2.5, icon: '👑' }, { key: 'harbor', name: 'Pump Harbor', tier: 1.0 }, { key: 'market', name: 'Meteora Market', tier: 1.2 }],
  blocks: [{ id: 'fee-0', b: 'fee', owner: 'x' }, { id: 'fee-1', b: 'fee' }, { id: 'fee-2', b: 'fee' }, { id: 'harbor-0', b: 'harbor' }, { id: 'market-0', b: 'market' }, { id: 'market-1', b: 'market' }],
  me: { bank: 7000, turf: ['a'], prices: { 'fee-1': 9600, 'fee-2': 6000, 'harbor-0': 2400, 'market-0': 2880, 'market-1': 2880 } }, rules: { turfMax: 12 } };

test('pure: free plots by tier, cheapest first, what the bank covers', () => {
  expect(tierOf(2.5)[0]).toBe('prime'); expect(tierOf(1.4)[0]).toBe('uptown'); expect(tierOf(1.0)[0]).toBe('midtown'); expect(tierOf(0.8)[0]).toBe('back');
  const fee = forSale(V, 'fee');
  expect(fee.map(g => g.tier[0])).toEqual(['prime']); expect(fee[0].plots.map(p => [p.id, p.ok])).toEqual([['fee-2', true], ['fee-1', false]]);
  expect(forSale(V, 'harbor')[0].plots.map(p => p.id)).toEqual(['harbor-0', 'market-0', 'market-1']); expect(forSale(V, 'nope')).toEqual([]);
});

test('the realtor lists every city and buys with one tap', async () => {
  const act_ = jest.fn(); const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<Realtor v={V} act={act_} busy={false} onFly={() => {}} />); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('rl-city-fee').getAttribute('aria-checked')).toBe('true'); expect(q('rl-buy-fee-1').disabled).toBe(true);
  await act(async () => { q('rl-buy-fee-2').click(); });
  expect(act_).toHaveBeenCalledWith({ act: 'buy', block: 'fee-2' }, 'Bought fee-2');
  await act(async () => { q('rl-city-harbor').click(); });
  expect(q('rl-tier-midtown').textContent).toContain('3 plots'); expect(q('rl-lot-harbor-0').textContent).toContain('2,400 MP');
  await act(async () => { root.unmount(); });
});
