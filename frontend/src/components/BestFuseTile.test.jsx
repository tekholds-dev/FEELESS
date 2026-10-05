import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { BestFuseTile } from './BestFuseTile';

jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map() }));
globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('home tile shows the best Fuse card right now, labelled real or paper, and links to it', async () => {
  global.fetch = jest.fn(async () => ({ ok: true, json: async () => ({ cards: [
    { id: 'a', tier: 'gold', label: 'Prime Gold', pnlPct: 3.2, legs: [{ pairAddress: 'p1', symbol: 'AAA', entry: 1, now: 1.1 }] },
    { id: 'b', tier: 'degen', label: 'Prime Blaze', real: true, pnlPct: 41.5, legs: [{ pairAddress: 'p2', symbol: 'BBB', entry: 1, now: 2 }, { pairAddress: 'p3', symbol: 'CCC', entry: 1, now: 0.9 }] }] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<BestFuseTile />); });
  await act(() => new Promise(r => setTimeout(r, 20)));
  const tile = el.querySelector('[data-testid="best-fuse-tile"]');
  expect(tile.textContent).toContain('Prime Blaze');
  expect(tile.textContent).toContain('💵 REAL');
  expect(tile.textContent).toContain('+41.5%');
  expect(tile.textContent).toContain('$BBB');
  expect(tile.getAttribute('href')).toContain('/terminal/fuse');
});
