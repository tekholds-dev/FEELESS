import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CatBrainSwitch, EngineLine, deskCounts, feeBook, duel, linesChip } from './CatBrainSwitch';

const now = Date.now() / 1000;
const DESK = [{ pair: 'PA', symbol: 'AAA', word: 'YES', why: 'buyers lead', line: '$AAA · MC 120K', ms: 9000, at: now - 60 },
  { pair: 'PH', symbol: 'HHH', word: 'SELL', why: 'move died', line: '$HHH · you +4%', ms: 8000, at: now - 50 },
  { pair: 'PN', symbol: 'NNN', word: 'NO', why: '', line: '$NNN', ms: 7000, at: now - 40 }, { pair: 'PO', symbol: 'OLD', word: 'YES', at: now - 2000 }];

test('🐱 NEXA trades FeeCat: owner switch, her round countdown, her last words (YES / NO / SELL) and the calls with the numbers she saw', async () => {
  expect(deskCounts(DESK, now)).toEqual({ YES: 1, NO: 1, SELL: 1, HOLD: 0, SKIM: 0 });   // only the last 15 min count
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
  expect(el.querySelector('.cb-nums').textContent).toBe('1YES1NO1SELL0SKIM');
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

test('⚔ the duel: NEXA\'s graded YES vs FeeCat\'s closed trades, the higher one leads', () => {
  expect(duel({ n: 147, rightPct: 43, typical: -1.55 }, { wins: 6, losses: 4 })).toMatchObject({ lead: 'rules', nx: { pct: 43 }, rl: { pct: 60, n: 10 } });
  expect(duel({ n: 5, rightPct: 80 }, { wins: 1, losses: 3 }).lead).toBe('nexa');
  expect(duel(null, null)).toEqual({ nx: null, rl: null, lead: null });
});

test('⏱ a live trade: her 2-min held check, SKIM / stop / take chips, and silence as an icon (never a sentence)', async () => {
  const now = Date.now() / 1000;   // this test's own clock (the file's clock is minutes old under gate load)
  expect(linesChip({ sl: 15, tp: 60 })).toBe('SL −15 · TP +60');
  expect(linesChip({})).toBe('');
  const lead = { cat: { balanceSol: 9, positions: [{ symbol: 'HHH', pairAddress: 'PH', currentChange: 4, costSol: 0.3 }] } };
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(lead) }));
  const desk = [{ pair: 'PH', symbol: 'HHH', word: 'HOLD', why: 'buyers still lead', lines: { sl: 15, tp: 60 }, at: now - 30 },
    { pair: 'PS', symbol: 'SSS', word: 'SKIM', why: 'spike', at: now - 20 }, { pair: 'PZ', symbol: 'ZZZ', word: null, why: 'no provider answered — deterministic only', at: now - 10 }];
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  await act(async () => { root.render(<CatBrainSwitch d={{ trade: true, provider: { on: true }, desk, deskAt: now - 200, heldAt: now - 30, deskEvery: 300, heldEvery: 120 }} act={() => {}} />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelector('.cb-wrap').classList.contains('is-fast')).toBe(true);
  expect(el.querySelector('.cb-read small').textContent).toMatch(/^⏱ live trade · checked (3\d|[4-9]\d)s ago · next in \d+s$/);
  expect(el.querySelector('.cb-word.is-skim').closest('li').textContent).toContain('$SSS');
  expect(el.querySelector('.cb-lines').textContent).toBe('🎯 SL −15 · TP +60');
  const off = el.querySelector('[data-testid="nexa-silent"]');
  expect(off.getAttribute('data-tip')).toContain('no provider answered');
  expect(off.closest('li').querySelector('em').textContent).toBe('');   // the reason lives on hover, the row shows the icon
  act(() => root.unmount()); delete global.fetch;
});
