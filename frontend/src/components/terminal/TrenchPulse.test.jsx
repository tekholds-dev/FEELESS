import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { TrenchPulse, pulse, buckets, race } from './TrenchPulse';

const now = Date.now();
const T = (tx, kind, usd, ageS, wallet = 'W' + tx) => ({ tx, kind, usd, ts: new Date(now - ageS * 1000).toISOString(), wallet });

test('the pulse word reads who is in charge, and flagged wallets selling = RUG WATCH', () => {
  const buys = ['a', 'b', 'c', 'd', 'e'].map((x, i) => T(x, 'buy', 200, i * 5));
  expect(pulse([...buys, T('s', 'sell', 50, 3)], now).word).toBe('SEND');
  expect(pulse([T('a', 'buy', 60, 5), T('b', 'sell', 40, 5)], now).word).toBe('BUYERS STACKING');
  expect(pulse([T('a', 'buy', 50, 5), T('b', 'sell', 400, 5), T('c', 'sell', 300, 6), T('d', 'sell', 300, 7)], now).word).toBe('DUMPING');
  expect(pulse([T('a', 'buy', 100, 90)], now).word).toBe('QUIET');
  const tags = new Map([['DEV', [{ id: 'dev', label: 'DEV', tone: 'bad' }]]]);
  const r = pulse([...buys, T('x', 'sell', 300, 4, 'DEV')], now, tags);
  expect(r.word).toBe('RUG WATCH'); expect(r.badSell).toBe(300);
  expect(pulse([T('a', 'buy', 10, 5, 'NEW'), T('b', 'buy', 10, 5, 'OLD')], now, new Map(), new Set(['OLD'])).fresh).toBe(1);
});

test('pressure bars bucket the last minute (right = now); the race ranks wallets by net $', () => {
  const b = buckets([T('a', 'buy', 100, 1), T('b', 'sell', 30, 58), T('c', 'buy', 5, 120)], now);
  expect(b).toHaveLength(12); expect(b[11].buy).toBe(100); expect(b[0].sell).toBe(30);
  const rows = race([T('a', 'buy', 100, 5, 'A'), T('b', 'sell', 300, 5, 'B'), T('c', 'buy', 50, 6, 'A')], now);
  expect(rows.map(r => [r.wallet, r.net])).toEqual([['B', -300], ['A', 150]]); expect(rows[0].w).toBe(1);
});

test('renders the word, 12 bars and the race', () => {
  const el = document.createElement('div'); document.body.appendChild(el); const root = createRoot(el);
  act(() => root.render(<TrenchPulse trades={[T('a', 'buy', 100, 2), T('b', 'sell', 20, 3)]} />));
  expect(el.querySelector('[data-testid="tpl-word"]').textContent).toContain('BUYERS STACKING');
  expect(el.querySelectorAll('.tpl-col')).toHaveLength(12); expect(el.querySelectorAll('.tpl-row')).toHaveLength(2);
  act(() => root.unmount()); el.remove();
});
