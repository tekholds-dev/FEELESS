import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, fateOf, hudCounters, heatDots, killFeed } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const rows = [{ mint: 'A', symbol: 'AAA', safe: true, chg5m: 30, mcap: 5e6, vol1h: 9e4 }, { mint: 'B', symbol: 'BBB', safe: false, fails: ['top-10 holds 61%'], chg5m: -40, mcap: 5e3 },
  { mint: 'C', symbol: 'CCC', mcap: 5e4 }, { mint: 'B2', symbol: 'BBB', safe: false, fails: ['dev'], mcap: 9e3 }];

test('every number comes only from what was answered; dots sit by cap and 5m move; the feed is real events', () => {
  expect(rows.map(fateOf)).toEqual(['safe', 'fail', 'wait', 'fail']);
  expect(hudCounters({ rows, seen: 9 }, { live: [1, 2] }, { feed: [1, 2, 3] }).map(c => c.v)).toEqual([9, 2, 2, 3]);
  expect(hudCounters(null, null, null).map(c => c.v)).toEqual([null, null, null, null]);
  const d = heatDots(rows);
  expect(d.map(x => x.sym)).toEqual(['AAA', 'BBB', 'CCC']);              // one dot per ticker
  expect(d[0]).toMatchObject({ x: 98, y: 6 }); expect(d[1]).toMatchObject({ x: 2, y: 94, fate: 'fail' });   // $5M top-right, $5K dumping bottom-left
  const f = killFeed(rows, { live: [{ symbol: 'RUN', mint: 'R', chg1h: 44 }] }, { feed: [{ sig: 's1', at: Date.now() / 1000, side: 'buy', symbol: 'BUY', mint: 'M', usd: 0.5 }] });
  expect(f.map(e => e.kind)).toEqual(['buy', 'block', 'runner']);
  expect(f[1].txt).toBe('missed: top-10 holds 61%');
  expect(killFeed(rows, { live: [{ symbol: 'BBB' }] }, null).filter(e => e.kind === 'block')).toHaveLength(0);   // never both blocked and a runner
});

test('the HUD draws counters, the heat field and the feed, and opens a coin on tap', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('trench/open') ? { rows, seen: 9 } : String(url).includes('proof') ? { feed: [] } : String(url).includes('forecast') ? { level: 'rain' } : { live: [1, 2] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('hud-live').querySelector('.hud-roll').getAttribute('aria-label')).toBe('9');
  expect(q('hud-blocked').querySelector('.hud-roll').getAttribute('aria-label')).toBe('2');
  expect(global.fetch).toHaveBeenCalledTimes(4);
  await act(async () => { q('hud-dot-BBB').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'B' }));
});
