import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { HomeEngine, enginePods, engineVitals, fateOf, sieveDrops, gateOf, beatSec } from './HomeEngine';

jest.mock('./CoinDrawer', () => ({ openCoin: jest.fn() }));
const rows = [{ mint: 'A', symbol: 'AAA', safe: true, chg5m: 2 }, { mint: 'B', symbol: 'BBB', safe: false, fails: ['top-10'], chg5m: -4 }, { mint: 'C', symbol: 'CCC', chg5m: 0 }, { mint: 'A', symbol: 'AAA', safe: true }];

test('pods are real coins once each with their fate; vitals come only from what was answered', () => {
  expect(rows.map(fateOf)).toEqual(['safe', 'fail', 'wait', 'safe']);
  expect(enginePods(rows).map(p => [p.sym, p.fate])).toEqual([['AAA', 'safe'], ['BBB', 'fail'], ['CCC', 'wait']]);
  const v = engineVitals({ rows, seen: 9 }, { level: 'rain', breadthPct: 69, buyersPct: 56 }, { live: [1, 2], nextRoundAt: 5 });
  expect(v).toMatchObject({ seen: 9, read: 3, safe: 2, safePct: 67, runners: 2, weather: 'rain', green: 69, buyers: 56 });
  expect(sieveDrops(rows).map(p => [p.sym, p.fate, p.gate])).toEqual([['BBB', 'fail', 1], ['AAA', 'safe', 4], ['CCC', 'wait', 0]]);   // caught at HOLDERS (top-10)
  expect(fateOf({ fails: ['not scanned yet — holders unknown'] })).toBe('wait');   // not read is not a fail
  expect([gateOf({ fails: ['Snipers/bundlers under 8%'] }), gateOf({ fails: ['Dev holds under 4%'] }), gateOf({ fails: ['mystery'] })]).toEqual([2, 3, 0]);
  expect(beatSec(100)).toBe(0.7); expect(beatSec(0)).toBe(2.4); expect(beatSec(null)).toBe(2);
  expect(engineVitals(null, null, null)).toMatchObject({ seen: null, safe: null, safePct: null, runners: null, weather: null });
});

test('the home engine draws the gates, the live pods and opens a coin on tap', async () => {
  const { openCoin } = require('./CoinDrawer');
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('trench/open') ? { rows, seen: 9 } : String(url).includes('forecast') ? { level: 'rain', trend: 'clearing', breadthPct: 69, buyersPct: 56 } : { live: [1, 2] }) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  const q = id => el.querySelector(`[data-testid="${id}"]`);
  expect(q('home-engine')).toBeTruthy(); expect(q('hen-gate-seen').textContent).toContain('9'); expect(q('hen-gate-safe').textContent).toContain('2');
  expect(q('hen-weather').textContent).toContain('RAIN'); expect(global.fetch).toHaveBeenCalledTimes(3);
  await act(async () => { q('hen-pod-BBB').click(); });
  expect(openCoin).toHaveBeenCalledWith(expect.objectContaining({ mint: 'B' }));
});

test('the live scan heartbeat: one beat per real coin, up = passed, down = caught with its reason', async () => {
  const { scanBeats, beatPath } = require('./HomeEngine');
  const many = [...rows.slice(0, 3), { mint: 'D', symbol: 'DDD', safe: true }, { mint: 'E', symbol: 'EEE', safe: false, fails: ['dev holds 40%'] }];
  const b = scanBeats(many);
  expect(b.map(x => [x.sym, x.fate, x.why])).toEqual([['AAA', 'safe', null], ['BBB', 'fail', 'failed “top-10”'], ['CCC', 'wait', null], ['DDD', 'safe', null], ['EEE', 'fail', 'failed “dev holds 40%”']]);
  expect(beatPath(b.slice(0, 1))).toMatch(/^M0 30 .* L64 30$/);
  global.fetch = jest.fn(url => Promise.resolve({ ok: true, json: () => Promise.resolve(String(url).includes('trench/open') ? { rows: many } : {}) }));
  const el = document.createElement('div'); document.body.appendChild(el);
  await act(async () => { createRoot(el).render(<HomeEngine />); });
  await act(async () => { await Promise.resolve(); });
  expect(el.querySelector('[data-testid="hen-ekg"]')).toBeTruthy();
  expect(el.querySelector('[data-testid="hen-caught"]').textContent).toContain('caught $BBB · failed “top-10”');
});
