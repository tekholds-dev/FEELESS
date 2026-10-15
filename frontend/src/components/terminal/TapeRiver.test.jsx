import React from 'react';
import { createRoot } from 'react-dom/client';
import { act } from 'react';
import { TapeRiver, bubbleOf, tug, priceScale } from './TapeRiver';

const now = Date.now();
const T = (tx, kind, usd, ageS, wallet = 'W' + tx) => ({ tx, kind, usd, ts: new Date(now - ageS * 1000).toISOString(), wallet });

test('bubbles: size by $, side by kind, whales, flags; the tug reads who is in charge', () => {
  const b = bubbleOf(T('a', 'buy', 5000, 3), 1000, now, [{ tone: 'bad' }]);
  expect(b.side).toBe('buy'); expect(b.whale).toBe(true); expect(b.flag).toBe('bad'); expect(b.r).toBeGreaterThan(bubbleOf(T('b', 'sell', 10, 3), 1000, now).r);
  expect(tug([T('a', 'buy', 900, 5), T('b', 'sell', 100, 5)], now).word).toBe('BUYERS IN CHARGE');
  expect(tug([T('a', 'buy', 100, 5), T('b', 'sell', 900, 5)], now).word).toBe('SELLERS IN CHARGE');
  expect(tug([T('a', 'buy', 100, 120)], now).word).toBe('QUIET');
  const g = tug([T('a', 'buy', 50, 40, 'W1'), T('b', 'sell', 300, 40, 'W2'), T('c', 'buy', 300, 3, 'W3'), T('d', 'buy', 10, 4, 'W1')], now);
  expect(g.buyers).toBe(2); expect(g.sellers).toBe(1); expect(g.turn).toBe('up');
  const ys = priceScale([1, 2, 3]); expect(ys(1)).toBe(0); expect(ys(3)).toBe(1); expect(priceScale([2, 2])(2)).toBe(0.5);
});

test('tap a bubble → who, the $, and the good / bad flags', async () => {
  const el = document.createElement('div'); document.body.appendChild(el);
  const tags = new Map([['Wdev', [{ id: 'dev', label: 'DEV', tone: 'bad', why: 'Created this coin' }]]]);
  await act(async () => { createRoot(el).render(<TapeRiver trades={[T('dev', 'sell', 2500, 4, 'Wdev'), T('x', 'buy', 40, 9)]} cut={1000} tags={tags} me={null} />); });
  const bs = el.querySelectorAll('[data-testid="trv-bubble"]');
  expect(bs.length).toBe(2); expect(bs[0].className).toContain('is-sell'); expect(bs[0].className).toContain('is-bad'); expect(bs[0].className).toContain('is-whale');
  await act(async () => { bs[0].click(); });
  expect(el.querySelector('[data-testid="trv-pop"]').textContent).toContain('DEV — Created this coin');
});
