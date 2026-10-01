import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaPrime, primeRow } from './ArenaPrime';
import { CardEarnings } from './CardEarnings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const CARD = { id: 'prime-degen', tpl: 'degen', label: '🚀 Prime Degen', at: 1, lastRotateAt: Date.now() / 1000, startUsd: 100, valueUsd: 112.5, pnlPct: 12.5, compoundedUsd: 12.5, takenUsd: 12.5, feesUsd: 0.9, cash: 0,
  legs: [{ mint: 'A', pairAddress: 'PA', symbol: 'AAA', role: 'pool', units: 16.7, costUsd: 25, usd: 25, now: 1.5 }, { mint: 'R', pairAddress: 'PR', symbol: 'RUN', role: 'runner', units: 30, costUsd: 25, usd: 30, now: 1 }],
  events: [{ kind: 'tp', at: Date.now() / 1000 - 600, symbol: 'AAA', usd: 12.5, why: '+50% ≥ +30%', to: ['RUN'] }] };

test('prime cards: live card, compounded $, rotation clock, Buy now loads the Lab, earnings show where the profit went', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 6, rotateCount: 2, compound: true } }) }));
  const onLoad = jest.fn();
  const el = await mount(<ArenaPrime onLoad={onLoad} />);
  expect(el.textContent).toContain('+12.5%'); expect(el.textContent).toContain('$12.50');
  await act(async () => { el.querySelector('[data-testid="prime-buy-degen"]').click(); });
  expect(onLoad.mock.calls[0][0].map(l => [l.symbol, l.runner])).toEqual([['AAA', false], ['RUN', true]]);
  await act(async () => { el.querySelector('[data-testid="prime-earn-degen"]').click(); });
  const ce = document.querySelector('[data-testid="card-earnings"]');
  expect(ce.textContent).toContain('💰 Auto TP'); expect(ce.textContent).toContain('→ $RUN'); expect(ce.textContent).toContain('not in P&L');
});

test('prime row maps to a live card without inventing numbers', () => {
  const r = primeRow(CARD);
  expect(r.legs[1]).toMatchObject({ tokens: 30, usd: 25, valueUsd: 30, role: 'runner' }); expect(r.pnlUsd).toBeCloseTo(12.5);
});

test('collect is one tap and disabled when the card is not up', async () => {
  const onCollect = jest.fn(); const onClose = jest.fn();
  await mount(<CardEarnings title="Mine" taken={3} compounded={1} gainNow={0} onCollect={onCollect} onClose={onClose} />);
  expect([...document.querySelectorAll('[data-testid="ce-collect"]')].pop().disabled).toBe(true);
  await act(async () => { [...document.querySelectorAll('[data-testid="card-earnings"]')].pop().click(); }); expect(onClose).toHaveBeenCalled();
});
