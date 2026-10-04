import React from 'react';
import { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FuseLanding, heroCard } from './FuseLanding';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('./terminal/MarketPrimitives', () => ({ TokenAvatar: () => null }));
jest.mock('../lib/livePrices', () => ({ useLivePrices: () => new Map([['P1', { price: 3 }]]) }));
const CARDS = [{ id: 'a', label: '💎 Prime Diamond', real: true, pnlPct: -5, valueUsd: 1.7, startUsd: 1.8, rounds: 300, nextRoundAt: 9e9, legs: [{ pairAddress: 'P9', mint: 'M9', symbol: 'SOL', role: 'anchor', entry: 100, now: 99 }] },
  { id: 'b', label: '♾ Prime Everlasting', pnlPct: 12, valueUsd: 112, startUsd: 100, rounds: 500, nextRoundAt: 9e9, legs: [{ pairAddress: 'P1', mint: 'M1', symbol: 'AAA', role: 'runner', entry: 2, now: 2.1 }] }];
jest.mock('./ArenaPrime', () => ({ usePrime: () => ({ cards: require('./FuseLanding.test.jsx').__cards }) }));
export const __cards = CARDS;

test('hero = the best card right now, each coin priced live against its own entry', () => {
  const c = heroCard(CARDS, new Map([['P1', { price: 3 }]]));
  expect(c.id).toBe('b'); expect(c.legs[0].livePct).toBeCloseTo(50);
  expect(heroCard([], null)).toBeNull();
});

test('landing: live numbers, the card flips to its book, and the buttons lead into the Lab and the Arena', async () => {
  const onGo = jest.fn(); const host = document.createElement('div'); document.body.appendChild(host);
  await act(async () => { createRoot(host).render(<FuseLanding onGo={onGo} />); });
  expect(host.querySelector('[data-testid="fld-live"]').textContent).toContain('800');            // 300 + 500 rounds played
  const card = host.querySelector('[data-testid="fld-card"]');
  expect(card.textContent).toContain('Prime Everlasting'); expect(card.textContent).toContain('PAPER'); expect(card.textContent).toContain('+50.0%');
  act(() => card.click()); expect(card.className).toContain('is-flip');
  act(() => host.querySelector('[data-testid="fld-build"]').click()); expect(onGo).toHaveBeenCalledWith('lab');
  act(() => host.querySelector('[data-testid="fld-arena"]').click()); expect(onGo).toHaveBeenCalledWith('arena');
  expect(host.querySelectorAll('[data-testid="fld-how"] li').length).toBe(4);
});
