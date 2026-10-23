import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CatBrainSwitch, EngineLine, deskCounts, feeBook } from './CatBrainSwitch';

const now = Date.now() / 1000;
const DESK = [{ pair: 'PA', symbol: 'AAA', word: 'YES', why: 'buyers lead', line: '$AAA · MC 120K', ms: 9000, at: now - 60 },
  { pair: 'PH', symbol: 'HHH', word: 'SELL', why: 'move died', line: '$HHH · you +4%', ms: 8000, at: now - 50 },
  { pair: 'PN', symbol: 'NNN', word: 'NO', why: '', line: '$NNN', ms: 7000, at: now - 40 }, { pair: 'PO', symbol: 'OLD', word: 'YES', at: now - 2000 }];

test('🐱 NEXA trades FeeCat: owner switch, her round countdown, her last words (YES / NO / SELL) and the calls with the numbers she saw', async () => {
  expect(deskCounts(DESK, now)).toEqual({ YES: 1, NO: 1, SELL: 1, HOLD: 0 });   // only the last 15 min count
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  const act_ = jest.fn();
  await act(async () => { root.render(<CatBrainSwitch d={{ trade: false, provider: { on: true }, desk: [] }} act={act_} />); });
  const [rules, nexa] = el.querySelectorAll('[role="radio"]');
  expect(rules.getAttribute('aria-checked')).toBe('true');
  await act(async () => { nexa.click(); });
  expect(act_).toHaveBeenCalledWith({ trade: true });
  await act(async () => { root.render(<CatBrainSwitch d={{ trade: true, provider: { on: true }, desk: DESK, deskAt: now - 60, deskEvery: 300, record: { favor: { n: 40, rightPct: 55, typical: 1.2 } } }} act={act_} />); });
  expect(el.textContent).toContain('NEXA trades FeeCat');
  expect(el.textContent).toContain('next in 4m');
  expect(el.querySelector('.cb-nums').textContent).toBe('1YES1NO1SELL');
  expect(el.querySelectorAll('.cb-calls li')).toHaveLength(4);
  expect(el.querySelectorAll('.cb-calls li')[1].getAttribute('data-tip')).toBe('$NNN');   // hover = the exact line she was asked
  expect(el.querySelector('.cb-word.is-sell').closest('li').textContent).toContain('$HHH');
  expect(el.querySelector('.cb-rec').textContent).toContain('55%');
  await act(async () => { el.querySelectorAll('[role="radio"]')[0].click(); });
  expect(act_).toHaveBeenLastCalledWith({ trade: false });
  await act(async () => { root.render(<CatBrainSwitch d={{ trade: true, provider: { on: false }, desk: [] }} act={act_} />); });
  expect(el.textContent).toContain('NEXA is not connected — FeeCat holds');
  await act(async () => { root.render(<EngineLine />); });
  expect(el.textContent).toContain('FEELESS rule engine');
  act(() => root.unmount());
});

test('🐱 FeeCat\'s book under NEXA: her holdings (🪟 = NEXA\'s YES), the free SOL and the guard that stopped a YES', () => {
  const b = feeBook({ cat: { balanceSol: 22.5, positions: [{ symbol: 'AAA', pairAddress: 'PA', currentChange: 12.3, costSol: 0.4, nexa: true },
    { symbol: 'BBB', pairAddress: 'PB', currentChange: -3, costSol: 0.2, reason: 'fresh lane' }] }, scan: { safetyRejects: [{ symbol: 'LUKE', why: 'top 10 wallets hold 25%' }] } });
  expect(b.bal).toBe(22.5);
  expect(b.held.map(h => [h.sym, h.nexa])).toEqual([['AAA', true], ['BBB', false]]);
  expect(b.stops[0].why).toMatch(/top 10/);
  expect(feeBook(null)).toEqual({ held: [], stops: [], bal: 0 });
});
