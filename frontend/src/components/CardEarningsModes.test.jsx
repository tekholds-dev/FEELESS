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

test('card window: ⚙ per coin sets its own TP / SL / replace clock', () => {
  const sent = [];
  const host = document.createElement('div'); document.body.appendChild(host);
  act(() => { createRoot(host).render(<CardEarnings title="C2" legs={[{ pairAddress: 'Q1', symbol: 'BBB', tp: 50 }]} onCoinCfg={(l, p) => sent.push(p)} onClose={() => {}} />); });
  act(() => document.querySelector('[data-testid="ccfg-Q1"]').click());
  expect(document.querySelector('[data-testid="ccfg-tp-Q1"]').value).toBe('50');
  act(() => document.querySelector('[data-testid="ccfg-rot-15m-Q1"]').click());
  expect(sent).toEqual([{ rotateHours: 0.25 }]);
});
