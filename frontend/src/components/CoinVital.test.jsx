import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CoinVital, statLine } from './CoinVital';

jest.mock('./RowVitals', () => ({ RowVitals: () => <div data-testid="old-line" /> }));

test('the vital shows a grade, five bars (organic flow first), the crew and the deciding facts; a coin not read yet keeps the old line', async () => {
  const r = { symbol: 'TT', ageH: 0.8, mcap: 635000, vol1h: 1200000, buyShare: 52, holders: 3103,
    vital: { grade: 'D', score: 38, tone: 'bad', word: 'RISKY', bars: { holders: 0.7, dev: 0.5, crew: 0.15, flow: 0.07 },
      flags: [['☠', 'serial launcher (22/1076)', 'bad'], ['🤖', 'bots — 3% of volume is organic', 'bad']],
      crew: { kind: 'serial', icon: '☠', label: 'serial launcher', why: 'dev launched 1076 coins, 22 graduated' } } };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CoinVital r={r} />); });
  const v = el.querySelector('[data-testid="cvl-TT"]');
  expect(v.className).toContain('cvl-bad'); expect(v.querySelector('.cvl-grade .cvl-g').textContent).toBe('D');
  expect(v.querySelectorAll('.cvl-bar').length).toBe(5); expect(v.querySelector('.cvl-bar .cvl-ic').textContent).toBe('🌱');   // organic flow first expect(v.querySelectorAll('.cvl-bar.bad').length).toBe(2);
  expect(v.querySelector('.cvl-crew.is-serial').textContent).toContain('serial launcher');
  expect(v.textContent).toContain('bots — 3% of volume is organic');
  expect(statLine(r)).toEqual(['48m old', '$635K cap', '$1.2M/h', '52% buys', '3,103 holders']);
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<CoinVital r={{ symbol: 'NEW' }} />); });
  expect(el2.querySelector('[data-testid="old-line"]')).not.toBeNull();
});

test('lists sort organic first and the filters drop what the owner does not want', () => {
  const { applyView } = require('./CoinVital');
  const row = (s, score, organicPct, crew = 'mixed', growth = 0.5) => ({ symbol: s, vital: { score, organicPct, crew: { kind: crew }, bars: { growth } } });
  const rows = [row('A', 70, 2), row('B', 50, 40, 'serial'), row('C', 80, 15, 'popular', 0.9), { symbol: 'N' }];
  expect(applyView(rows, { sort: 'organic', on: {} }).map(r => r.symbol)).toEqual(['B', 'C', 'A', 'N']);
  expect(applyView(rows, { sort: 'vital', on: {} }).map(r => r.symbol)).toEqual(['C', 'A', 'B', 'N']);
  expect(applyView(rows, { sort: 'list', on: { serial: true, bots: true } }).map(r => r.symbol)).toEqual(['C', 'N']);
  expect(applyView(rows, { sort: 'list', on: { b: true } }).map(r => r.symbol)).toEqual(['A', 'C']);   // a filter needing a reading drops unread rows
});
