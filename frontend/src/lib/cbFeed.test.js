import { toBars, foldTrade } from './cbFeed';

test('📈 Coinbase rows (newest first) → chart bars (oldest first)', () => {
  expect(toBars([[120, 1, 3, 2, 2.5, 10], [60, 0.5, 2.2, 1, 2, 4], ['bad']])).toEqual([
    { time: 60, open: 1, high: 2.2, low: 0.5, close: 2, volume: 4 }, { time: 120, open: 2, high: 3, low: 1, close: 2.5, volume: 10 }]);
  expect(toBars(null)).toEqual([]);
});

test('⚡ every print folds into the live candle; a new bucket opens at the previous close (no gaps, no floating dashes)', () => {
  const last = { time: 60, open: 1, high: 2, low: 1, close: 1.5, volume: 3 };
  expect(foldTrade(last, 2.5, 1, 90, 60)).toEqual({ time: 60, open: 1, high: 2.5, low: 1, close: 2.5, volume: 4 });
  expect(foldTrade(last, 1.2, 2, 125, 60)).toEqual({ time: 120, open: 1.5, high: 1.5, low: 1.2, close: 1.2, volume: 2 });
  expect(foldTrade(last, 9, 1, 30, 60)).toBe(last);                                                      // a late print never rewrites history
});

test('🌊 order flow: taker buy vs sell, whale prints, the move over a window, realized volatility', () => {
  const { flowOf, whales, moveOf, rvol } = require('./cbFeed');
  const now = 100000; const flow = [{ t: 30000, usd: 5, buy: true }, { t: 70000, usd: 60000, buy: true }, { t: 90000, usd: 20000, buy: false }, { t: 99000, usd: 100, buy: true }];
  const f = flowOf(flow, 60000, now);
  expect(f.buy).toBe(60100); expect(f.sell).toBe(20000); expect(f.n).toBe(3); expect(f.top.usd).toBe(60000); expect(f.share).toBeCloseTo(0.7503, 3);
  expect(whales(flow, 50000).map(x => x.usd)).toEqual([60000]); expect(flowOf([], 60000, now).share).toBeNull();
  expect(moveOf([{ t: 1000, p: 100 }, { t: 50000, p: 101 }, { t: 99000, p: 102 }], 60000, now)).toBeCloseTo(0.990, 2);
  expect(moveOf([{ t: 99000, p: 102 }], 60000, now)).toBeNull();
  expect(rvol(Array.from({ length: 10 }, (_, i) => ({ p: 100 + i })))).toBeNull();
  expect(rvol(Array.from({ length: 60 }, (_, i) => ({ p: 100 * (1 + (i % 2 ? 0.0001 : -0.0001)) })))).toBeGreaterThan(0);
});
