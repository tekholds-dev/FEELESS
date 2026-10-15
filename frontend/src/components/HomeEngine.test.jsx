import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, fateOf, caughtCoins, stackVitals, stackChips } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const rows = [{ mint: 'A', symbol: 'AAA', safe: true, chg5m: 2 }, { mint: 'B', symbol: 'BBB', safe: false, fails: ['top-10 holds 61%'] }, { mint: 'C', symbol: 'CCC' }, { mint: 'B2', symbol: 'BBB', safe: false, fails: ['dev'] }];

test('every number comes only from what was answered; caught coins are real fails once each', () => {
  expect(rows.map(fateOf)).toEqual(['safe', 'fail', 'wait', 'fail']);
  expect(fateOf({ fails: ['not scanned yet — holders unknown'] })).toBe('wait');
  expect(caughtCoins(rows)).toEqual([{ mint: 'B', sym: 'BBB', pair: undefined, why: 'top-10 holds 61%' }]);
  const v = stackVitals({ rows, seen: 9 }, { level: 'rain', breadthPct: 69 }, { live: [1, 2] }, { cards: [{ real: true }, {}] }, { feed: [1, 2, 3] });
  expect(v).toMatchObject({ seen: 9, read: 3, caught: 2, safePct: 33, runners: 2, weather: 'rain', cards: 2, real: 1, swaps: 3 });
  const empty = stackChips(stackVitals(null, null, null, null, null));
  expect(empty.map(c => c.n)).toEqual(['—', '—', '—', '—', '—', '—']);
});

test('the stack draws six live chips, the caught ticker, and opens a caught coin on tap', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('trench/open') ? { rows, seen: 9 } : String(url).includes('forecast') ? { level: 'rain', breadthPct: 69 } : String(url).includes('proof') ? { feed: [1] } : String(url).includes('prime') ? { cards: [{}] } : { live: [1, 2] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('hen-chip-sees').textContent).toContain('9'); expect(q('hen-chip-hunts').textContent).toContain('2');
  expect(q('hen-chip-reads').textContent).toContain('RAIN'); expect(q('hen-chip-proves').textContent).toContain('1');
  expect(global.fetch).toHaveBeenCalledTimes(5);
  await act(async () => { q('hen-caught').querySelector('button').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'B' }));
});
