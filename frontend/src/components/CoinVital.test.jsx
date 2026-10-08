import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { CoinVital, statLine } from './CoinVital';

jest.mock('./RowVitals', () => ({ RowVitals: () => <div data-testid="old-line" /> }));

test('the vital shows a grade, four bars, the crew and the deciding facts; a coin not read yet keeps the old line', async () => {
  const r = { symbol: 'TT', ageH: 0.8, mcap: 635000, vol1h: 1200000, buyShare: 52, holders: 3103,
    vital: { grade: 'D', score: 38, tone: 'bad', word: 'RISKY', bars: { holders: 0.7, dev: 0.5, crew: 0.15, flow: 0.07 },
      flags: [['☠', 'serial launcher (22/1076)', 'bad'], ['🤖', 'bots — 3% of volume is organic', 'bad']],
      crew: { kind: 'serial', icon: '☠', label: 'serial launcher', why: 'dev launched 1076 coins, 22 graduated' } } };
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<CoinVital r={r} />); });
  const v = el.querySelector('[data-testid="cv-TT"]');
  expect(v.className).toContain('cv-bad'); expect(v.querySelector('.cv-grade b').textContent).toBe('D');
  expect(v.querySelectorAll('.cv-bar').length).toBe(4); expect(v.querySelectorAll('.cv-bar.bad').length).toBe(2);
  expect(v.querySelector('.cv-crew.is-serial').textContent).toContain('serial launcher');
  expect(v.textContent).toContain('bots — 3% of volume is organic');
  expect(statLine(r)).toEqual(['48m old', '$635K cap', '$1.2M/h', '52% buys', '3,103 holders']);
  const el2 = document.createElement('div'); document.body.appendChild(el2);
  await act(async () => { createRoot(el2).render(<CoinVital r={{ symbol: 'NEW' }} />); });
  expect(el2.querySelector('[data-testid="old-line"]')).not.toBeNull();
});
