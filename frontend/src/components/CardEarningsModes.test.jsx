import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
jest.mock('./ShareGif', () => ({ ShareGifButton: () => null }));
import { CardEarnings } from './CardEarnings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;

test('card window: each coin can freeze and pick its own stop mode (card / sell / park / hold)', () => {
  const picks = [];
  const host = document.createElement('div'); document.body.appendChild(host);
  act(() => { createRoot(host).render(<CardEarnings title="C" legs={[{ pairAddress: 'P1', symbol: 'AAA', mode: 'park' }]} onFreeze={() => {}} onMode={(l, m) => picks.push([l.pairAddress, m])} cardMode="sell" onClose={() => {}} />); });
  expect(document.querySelector('[data-testid="cmode-park-P1"]').className).toContain('active');
  expect(document.querySelector('[data-testid="cmode-card-P1"]').textContent).toContain('card · sell');
  act(() => document.querySelector('[data-testid="cmode-hold-P1"]').click());
  expect(picks).toEqual([['P1', 'hold']]);
});
