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
