import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, ageWord, scoreOf, fateOf, checksOf, spotlight, verdictOf, realTrades, counters } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const rows = [{ mint: 'A', symbol: 'AAA', safe: true, top10: 18, dev: 2, bundledN: 0, snipersN: 1, liq: 25000, buyShare: 61 }, { mint: 'B', symbol: 'BBB', safe: false, fails: ['Top 10 under 22%'], top10: 61 },
  { mint: 'C', symbol: 'CCC' }, { mint: 'R', symbol: 'RUN', safe: true }];

test('checks come from the coin only; unread is "—"; the spotlight weaves caught, cleared and runners', () => {
  expect(rows.map(fateOf)).toEqual(['safe', 'fail', 'wait', 'safe']);
  const ck = checksOf(rows[0]); expect(ck.map(c => c.ok)).toEqual([true, true, true, true, true]); expect(ck[0].v).toBe('18%');
  expect(checksOf(rows[1])[0].ok).toBe(false); expect(checksOf(rows[1])[1]).toMatchObject({ v: '—', ok: null, fill: 0 });
  const s = spotlight(rows, { live: [{ symbol: 'RUN' }] });
  expect(s.map(x => [x.symbol, x.verdict])).toEqual([['BBB', 'fail'], ['AAA', 'safe'], ['RUN', 'runner']]);   // the unread coin is skipped
  expect(verdictOf(s[0])).toEqual(['🛡', 'BLOCKED', 'missed: top 10 under 22%']);
  expect(realTrades({ feed: [{ sig: 'x', side: 'sell', symbol: 'Q', pct: 4.2, usd: 0.3, at: 1 }] })[0]).toMatchObject({ side: 'sell', pct: 4.2 });
  expect([ageWord(0.5), ageWord(5), ageWord(1528)]).toEqual(['30m', '5h', '64d']);
  expect(scoreOf(checksOf(rows[0]))).toEqual({ pass: 5, read: 5, pct: 100 }); expect(scoreOf(checksOf(rows[1]))).toEqual({ pass: 0, read: 1, pct: 0 });
  expect(counters(null, null, null)).toEqual({ live: null, blocked: null, runners: null, swaps: null });
});

test('the panel shows a coin with its verdict and the real swaps, and opens the coin on tap', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('trench/open') ? { rows, seen: 9 } : String(url).includes('proof') ? { feed: [{ sig: 's', side: 'buy', symbol: 'Q', usd: 0.25, at: Date.now() / 1000 }] } : { live: [] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('wfw-count').textContent).toContain('9 coins live'); expect(q('wfw-verdict').textContent).toContain('BLOCKED');
  expect(q('wfw-trades').textContent).toContain('$Q'); expect(q('wfw-ring').textContent).toContain('0/1'); expect(q('wfw-next').querySelectorAll('button').length).toBe(2);   // the other two coins in the queue
  await act(async () => { q('wfw-coin-BBB').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'B' }));
});
