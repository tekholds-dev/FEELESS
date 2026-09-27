import { scrubCandles } from './chartMath';

test('drops a bar priced from a different pool/quote (spike 14x) and keeps real moves', () => {
  const bar = (t, c) => [t, c, c, c, c, 1];
  const rows = [bar(1, 7e-6), bar(2, 7e-6), [3, 7e-6, 9.8e-5, 7e-6, 9.8e-5, 1], bar(4, 7e-6), bar(5, 9e-6), bar(6, 1.1e-5)];
  const out = scrubCandles(rows);
  expect(out.map(r => r[0])).toEqual([1, 2, 4, 5, 6]);
  expect(Math.max(...out.map(r => r[2]))).toBeLessThan(3e-5);
});
