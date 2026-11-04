import { trueCandles } from './chartMath';

test('🕯 a chart keeps every real number: no redrawn spike, no forced open, no clipped wick', () => {
  const rows = [[60, 1, 1.2, 0.9, 1.1, 5], [120, 14, 98, 0.1, 90, 1], [300, 3, 3, 3, 3, 0]];
  expect(trueCandles(rows)).toEqual(rows);
});

test('only a row that cannot be drawn is dropped', () => {
  expect(trueCandles([[60, 0, 1, 1, 1, 0], [120, NaN, 1, 1, 1, 0], [180, 1, 1, 1, 1, 0]])).toEqual([[180, 1, 1, 1, 1, 0]]);
});
