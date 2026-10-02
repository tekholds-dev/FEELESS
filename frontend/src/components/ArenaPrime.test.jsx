import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { ArenaPrime, primeRow } from './ArenaPrime';
import { CardEarnings } from './CardEarnings';

globalThis.IS_REACT_ACT_ENVIRONMENT = true;
jest.mock('sonner', () => ({ toast: { success: jest.fn(), error: jest.fn() } }));
const tick = ms => act(() => new Promise(r => setTimeout(r, ms)));
const mount = async node => { const el = document.createElement('div'); document.body.appendChild(el); await act(async () => { createRoot(el).render(node); }); await tick(20); return el; };
const CARD = { id: 'prime-degen', tpl: 'degen', tier: 'blaze', goodDays: 6, loggedDays: 8, lowPct: -7.5, label: '🔥 Prime Blaze', at: 1, lastRotateAt: Date.now() / 1000, startUsd: 100, valueUsd: 112.5, pnlPct: 12.5, compoundedUsd: 12.5, takenUsd: 12.5, feesUsd: 0.9, cash: 0,
  legs: [{ mint: 'S', pairAddress: 'PS', symbol: 'SOL', role: 'anchor', stars: 5, units: 0.1, costUsd: 20, usd: 21, now: 210 }, { mint: 'A', pairAddress: 'PA', symbol: 'AAA', role: 'pool', stars: 4, units: 16.7, costUsd: 25, usd: 25, now: 1.5 }, { mint: 'R', pairAddress: 'PR', symbol: 'RUN', role: 'runner', units: 30, costUsd: 25, usd: 30, now: 1 }],
  events: [{ kind: 'tp', at: Date.now() / 1000 - 600, symbol: 'AAA', usd: 12.5, why: '+50% ≥ +30%', to: ['RUN'] }] };

test('prime cards: live card, compounded $, rotation clock, Buy now loads the Lab, earnings show where the profit went', async () => {
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 6, rotateCount: 2, compound: true } }) }));
  const onLoad = jest.fn();
  const el = await mount(<ArenaPrime onLoad={onLoad} />);
  expect(el.textContent).toContain('+12.5%'); expect(el.textContent).toContain('$12.50');
  await act(async () => { el.querySelector('[data-testid="prime-buy-degen"]').click(); });
  expect(onLoad.mock.calls[0][0].map(l => [l.symbol, l.runner])).toEqual([['SOL', false], ['AAA', false], ['RUN', true]]);
  const card = el.querySelector('[data-testid="prime-degen"]');
  expect(card.className).toContain('tier-blaze'); expect(card.className).toContain('is-hot'); expect(card.textContent).toContain('BLAZE');
  expect(card.textContent).toContain('⚓ anchor'); expect(card.textContent).toContain('★★★★★');
  expect(el.querySelector('[data-testid="prime-rec-degen"]').textContent).toMatch(/6\/8.*-7\.5%/);
  await act(async () => { el.querySelector('[data-testid="prime-earn-degen"]').click(); });
  const ce = document.querySelector('[data-testid="card-earnings"]');
  expect(ce.textContent).toContain('💰 Auto TP'); expect(ce.textContent).toContain('→ $RUN'); expect(ce.textContent).toContain('not in P&L');
});

test('prime row maps to a live card without inventing numbers', () => {
  const r = primeRow(CARD);
  expect(r.legs[2]).toMatchObject({ tokens: 30, usd: 25, valueUsd: 30, role: 'runner' }); expect(r.pnlUsd).toBeCloseTo(12.5);
});

test('collect is one tap and disabled when the card is not up', async () => {
  const onCollect = jest.fn(); const onClose = jest.fn();
  await mount(<CardEarnings title="Mine" taken={3} compounded={1} gainNow={0} onCollect={onCollect} onClose={onClose} />);
  expect([...document.querySelectorAll('[data-testid="ce-collect"]')].pop().disabled).toBe(true);
  await act(async () => { [...document.querySelectorAll('[data-testid="card-earnings"]')].pop().click(); }); expect(onClose).toHaveBeenCalled();
});

test('HQ: ⇄ replaces one coin on a Prime card, 🃏 re-deals one tier', async () => {
  const { PrimeControls } = require('./ArenaPrime');
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 6, rotateCount: 2, compound: true, floorPct: 20, on: true } }) }));
  const call = jest.fn(async () => ({ cfg: {} }));
  const el = await mount(<PrimeControls call={call} />);
  await act(async () => { el.querySelector('[data-testid="prime-swap-degen-PR"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ replace: { tpl: 'degen', pairAddress: 'PR' } });
  await act(async () => { el.querySelector('[data-testid="prime-redeal-degen"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body)).toEqual({ redeal: 'degen' });
});

test('HQ: rotate every — typed minutes save as hours (15 min floor)', async () => {
  const { PrimeControls } = require('./ArenaPrime');
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [CARD], cfg: { sizeUsd: 100, rotateHours: 1, rotateCount: 1, compound: true, floorPct: 20, on: true } }) }));
  const call = jest.fn(async (p, o) => ({ cfg: { sizeUsd: 100, rotateHours: JSON.parse(o.body).cfg.rotateHours ?? 1, rotateCount: 1, compound: true, floorPct: 20, on: true } }));
  const el = await mount(<PrimeControls call={call} />);
  const inp = el.querySelector('[data-testid="prime-rotate-min"]'); expect(inp.value).toBe('60');
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  await act(async () => { set.call(inp, '45'); inp.dispatchEvent(new Event('input', { bubbles: true })); });
  await act(async () => { inp.focus(); inp.blur(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg.rotateHours).toBe(0.75);
});

test('meta config in one click + stop mode switch + parked coins shown on the card', async () => {
  const { PrimeControls, ArenaPrime, PRIME_META } = require('./ArenaPrime');
  const cfg = { sizeUsd: 100, rotateHours: 1, rotateCount: 1, compound: true, floorPct: 20, on: true, slMode: 'replace' };
  global.fetch = jest.fn(async () => ({ json: async () => ({ cards: [{ ...CARD, why: 'all runners', parked: [{ pairAddress: 'PX', symbol: 'GONE', usd: 18.5, backAt: 0.0012 }] }], cfg }) }));
  const call = jest.fn(async (p, o) => ({ cfg: { ...cfg, ...JSON.parse(o.body).cfg } }));
  const el = await mount(<PrimeControls call={call} />);
  await act(async () => { el.querySelector('[data-testid="prime-meta"]').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg).toEqual(PRIME_META);
  await act(async () => { [...el.querySelectorAll('button')].find(b => b.textContent === '❄ Hold').click(); });
  expect(JSON.parse(call.mock.calls.at(-1)[1].body).cfg).toEqual({ slMode: 'hold' });
  const ap = await mount(<ArenaPrime onLoad={() => {}} />);
  expect(ap.textContent).toContain('🅿 $GONE'); expect(ap.textContent).toContain('$18.50'); expect(ap.textContent).toContain('all runners');
});
