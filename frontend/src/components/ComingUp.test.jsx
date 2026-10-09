import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ComingUp } from './ArenaPrime';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
jest.mock('../lib/sharedJson', () => ({ sharedJson: () => Promise.resolve(null), markFresh: () => {}, _resetShared: () => {} }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('best 3: the engine\'s own picks with their door and live tape, three at most, each one tap to swap in', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const p = { best: [{ mint: 'A', pairAddress: 'pa', symbol: 'ONE', chg1h: 18, vol1h: 420000, tag: '⚡ burst · 🎯 proven caller', tape: 'burst' },
    { mint: 'B', pairAddress: 'pb', symbol: 'TWO', chg1h: 6, vol1h: 120000, tag: '🔥 top 3' },
    { mint: 'C', pairAddress: 'pc', symbol: 'THREE', chg1h: -2, vol1h: 90000, tag: '🧊 cooling off' },
    { mint: 'D', pairAddress: 'pd', symbol: 'FOUR', chg1h: 1, vol1h: 80000, tag: '🌊 narrative leader' }] };
  const swaps = [];
  await act(async () => { createRoot(el).render(<ComingUp p={p} legs={[{ symbol: 'OLD', pairAddress: 'po' }]} onSwap={(l, r, now) => swaps.push([l.symbol, r.symbol, now])} />); });
  expect(el.textContent).toContain('BEST 3');
  expect(el.querySelector('[data-testid="up-ONE"]').textContent).toContain('🥇');
  expect(el.querySelector('[data-testid="up-tape-ONE"]').textContent).toContain('burst');
  expect(el.querySelector('[data-testid="up-FOUR"]')).toBeNull();                       // three at most
  await act(async () => { el.querySelector('[data-testid="up-now-TWO"]').click(); });
  await act(async () => { el.querySelector('[data-testid="up-bell-THREE"]').click(); });
  expect(swaps).toEqual([['OLD', 'TWO', true], ['OLD', 'THREE', false]]);
  const fills = []; const e3 = document.createElement('div'); document.body.appendChild(e3);   // an empty seat is the default target
  await act(async () => { createRoot(e3).render(<ComingUp p={p} legs={[{ symbol: 'OLD', pairAddress: 'po' }]} emptySeats={1} onFill={r => fills.push(r.symbol)} onSwap={() => {}} />); });
  await act(async () => { e3.querySelector('[data-testid="up-now-ONE"]').click(); });
  expect(fills).toEqual(['ONE']);
  const e2 = document.createElement('div'); document.body.appendChild(e2);
  await act(async () => { createRoot(e2).render(<ComingUp p={{ best: [] }} />); });
  expect(e2.textContent).toContain('the engine waits');
});
