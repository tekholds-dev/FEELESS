import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { FeeCatLore, chapterStat, CHAPTERS } from './FeeCatLore';

jest.mock('react-router-dom', () => ({ Link: ({ to, children, ...p }) => require('react').createElement('a', { href: to, ...p }, children) }), { virtual: true });
globalThis.IS_REACT_ACT_ENVIRONMENT = true;
const P = { cat: { level: 2, balanceSol: 25.4, wins: 3, losses: 1, realizedPnlSol: 0.41 }, stats: { trades: 4, roiPct: 1.6 }, discipline: { lives: 7, maxLives: 9, why: 'normal size', pause: false } };

test('pure: every chapter carries a live number', () => {
  expect(CHAPTERS.map(c => c[0])).toEqual(['born', 'lives', 'record', 'feeback', 'cats']);
  expect(chapterStat('lives', P)).toEqual(['7 / 9', 'normal size']);
  expect(chapterStat('record', P)[0]).toBe('3W · 1L'); expect(chapterStat('record', P)[1]).toContain('+0.41 SOL');
  expect(chapterStat('lives', { discipline: { lives: 0, maxLives: 9, pause: true } })[1]).toContain('napping');
  expect(chapterStat('feeback', P, { status: 'market_observed' })).toEqual(['PLANNED', 'FEECAT market observed']);   // never claims a payout
});

test('the legend: nine lanterns lit from her lives, chapters, the Fee-Back tabs', async () => {
  global.fetch = jest.fn(() => Promise.resolve({ ok: true, json: () => Promise.resolve(P) }));
  const el = document.createElement('div'); const root = createRoot(el);
  await act(async () => { root.render(<FeeCatLore asset={{ status: 'awaiting' }} community={{ messages: 12 }}>{t => <p data-testid="pane">{t}</p>}</FeeCatLore>); });
  await act(async () => { await new Promise(r => setTimeout(r, 900)); });
  expect(el.querySelectorAll('.fcl-lanterns i').length).toBe(9); expect(el.querySelectorAll('.fcl-lanterns i.is-lit').length).toBe(7);
  expect(el.querySelector('[data-testid="feecat-ch-record"]').textContent).toContain('3W · 1L');
  expect(el.querySelector('[data-testid="feecat-stat-2"]').textContent).toContain('12 real messages');
  expect(el.querySelector('[data-testid="pane"]').textContent).toBe('path');
  await act(async () => { el.querySelector('[data-testid="feecat-tab-calc"]').click(); });
  expect(el.querySelector('[data-testid="pane"]').textContent).toBe('calc');
  await act(async () => { root.unmount(); });
});
