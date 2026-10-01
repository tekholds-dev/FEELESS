import { scrubCandles } from './chartMath';

test('flattens a bar priced from a different pool/quote (spike 14x) without skipping the candle', () => {
  const bar = (t, c) => [t, c, c, c, c, 1];
  const rows = [bar(1, 7e-6), bar(2, 7e-6), [3, 7e-6, 9.8e-5, 7e-6, 9.8e-5, 1], bar(4, 7e-6), bar(5, 9e-6), bar(6, 1.1e-5)];
  const out = scrubCandles(rows);
  expect(out.map(r => r[0])).toEqual([1, 2, 3, 4, 5, 6]);
  expect(Math.max(...out.map(r => r[2]))).toBeLessThan(3e-5);
});

test('candles connect: each opens at the previous close, wicks include the open', () => {
  const { scrubCandles } = require('./chartMath');
  const out = scrubCandles([[60, 1, 1, 1, 1, 0], [120, 1.3, 1.3, 1.3, 1.3, 0], [180, 0.9, 1.0, 0.8, 0.95, 5]]);
  expect(out.map(r => r[1])).toEqual([1, 1, 1.3]);
  expect(out[1]).toEqual([120, 1, 1.3, 1, 1.3, 0]);   // was a floating one-price dash at 1.3
  expect(out[2][2]).toBeGreaterThanOrEqual(1.3);
});
