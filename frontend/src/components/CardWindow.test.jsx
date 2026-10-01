import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { CardEarnings } from './CardEarnings';
import { topupOrders, SOL_MINT } from '../lib/fuseGo';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const L = [{ pairAddress: 'PA', mint: 'MA', symbol: 'A', heldUsd: 30 }, { pairAddress: 'PB', mint: 'MB', symbol: 'B', heldUsd: 10 }, { pairAddress: 'PC', mint: 'MC', symbol: 'C', soldUsd: 5 }];

test('top up: equal / by weight / one coin — SOL in, buys only, sold coins skipped', () => {
  const amt = o => o.map(x => [x.leg.symbol, Number(x.request.amount)]);
  expect(amt(topupOrders(L, 1, 'equal', 'W'))).toEqual([['A', 0.5], ['B', 0.5]]);
  expect(amt(topupOrders(L, 1, 'weight', 'W'))).toEqual([['A', 0.75], ['B', 0.25]]);
  expect(amt(topupOrders(L, 1, 'one', 'W', 'PB'))).toEqual([['B', 1]]);
  expect(topupOrders(L, 1, 'equal', 'W').every(o => o.request.input_mint === SOL_MINT)).toBe(true);
  expect(topupOrders(L, 0.0001, 'equal', 'W')).toEqual([]);
});

test('card window: actions, ❄ freeze per coin, last-24h autos linked to their action', async () => {
  const onFreeze = jest.fn(); const top = jest.fn();
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CardEarnings title="Moon" taken={2} compounded={1} onClose={() => {}} onFreeze={onFreeze}
    legs={[{ ...L[0], frozen: true, pnlPct: 12 }, { ...L[1], pnlPct: -3 }]} autos={[{ at: Date.now() / 1000 - 120, text: '💸 Moon hit +50%', url: '/terminal/fuse?tab=cards&collect=c1&pct=33' }]}
    actions={[{ label: '＋ Top up', onClick: top, testid: 'cw-topup' }]} />); });
  const w = document.querySelector('[data-testid="card-earnings"]');
  expect(w.textContent).toContain('❄ Frozen'); expect(w.textContent).toContain('+12.0%');
  expect(w.querySelector('.ce-auto').getAttribute('href')).toContain('collect=c1');
  await act(async () => { w.querySelector('[data-testid="freeze-PB"]').click(); });
  expect(onFreeze).toHaveBeenCalledWith(expect.objectContaining({ pairAddress: 'PB' }), true);
  await act(async () => { w.querySelector('[data-testid="cw-topup"]').click(); }); expect(top).toHaveBeenCalled();
});
